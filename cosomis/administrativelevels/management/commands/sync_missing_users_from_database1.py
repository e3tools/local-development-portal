"""
Cette commande sert a migrer, une seule fois, les utilisateurs presents dans
un fichier sqlite `database1.db` (une base de developpement local) vers la
base de donnees courante (destinee a etre la production au moment de
l'execution reelle).

Elle est concue pour etre executee APRES upload du fichier `database1.db` sur
le serveur, avec les variables d'environnement de production actives (de
sorte que la base "default" de Django pointe bien vers la base de production).

Ce que fait la commande, dans l'ordre :
  1. Elle enregistre une connexion secondaire en lecture seule vers le
     fichier sqlite passe en `--source` (par defaut `database1.db` a la
     racine du projet).
  2. Elle synchronise d'abord les `Organization` ("Organisateurs") : le
     modele `Organization` est la seule dependance FK du modele `User`, elle
     doit donc exister en base cible avant de creer les utilisateurs qui s'y
     rattachent. Le rapprochement se fait par nom (insensible a la casse) ;
     une organisation deja presente en cible n'est pas recreee.
  3. Elle cree en base cible chaque `User` de la source dont l'email n'existe
     pas deja en cible, en copiant toutes les valeurs d'attributs (y compris
     le mot de passe deja hache, pour eviter de forcer une reinitialisation).
  4. Pour chaque utilisateur cree, elle recree et relie les objets qui en
     dependent : groupes et permissions Django, `UserToken` (jeton API) et
     `UserPassCode`, en les rattachant au nouvel utilisateur.

Le champ `photo` (ImageField) ne contient qu'un chemin relatif : le fichier
media lui-meme n'est pas stocke dans la base et n'est donc pas copie par
cette commande ; il faudra le transferer separement si necessaire.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.models.signals import post_save
from django.db.models import Q

from usermanager.models import Organization, User, UserPassCode, UserToken
from usermanager.signals import email_notification_welcome
from usermanager.tokens.jwt import create_user_token

SOURCE_ALIAS = "database1_source"


class Command(BaseCommand):
    help = (
        "Cree en base cible les utilisateurs de database1.db absents de la base "
        "courante (avec leurs Organisations et objets lies : UserToken, "
        "UserPassCode, groupes/permissions)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=str(Path(settings.BASE_DIR) / "database1.db"),
            help="Chemin vers le fichier sqlite source (defaut : database1.db a la racine du projet).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simule la synchronisation puis annule la transaction : rien n'est ecrit en base.",
        )

    def handle(self, *args, **options):
        source_path = Path(options["source"]).resolve()
        if not source_path.exists():
            raise CommandError(f"Fichier source introuvable : {source_path}")

        self._register_source_connection(source_path)
        self._warn_if_source_equals_target(source_path)

        dry_run = options["dry_run"]
        stats = {
            "organizations_created": 0,
            "organizations_matched": 0,
            "users_created": 0,
            "users_skipped": 0,
            "users_failed": [],
            "tokens_created": 0,
            "passcodes_created": 0,
            "groups_missing": set(),
        }

        # Les utilisateurs migres existent deja reellement : on desactive les
        # signaux post_save de User le temps de la commande, pour ne pas leur
        # renvoyer un e-mail de bienvenue ni ecraser le UserToken qu'on copie
        # nous-memes depuis la source par un nouveau jeton JWT genere a la volee.
        post_save.disconnect(email_notification_welcome, sender=User)
        post_save.disconnect(create_user_token, sender=User)
        try:
            with transaction.atomic():
                org_map = self._sync_organizations(stats)
                self._sync_users(org_map, stats)

                if dry_run:
                    self.stdout.write(self.style.WARNING(
                        "Dry-run : la transaction va etre annulee, rien n'est enregistre."
                    ))
                    transaction.set_rollback(True)
        finally:
            post_save.connect(email_notification_welcome, sender=User)
            post_save.connect(create_user_token, sender=User)

        self._print_summary(stats, dry_run)

    # -- infrastructure -------------------------------------------------

    def _register_source_connection(self, source_path):
        if SOURCE_ALIAS in connections.databases:
            return
        connections.databases[SOURCE_ALIAS] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(source_path),
            "ATOMIC_REQUESTS": False,
            "AUTOCOMMIT": True,
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False,
            "OPTIONS": {},
            "TIME_ZONE": None,
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
            "TEST": {"CHARSET": None, "COLLATION": None, "MIGRATE": False, "MIRROR": None, "NAME": None},
        }

    def _warn_if_source_equals_target(self, source_path):
        default_db = connections.databases.get("default", {})
        default_name = default_db.get("NAME")
        if default_name and Path(str(default_name)).resolve() == source_path:
            self.stdout.write(self.style.WARNING(
                "La base 'default' pointe deja vers le fichier source : aucun utilisateur "
                "manquant ne pourra etre detecte (source == cible)."
            ))

    @staticmethod
    def _copy_fields(source_obj, target_obj):
        """Copie tous les champs simples (hors cle primaire et relations) de
        source_obj vers target_obj, quel que soit le modele."""
        for field in source_obj._meta.local_fields:
            if field.attname in ("id", "pk") or field.is_relation:
                continue
            setattr(target_obj, field.attname, getattr(source_obj, field.attname))

    @staticmethod
    def _restore_timestamps(model, pk, source_obj):
        """`created_date` (auto_now_add) et `updated_date` (auto_now) sont
        toujours ecrases par Model.save() ; on les restaure ici via .update(),
        qui respecte une valeur explicitement fournie pour un champ auto_now
        et n'est pas du tout concerne par auto_now_add."""
        values = {}
        if hasattr(source_obj, "created_date"):
            values["created_date"] = source_obj.created_date
        if hasattr(source_obj, "updated_date"):
            values["updated_date"] = source_obj.updated_date
        if values:
            model.objects.filter(pk=pk).update(**values)

    # -- synchronisation --------------------------------------------------

    def _sync_organizations(self, stats):
        """Cree d'abord toutes les Organisations ("Organisateurs") source
        absentes de la cible, avant tout utilisateur : User.organization est
        une FK vers Organization."""
        org_map = {}
        source_orgs = Organization.objects.using(SOURCE_ALIAS).all().order_by("id")
        for source_org in source_orgs:
            target_org = Organization.objects.filter(name__iexact=source_org.name).first()
            if target_org is not None:
                stats["organizations_matched"] += 1
                org_map[source_org.id] = target_org
                continue

            try:
                with transaction.atomic():
                    target_org = Organization()
                    self._copy_fields(source_org, target_org)
                    target_org.save()
                    self._restore_timestamps(Organization, target_org.pk, source_org)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(
                    f"Echec creation organisation '{source_org.name}' : {exc}"
                ))
                continue

            stats["organizations_created"] += 1
            org_map[source_org.id] = target_org
            self.stdout.write(self.style.SUCCESS(f"Organisation creee : {target_org.name}"))

        return org_map

    def _sync_users(self, org_map, stats):
        source_users = User.objects.using(SOURCE_ALIAS).all().exclude(
            Q(email__isnull=True) 
            # | 
            # Q(email__in=[
            #     'adaboubvincent_is_moderator@gmail.com', 
            #     'adaboubvincent_is_superuser@gmail.com',
            #     'adaboubvincent_simple_user@gmail.com', 
            #     'adaboubvincent44@gmail.com'
            # ])
        ).order_by("id")
        for source_user in source_users:
            if User.objects.filter(email__iexact=source_user.email).exists():
                stats["users_skipped"] += 1
                continue

            try:
                with transaction.atomic():
                    target_user = User()
                    self._copy_fields(source_user, target_user)
                    target_user.organization = org_map.get(source_user.organization_id)
                    target_user.save()

                    self._sync_user_groups(source_user, target_user, stats)
                    self._sync_user_permissions(source_user, target_user)
                    self._sync_user_token(source_user, target_user, stats)
                    self._sync_user_passcode(source_user, target_user, stats)
            except Exception as exc:
                stats["users_failed"].append((source_user.email, str(exc)))
                self.stdout.write(self.style.ERROR(f"Echec creation utilisateur '{source_user.email}' : {exc}"))
                continue

            stats["users_created"] += 1
            self.stdout.write(self.style.SUCCESS(f"Utilisateur cree : {target_user.email}"))

    def _sync_user_groups(self, source_user, target_user, stats):
        for group_name in source_user.groups.all().values_list("name", flat=True):
            group = Group.objects.filter(name=group_name).first()
            if group is None:
                stats["groups_missing"].add(group_name)
                continue
            target_user.groups.add(group)

    def _sync_user_permissions(self, source_user, target_user):
        pairs = source_user.user_permissions.all().values_list("content_type__app_label", "codename")
        for app_label, codename in pairs:
            permission = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first()
            if permission is not None:
                target_user.user_permissions.add(permission)

    def _sync_user_token(self, source_user, target_user, stats):
        source_token = UserToken.objects.using(SOURCE_ALIAS).filter(user_id=source_user.id).first()
        if source_token is None or UserToken.objects.filter(user=target_user).exists():
            return

        target_token = UserToken(user=target_user)
        self._copy_fields(source_token, target_token)
        target_token.save()
        self._restore_timestamps(UserToken, target_token.pk, source_token)
        stats["tokens_created"] += 1

    def _sync_user_passcode(self, source_user, target_user, stats):
        source_passcode = UserPassCode.objects.using(SOURCE_ALIAS).filter(user_id=source_user.id).first()
        if source_passcode is None or UserPassCode.objects.filter(user=target_user).exists():
            return

        target_passcode = UserPassCode(user=target_user)
        self._copy_fields(source_passcode, target_passcode)
        target_passcode.save()
        stats["passcodes_created"] += 1

    def _print_summary(self, stats, dry_run):
        title = "Resume (dry-run, rien n'a ete enregistre)" if dry_run else "Resume"
        self.stdout.write(self.style.MIGRATE_HEADING(title))
        self.stdout.write(f"  Organisations creees : {stats['organizations_created']}")
        self.stdout.write(f"  Organisations deja existantes (reutilisees) : {stats['organizations_matched']}")
        self.stdout.write(f"  Utilisateurs crees : {stats['users_created']}")
        self.stdout.write(f"  Utilisateurs deja existants (ignores) : {stats['users_skipped']}")
        self.stdout.write(f"  Jetons API crees (UserToken) : {stats['tokens_created']}")
        self.stdout.write(f"  Codes de securite crees (UserPassCode) : {stats['passcodes_created']}")

        if stats["groups_missing"]:
            self.stdout.write(self.style.WARNING(
                "  Groupes absents en cible (non assignes) : " + ", ".join(sorted(stats["groups_missing"]))
            ))

        if stats["users_failed"]:
            self.stdout.write(self.style.ERROR(f"  Utilisateurs en echec : {len(stats['users_failed'])}"))
            for email, error in stats["users_failed"]:
                self.stdout.write(self.style.ERROR(f"    - {email} : {error}"))

        if stats["users_created"]:
            self.stdout.write(self.style.WARNING(
                "  Note : le champ 'photo' des utilisateurs n'est qu'un chemin relatif ; "
                "les fichiers media doivent etre transferes separement si necessaire."
            ))
