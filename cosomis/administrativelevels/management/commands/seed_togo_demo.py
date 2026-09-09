"""Build a complete, self-contained Togo demo dataset.

The portal normally fills itself from CouchDB/Kobo syncs and an MIS export.
None of that exists for a public demo deployment, so this command writes a
plausible dataset straight into the relational database: the administrative
tree (region / prefecture / commune / canton / village), the CDD planning
cycle attached to every village, four ranked local priorities per village,
the sub-projects that came out of them, a photo library, funding programmes
and the user accounts needed to sign in.

Everything is generated from a seeded PRNG, so the same ``--seed`` always
produces the same portal — re-running after a reset gives a byte-identical
dataset, and screenshots taken for a presentation stay valid.

    python manage.py seed_togo_demo --reset

The data is fictional. Village names are constructed from Togolese syllables
rather than copied from the real gazetteer, and the imagery is procedurally
drawn (see ``static/images/demo/``), so nothing here can be mistaken for real
household records.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.test.utils import override_settings

from administrativelevels.models import (
    Activity,
    AdministrativeLevel,
    Category,
    Phase,
    Project,
    Sector,
    Task,
)
from investments.models import Attachment, Investment, Package, PackageFundedInvestment
from usermanager.models import Organization, User

# --------------------------------------------------------------------------
# Geography — the three COSO regions of northern Togo.
# --------------------------------------------------------------------------

REGIONS = [
    ("Savanes", "Dapaong", (10.62, 0.35)),
    ("Kara", "Kara", (9.65, 1.05)),
    ("Centrale", "Sokodé", (8.85, 1.00)),
]

# prefecture -> (region, chef-lieu, [communes], [cantons])
PREFECTURES = {
    "Tône": ("Savanes", "Dapaong", ["Tône 1", "Tône 2"],
             ["Nano", "Naki-Est", "Korbongou", "Lotogou", "Tami", "Bogou"]),
    "Cinkassé": ("Savanes", "Cinkassé", ["Cinkassé 1"],
                 ["Timbou", "Biankouri", "Gouloungoussi"]),
    "Kpendjal": ("Savanes", "Mandouri", ["Kpendjal 1", "Kpendjal 2"],
                 ["Mandouri", "Borgou", "Koundjoaré", "Ogaro"]),
    "Oti": ("Savanes", "Sansanné-Mango", ["Oti 1", "Oti 2"],
            ["Barkoissi", "Galangashi", "Koumongou", "Takpamba"]),
    "Tandjouaré": ("Savanes", "Tandjouaré", ["Tandjouaré 1"],
                   ["Bombouaka", "Nandoga", "Goundoga", "Lokpano"]),
    "Kozah": ("Kara", "Kara", ["Kozah 1", "Kozah 2"],
              ["Pya", "Lassa", "Kouméa", "Landa", "Soumdina", "Sarakawa"]),
    "Binah": ("Kara", "Pagouda", ["Binah 1"],
              ["Kétao", "Boufalé", "Sirka", "Solla"]),
    "Doufelgou": ("Kara", "Niamtougou", ["Doufelgou 1"],
                  ["Défalé", "Siou", "Koka", "Baga"]),
    "Kéran": ("Kara", "Kandé", ["Kéran 1"],
              ["Nadoba", "Atalote", "Hélota", "Natchamba"]),
    "Bassar": ("Kara", "Bassar", ["Bassar 1", "Bassar 2"],
               ["Kabou", "Bangéli", "Bitchabé", "Dimori"]),
    "Dankpen": ("Kara", "Guérin-Kouka", ["Dankpen 1"],
                ["Nampoch", "Namon", "Natchitikpi"]),
    "Tchaoudjo": ("Centrale", "Sokodé", ["Tchaoudjo 1", "Tchaoudjo 2"],
                  ["Kparatao", "Kadambara", "Kémini", "Lama-Tessi", "Tchalo"]),
    "Tchamba": ("Centrale", "Tchamba", ["Tchamba 1"],
                ["Kaboli", "Koussountou", "Balanka", "Goubi", "Larini"]),
    "Sotouboua": ("Centrale", "Sotouboua", ["Sotouboua 1", "Sotouboua 2"],
                  ["Adjengré", "Tchébébé", "Fazao", "Kaniamboua"]),
    "Blitta": ("Centrale", "Blitta", ["Blitta 1"],
               ["Yélivo", "Pagala", "Langabou", "Yégué"]),
    "Mô": ("Centrale", "Djarkpanga", ["Mô 1"],
           ["Boulohou", "Tindjassi", "Saïbou"]),
}

VILLAGE_PREFIX = [
    "Kou", "Nan", "Tam", "Dja", "Bo", "Kpa", "Lam", "Sa", "Na", "Ti", "Ga",
    "Ba", "Ko", "Yé", "Sou", "Kan", "Pa", "Bou", "Ma", "Ta", "Do", "Lo",
    "Wa", "Ka", "Tchi", "Gbé", "Fon", "Zi", "Bin", "Kpé",
]
VILLAGE_SUFFIX = [
    "djoaré", "bongou", "gou", "kpaga", "boua", "doga", "lou", "ri", "ndé",
    "tchou", "bani", "kondji", "kopé", "ssi", "yélé", "landa", "gbadè", "lo",
    "dèna", "bou", "loum", "pou", "kaka", "nga", "mbou", "tiga", "todji",
    "wanda", "féré", "niabé",
]

FIRST_NAMES = [
    "Kossi", "Kodjo", "Yao", "Komlan", "Essohanam", "Pyabalo", "Tchilalo",
    "Lamboni", "Yentougle", "Nakpane", "Bassabi", "Abalo", "Afi", "Ama",
    "Akouvi", "Adjoa", "Essossimna", "Pihalo", "Nadjombe", "Yendoubouam",
    "Bilame", "Fousséni", "Mamah", "Sadia", "Kpatcha", "Damigou", "Assibi",
    "Nabine", "Palakiyem", "Ayaba", "Djobo", "Kokou", "Mazalo", "Talime",
]
LAST_NAMES = [
    "Lamboni", "Kombate", "Douti", "Nadjombe", "Tchagnao", "Pali", "Agba",
    "Kpatcha", "Badjona", "Tchalim", "Bassabi", "Toyi", "Nabagou", "Mensah",
    "Boukari", "Sama", "Tchassanti", "Gnama", "Yentchabre", "Doubidji",
    "Assih", "Aboudou", "Kolani", "Katanga", "Nayo", "Tchédré", "Kadanga",
]

ETHNIC_GROUPS = {
    "Savanes": ["Moba", "Gourma", "Tchokossi", "Ngam-Ngam", "Peul"],
    "Kara": ["Kabyè", "Lamba", "Nawdba", "Tamberma", "Bassar", "Konkomba"],
    "Centrale": ["Tem", "Kabyè", "Ana-Ifè", "Tchamba", "Peul"],
}

# --------------------------------------------------------------------------
# Sectors — grouped the way the portal's category filter expects.
# `image` keys the procedurally drawn scenes in static/images/demo/secteurs/.
# --------------------------------------------------------------------------

SECTORS = [
    # (category, sector, image key, cost range in thousands of FCFA, titles)
    ("Infrastructures sociales de base", "Eau & assainissement", "eau", (8_000, 45_000), [
        "Forage équipé d'une pompe à motricité humaine",
        "Réhabilitation de deux forages villageois",
        "Mini-adduction d'eau potable",
        "Bloc de latrines publiques au marché",
        "Puits pastoral aménagé",
    ]),
    ("Infrastructures sociales de base", "Éducation", "education", (25_000, 70_000), [
        "Construction de trois salles de classe",
        "Réhabilitation de l'école primaire publique",
        "Bloc de latrines scolaires séparées",
        "Logement pour enseignants",
        "Cantine scolaire équipée",
    ]),
    ("Infrastructures sociales de base", "Santé", "sante", (30_000, 90_000), [
        "Construction d'une unité de soins périphériques (USP)",
        "Réhabilitation du dispensaire villageois",
        "Case de santé communautaire",
        "Logement pour l'infirmier",
        "Équipement de la maternité",
    ]),
    ("Infrastructures économiques", "Pistes rurales", "pistes", (40_000, 160_000), [
        "Réhabilitation de la piste rurale (8 km)",
        "Construction d'un dalot de franchissement",
        "Radier submersible sur le cours d'eau",
        "Ouverture de piste vers le marché hebdomadaire",
        "Passerelle piétonne sur la rivière",
    ]),
    ("Infrastructures économiques", "Agriculture", "agriculture", (15_000, 60_000), [
        "Magasin de stockage de 100 tonnes",
        "Aménagement d'un bas-fond rizicole",
        "Périmètre maraîcher irrigué",
        "Unité de transformation du karité",
        "Parc de vaccination du bétail",
    ]),
    ("Infrastructures économiques", "Énergie", "energie", (10_000, 35_000), [
        "Électrification solaire du centre de santé",
        "Lampadaires solaires (30 unités)",
        "Kit solaire pour l'école primaire",
        "Plateforme multifonctionnelle",
    ]),
    ("Infrastructures économiques", "Infrastructures marchandes", "economie", (20_000, 55_000), [
        "Construction de hangars de marché",
        "Boutique de fourniture d'intrants agricoles",
        "Aire d'abattage aménagée",
        "Gare routière aménagée",
    ]),
    ("Gouvernance et cohésion sociale", "Cohésion sociale", "cohesion", (5_000, 30_000), [
        "Centre communautaire polyvalent",
        "Terrain de sport pour les jeunes",
        "Dialogue intercommunautaire agriculteurs-éleveurs",
        "Radio communautaire de proximité",
    ]),
    ("Environnement et climat", "Environnement", "environnement", (4_000, 20_000), [
        "Reboisement communautaire (10 ha)",
        "Diffusion de foyers améliorés (200 ménages)",
        "Protection des berges du cours d'eau",
        "Dispositif de gestion des déchets",
    ]),
]

CLIMATE_NOTES = [
    "Réduit la pression sur la ressource en eau en saison sèche.",
    "Limite la coupe du bois de chauffe et les émissions associées.",
    "Améliore la résilience des ménages face aux sécheresses récurrentes.",
    "Protège les sols contre l'érosion consécutive aux pluies violentes.",
]

RESPONSIBLE_STRUCTURES = [
    "Comité villageois de développement (CVD)",
    "Comité cantonal de développement (CCD)",
    "Mairie de la commune",
    "Direction préfectorale de la planification",
]

# --------------------------------------------------------------------------
# CDD planning cycle — phases / activities / tasks replicated per village.
# --------------------------------------------------------------------------

PLANNING_CYCLE = [
    ("Diagnostic participatif", [
        ("Information et mobilisation communautaire", [
            "Réunion d'information villageoise",
            "Mise en place du comité villageois de développement",
        ]),
        ("Collecte des données villageoises", [
            "Recensement des ménages et de la population",
            "Inventaire des équipements et infrastructures",
            "Cartographie participative du terroir",
        ]),
    ]),
    ("Planification et priorisation", [
        ("Assemblée villageoise de priorisation", [
            "Focus groupes femmes et jeunes",
            "Vote et classement des priorités",
        ]),
        ("Élaboration du plan de développement", [
            "Rédaction du plan de développement villageois",
            "Restitution publique du plan",
        ]),
    ]),
    ("Validation et financement", [
        ("Validation cantonale", [
            "Examen du plan par le CCD",
            "Intégration au plan de développement cantonal",
        ]),
        ("Mise en place du financement", [
            "Constitution du dossier de financement",
            "Signature de la convention de financement",
        ]),
    ]),
    ("Mise en œuvre et suivi", [
        ("Exécution des travaux", [
            "Passation de marché et sélection de l'entreprise",
            "Suivi du chantier par le comité de gestion",
        ]),
        ("Suivi communautaire et clôture", [
            "Réception technique de l'ouvrage",
            "Mise en place du comité de maintenance",
        ]),
    ]),
]

TASK_DESCRIPTION = (
    "Étape du cycle de planification communautaire conduite par le comité "
    "villageois avec l'appui de l'agent de développement."
)

# --------------------------------------------------------------------------
# Funding programmes and the organisations behind them.
# --------------------------------------------------------------------------

PROGRAMMES = [
    ("COSO — Projet d'Opportunités Communautaires", "Banque mondiale / IDA", 18_500_000_000),
    ("PARSI — Résilience et sécurité communautaire", "Banque mondiale", 9_200_000_000),
    ("PNUD — Cohésion sociale Savanes", "PNUD", 3_400_000_000),
    ("PDRI — Développement rural intégré", "BAD", 6_800_000_000),
    ("FAIEJ — Emploi des jeunes ruraux", "État togolais", 1_900_000_000),
]

PARTNER_ORGS = [
    "Banque mondiale", "PNUD", "Banque africaine de développement",
    "Agence Française de Développement", "UNICEF", "PAM",
    "Coopération allemande (GIZ)", "Union européenne",
]

CONTRACTORS = [
    "ETS Kombate & Fils", "SOTRAB BTP", "Entreprise Nadjombe Construction",
    "GTB Sahel", "COGEB International", "ETS Lamboni Travaux",
]


class Command(BaseCommand):
    help = "Seed a complete fictional Togo dataset for the demo deployment."

    def add_arguments(self, parser):
        parser.add_argument(
            "--villages", type=int, default=336,
            help="Number of villages to generate (default: 336).",
        )
        parser.add_argument(
            "--priorities", type=int, default=4,
            help="Ranked priorities registered per village (default: 4).",
        )
        parser.add_argument(
            "--seed", type=int, default=20260909,
            help="PRNG seed; the same seed always rebuilds the same portal.",
        )
        parser.add_argument(
            "--password", default="DemoCOSO2026!",
            help="Password shared by every generated account.",
        )
        parser.add_argument(
            "--reset", action="store_true",
            help="Delete the existing portal content before seeding.",
        )

    def handle(self, *args, **options):
        self.rng = random.Random(options["seed"])
        self.password = options["password"]
        self.priorities_per_village = options["priorities"]
        target_villages = options["villages"]

        # Creating a User fires the registration signal, which sends a welcome
        # mail. Seeding must never reach a real inbox, so mail is captured in
        # memory for the duration of the command whatever EMAIL_BACKEND says.
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
        ), transaction.atomic():
            if options["reset"]:
                self._reset()

            categories, sectors = self._create_sectors()
            orgs = self._create_organisations()
            users = self._create_users(orgs)
            projects = self._create_projects(orgs, users, categories)
            villages = self._create_administrative_tree(target_villages)
            self._create_planning_cycle(villages)
            priorities, subprojects = self._create_investments(
                villages, sectors, projects,
            )
            self._create_attachments(villages, subprojects)
            self._create_packages(users, priorities)

        self.stdout.write(self.style.SUCCESS(
            "\nSeeded the Togo demo portal:\n"
            f"  villages          {len(villages)}\n"
            f"  local priorities  {len(priorities)} "
            f"({self.priorities_per_village} per village)\n"
            f"  sub-projects      {len(subprojects)}\n"
            f"  photos            {Attachment.objects.count()}\n"
            f"  planning tasks    {Task.objects.count()}\n"
            f"  accounts          {User.objects.count()} "
            f"(password: {self.password})\n"
        ))

    # -- helpers ----------------------------------------------------------

    def _person(self):
        return f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}"

    def _reset(self):
        self.stdout.write("Clearing existing portal content…")
        PackageFundedInvestment.objects.all().delete()
        Package.objects.all().delete()
        Attachment.objects.all().delete()
        Task.objects.all().delete()
        Activity.objects.all().delete()
        Phase.objects.all().delete()
        Investment.objects.all().delete()
        # default_image points at an Attachment; clear it before the cascade.
        AdministrativeLevel.objects.update(default_image=None)
        AdministrativeLevel.objects.all().delete()
        Project.objects.all().delete()
        Sector.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Organization.objects.all().delete()

    # -- sectors ----------------------------------------------------------

    def _create_sectors(self):
        categories, sectors = {}, {}
        for category_name, sector_name, image, cost, titles in SECTORS:
            if category_name not in categories:
                categories[category_name] = Category.objects.create(
                    name=category_name,
                    description=f"Regroupement sectoriel : {category_name.lower()}.",
                )
            sector = Sector.objects.create(
                name=sector_name,
                description=f"Investissements du secteur « {sector_name} ».",
                category=categories[category_name],
            )
            sectors[sector_name] = (sector, image, cost, titles)
        self.stdout.write(
            f"  {len(categories)} categories, {len(sectors)} sectors")
        return categories, sectors

    # -- people -----------------------------------------------------------

    def _create_organisations(self):
        orgs = {
            name: Organization.objects.create(
                name=name, description=f"Partenaire technique et financier : {name}.",
            )
            for name in PARTNER_ORGS
        }
        orgs["UCP COSO"] = Organization.objects.create(
            name="Unité de coordination du projet (UCP)",
            description="Équipe nationale de coordination du programme COSO.",
        )
        return orgs

    def _create_users(self, orgs):
        """Demo accounts, one per role the portal distinguishes."""
        specs = [
            ("admin@coso-demo.tg", "Administrateur", "COSO", True, True, "UCP COSO"),
            ("moderateur@coso-demo.tg", "Essohanam", "Lamboni", False, True, "UCP COSO"),
            ("coordonnateur@coso-demo.tg", "Pyabalo", "Kombate", False, True, "UCP COSO"),
            ("banque.mondiale@coso-demo.tg", "Afi", "Mensah", False, False, "Banque mondiale"),
            ("pnud@coso-demo.tg", "Kodjo", "Agba", False, False, "PNUD"),
            ("bad@coso-demo.tg", "Tchilalo", "Douti", False, False,
             "Banque africaine de développement"),
            ("afd@coso-demo.tg", "Yao", "Nadjombe", False, False,
             "Agence Française de Développement"),
            ("unicef@coso-demo.tg", "Ama", "Kolani", False, False, "UNICEF"),
        ]
        users = {}
        for email, first, last, is_super, is_moderator, org in specs:
            user = User(
                email=email,
                username=email.split("@")[0],
                first_name=first,
                last_name=last,
                is_staff=is_super,
                is_superuser=is_super,
                is_moderator=is_moderator,
                is_approved=True,
                email_was_confirm=True,
                password_changed_once=True,
                organization=orgs.get(org),
            )
            user.set_password(self.password)
            user.save()
            users[email] = user
        self.stdout.write(f"  {len(users)} accounts")
        return users

    def _create_projects(self, orgs, users, categories):
        owner = users["admin@coso-demo.tg"]
        category_objs = list(categories.values())
        projects = []
        for index, (name, partner, amount) in enumerate(PROGRAMMES):
            start = date(2022 + index % 3, self.rng.randint(1, 12), 1)
            project = Project.objects.create(
                name=name,
                description=(
                    f"Programme financé par {partner}, intervenant dans les régions "
                    "des Savanes, de la Kara et Centrale."
                ),
                organization=orgs.get(partner.split(" /")[0], None),
                owner=owner,
                start_date=start,
                end_date=start + timedelta(days=365 * 5),
                total_amount=amount,
                implementation_partner=partner,
                source_of_financing=partner,
            )
            project.sectors.set(self.rng.sample(
                category_objs, self.rng.randint(2, len(category_objs))))
            projects.append(project)
        self.stdout.write(f"  {len(projects)} funding programmes")
        return projects

    # -- administrative tree ----------------------------------------------

    def _create_administrative_tree(self, target_villages):
        region_objs, canton_objs = {}, []

        for name, chef_lieu, _center in REGIONS:
            region_objs[name] = AdministrativeLevel.objects.create(
                name=name, type=AdministrativeLevel.REGION, rural=False,
                frontalier=name == "Savanes", main_languages="Français",
                facilitator=chef_lieu,
            )

        for pref_name, (region, chef_lieu, communes, cantons) in PREFECTURES.items():
            prefecture = AdministrativeLevel.objects.create(
                name=pref_name, type=AdministrativeLevel.PREFECTURE,
                parent=region_objs[region], rural=False,
                frontalier=region == "Savanes", facilitator=chef_lieu,
            )
            commune_objs = [
                AdministrativeLevel.objects.create(
                    name=commune, type=AdministrativeLevel.COMMUNE,
                    parent=prefecture, rural=False,
                )
                for commune in communes
            ]
            for index, canton in enumerate(cantons):
                canton_objs.append(AdministrativeLevel.objects.create(
                    name=canton, type=AdministrativeLevel.CANTON,
                    parent=commune_objs[index % len(commune_objs)],
                    rural=True, frontalier=region == "Savanes",
                    facilitator=self._person(),
                ))

        villages = self._create_villages(canton_objs, target_villages)
        self.stdout.write(
            f"  {len(region_objs)} regions, {len(PREFECTURES)} prefectures, "
            f"{len(canton_objs)} cantons, {len(villages)} villages"
        )
        return villages

    def _create_villages(self, cantons, target):
        """Spread `target` villages over the cantons, round-robin."""
        used_names, villages = set(), []
        region_center = {name: center for name, _chef, center in REGIONS}

        def village_name():
            while True:
                name = (self.rng.choice(VILLAGE_PREFIX)
                        + self.rng.choice(VILLAGE_SUFFIX))
                if name not in used_names:
                    used_names.add(name)
                    return name

        for index in range(target):
            canton = cantons[index % len(cantons)]
            region = canton.parent.parent.parent.name
            lat, lng = region_center[region]
            population = self.rng.randint(350, 4200)
            women = int(population * self.rng.uniform(0.48, 0.54))
            young = int(population * self.rng.uniform(0.38, 0.52))

            village = AdministrativeLevel.objects.create(
                name=village_name(),
                type=AdministrativeLevel.VILLAGE,
                parent=canton,
                rural=True,
                frontalier=region == "Savanes",
                facilitator=self._person(),
                total_population=population,
                population_women=women,
                population_men=population - women,
                population_young=young,
                population_elder=int(population * self.rng.uniform(0.05, 0.11)),
                population_handicap=self.rng.randint(2, 40),
                population_agriculturist=int(population * self.rng.uniform(0.45, 0.75)),
                population_pastoralist=int(population * self.rng.uniform(0.03, 0.18)),
                population_minorities=self.rng.randint(0, 120),
                main_languages=", ".join(self.rng.sample(
                    ETHNIC_GROUPS[region], self.rng.randint(1, 3))),
                latitude=round(lat + (self.rng.random() - 0.5) * 0.9, 6),
                longitude=round(lng + (self.rng.random() - 0.5) * 0.9, 6),
                identified_priority=date(2025, self.rng.randint(1, 12),
                                         self.rng.randint(1, 28)),
                infrastructure=self._infrastructure(),
                status_color=self.rng.choice([
                    AdministrativeLevel.LIME_GREEN, AdministrativeLevel.DARK_GREEN,
                    AdministrativeLevel.ORANGE, AdministrativeLevel.RED,
                ]),
                status_description=self.rng.choice([
                    AdministrativeLevel.EARLY, AdministrativeLevel.NORMAL,
                    AdministrativeLevel.NORMAL, AdministrativeLevel.LATE,
                    AdministrativeLevel.BLOCKED,
                ]),
                code_loc=f"TG-{canton.id:04d}-{index + 1:04d}",
            )
            villages.append(village)
        return villages

    def _infrastructure(self):
        """The nested shape written by `sync_service_infrastructure_togo`."""
        chance = lambda p: self.rng.random() < p  # noqa: E731
        return {
            "health_care": {
                "dispensaire": chance(0.35),
                "peripheral_care_unit": chance(0.22),
                "specialized_medical_centers": chance(0.06),
                "clinique": chance(0.04),
                "other": None,
            },
            "education": {
                "preschool": chance(0.30),
                "primary_school": chance(0.78),
                "college": chance(0.24),
                "high_school": chance(0.08),
                "other": None,
            },
            "religion": {
                "church": chance(0.62),
                "mosque": chance(0.58),
                "other": None,
            },
            "markets": {
                "shed": chance(0.31),
                "track": chance(0.54),
            },
        }

    # -- planning cycle ---------------------------------------------------

    def _create_planning_cycle(self, villages):
        """Replicate the CDD cycle per village, stopped at a random step.

        Tasks before the village's current position are completed, the current
        one is in progress, later ones are untouched — so the progress ring on
        the village profile shows a spread of real-looking states.
        """
        flat_steps = [
            (phase_index, activity_index, task_index)
            for phase_index, (_phase, activities) in enumerate(PLANNING_CYCLE)
            for activity_index, (_activity, tasks) in enumerate(activities)
            for task_index, _task in enumerate(tasks)
        ]

        phases = []
        for village in villages:
            for order, (name, _activities) in enumerate(PLANNING_CYCLE, start=1):
                phases.append(Phase(
                    village=village, order=order, name=name,
                    description=f"Phase {order} du cycle de planification communautaire.",
                ))
        Phase.objects.bulk_create(phases, batch_size=500)

        phases_by_village = {}
        for phase in Phase.objects.filter(village__in=villages).order_by("order"):
            phases_by_village.setdefault(phase.village_id, []).append(phase)

        activities = []
        for village_phases in phases_by_village.values():
            for phase_index, phase in enumerate(village_phases):
                for order, (name, _tasks) in enumerate(
                        PLANNING_CYCLE[phase_index][1], start=1):
                    activities.append(Activity(
                        phase=phase, order=order, name=name,
                        description="Activité du cycle de planification communautaire.",
                    ))
        Activity.objects.bulk_create(activities, batch_size=500)

        activities_by_phase = {}
        for activity in Activity.objects.filter(
                phase__village__in=villages).order_by("order"):
            activities_by_phase.setdefault(activity.phase_id, []).append(activity)

        tasks = []
        for village in villages:
            # How far this village has come through the cycle.
            progress = self.rng.randint(1, len(flat_steps))
            step = 0
            for phase_index, phase in enumerate(phases_by_village[village.id]):
                for activity_index, activity in enumerate(
                        activities_by_phase.get(phase.id, [])):
                    names = PLANNING_CYCLE[phase_index][1][activity_index][1]
                    for order, task_name in enumerate(names, start=1):
                        if step < progress - 1:
                            status = Task.COMPLETED
                        elif step == progress - 1:
                            # A few villages are stuck rather than progressing.
                            status = (Task.ERROR if self.rng.random() < 0.08
                                      else Task.IN_PROGRESS)
                        else:
                            status = Task.NOT_STARTED
                        tasks.append(Task(
                            activity=activity, order=order, name=task_name,
                            description=TASK_DESCRIPTION, status=status,
                        ))
                        step += 1
        Task.objects.bulk_create(tasks, batch_size=1000)
        self.stdout.write(
            f"  {len(phases)} phases, {len(activities)} activities, "
            f"{len(tasks)} tasks"
        )

    # -- investments ------------------------------------------------------

    def _create_investments(self, villages, sectors, projects):
        """Four ranked priorities per village, plus the works that followed.

        Rank 1 is the village's headline need, so it is the one most often
        funded; the tail stays unfunded and feeds the investment catalogue
        that partners browse.
        """
        sector_names = list(sectors)
        priorities, subprojects = [], []

        for village in villages:
            chosen = self.rng.sample(sector_names, self.priorities_per_village)
            for rank, sector_name in enumerate(chosen, start=1):
                sector, _image, (low, high), titles = sectors[sector_name]
                cost = self.rng.randrange(low, high, 500)
                beneficiaries = int(village.total_population
                                    * self.rng.uniform(0.35, 1.0))

                # Higher-ranked priorities are likelier to have found funding.
                funded_chance = {1: 0.55, 2: 0.30, 3: 0.15}.get(rank, 0.07)
                is_funded = self.rng.random() < funded_chance
                status = (self.rng.choice([
                    Investment.FUNDED, Investment.IN_PROGRESS,
                    Investment.IN_PROGRESS, Investment.COMPLETED,
                    Investment.COMPLETED, Investment.PAUSED,
                ]) if is_funded else Investment.NOT_FUNDED)

                priorities.append(Investment(
                    ranking=rank,
                    title=self.rng.choice(titles),
                    description=(
                        f"Priorité de rang {rank} retenue par l'assemblée "
                        f"villageoise de {village.name}, au bénéfice d'environ "
                        f"{beneficiaries} personnes."
                    ),
                    responsible_structure=self.rng.choice(RESPONSIBLE_STRUCTURES),
                    administrative_level=village,
                    sector=sector,
                    estimated_cost=cost,
                    investment_status=Investment.PRIORITY,
                    project_status=status,
                    duration=self.rng.randint(60, 420),
                    delays_consumed=0,
                    physical_execution_rate=0,
                    financial_implementation_rate=0,
                    endorsed_by_women=self.rng.random() < 0.62,
                    endorsed_by_youth=self.rng.random() < 0.55,
                    endorsed_by_agriculturist=self.rng.random() < 0.48,
                    endorsed_by_pastoralist=self.rng.random() < 0.27,
                    climate_contribution=sector_name in (
                        "Environnement", "Eau & assainissement", "Énergie"),
                    climate_contribution_text=self.rng.choice(CLIMATE_NOTES),
                    latitude=float(village.latitude),
                    longitude=float(village.longitude),
                    funded_by=self.rng.choice(projects) if is_funded else None,
                    no_sql_id="",
                    start_date=(date(2025, self.rng.randint(1, 12),
                                     self.rng.randint(1, 28))
                                if is_funded else None),
                ))
        Investment.objects.bulk_create(priorities, batch_size=500)

        # The funded priorities are the ones that became actual works.
        funded = list(Investment.objects.filter(
            investment_status=Investment.PRIORITY,
        ).exclude(project_status=Investment.NOT_FUNDED).select_related(
            "administrative_level", "sector"))

        for source in funded:
            status = source.project_status
            if status == Investment.COMPLETED:
                physical, financial = 100, self.rng.randint(92, 100)
            elif status == Investment.IN_PROGRESS:
                physical = self.rng.randint(15, 90)
                financial = max(0, physical - self.rng.randint(0, 18))
            elif status == Investment.PAUSED:
                physical = self.rng.randint(10, 55)
                financial = max(0, physical - self.rng.randint(0, 12))
            else:  # freshly funded, work not started
                physical, financial = 0, self.rng.randint(0, 25)

            duration = self.rng.randint(90, 480)
            subprojects.append(Investment(
                ranking=source.ranking,
                title=source.title,
                description=(
                    f"Sous-projet issu de la priorité de rang {source.ranking} "
                    f"du village de {source.administrative_level.name}."
                ),
                responsible_structure=self.rng.choice(CONTRACTORS),
                administrative_level=source.administrative_level,
                sector=source.sector,
                estimated_cost=source.estimated_cost,
                real_cost=int(source.estimated_cost
                              * self.rng.uniform(0.94, 1.14)),
                investment_status=Investment.SUBPROJECT,
                project_status=status,
                duration=duration,
                delays_consumed=int(duration * physical / 100)
                + self.rng.randint(0, 40),
                physical_execution_rate=physical,
                financial_implementation_rate=financial,
                endorsed_by_women=source.endorsed_by_women,
                endorsed_by_youth=source.endorsed_by_youth,
                endorsed_by_agriculturist=source.endorsed_by_agriculturist,
                endorsed_by_pastoralist=source.endorsed_by_pastoralist,
                climate_contribution=source.climate_contribution,
                climate_contribution_text=source.climate_contribution_text,
                latitude=source.latitude,
                longitude=source.longitude,
                funded_by=source.funded_by,
                no_sql_id="",
                start_date=source.start_date,
            ))
        Investment.objects.bulk_create(subprojects, batch_size=500)

        self.stdout.write(
            f"  {len(priorities)} priorities, {len(subprojects)} sub-projects")
        return priorities, subprojects

    # -- photo library ----------------------------------------------------

    def _create_attachments(self, villages, subprojects):
        """Attach procedurally drawn scenes to villages and works.

        `Attachment.url` is a plain URL column, so the demo points it at the
        static files shipped with the deployment instead of an S3 bucket.
        """
        sector_image = {name: image for _cat, name, image, _cost, _titles in SECTORS}
        attachments = []

        for village in villages:
            for order in range(3):
                scene = self.rng.randint(1, 8)
                attachments.append(Attachment(
                    adm=village,
                    url=f"/static/images/demo/villages/village-{scene}.svg",
                    type=Attachment.PHOTO,
                    process_moment=Attachment.COMMUNITY_PROCESS,
                    name=f"{village.name} — processus communautaire {order + 1}",
                    description=(
                        "Assemblée villageoise et travaux de diagnostic "
                        f"participatif à {village.name}."
                    ),
                    order=order,
                    source="demo",
                ))

        works = Investment.objects.filter(
            investment_status=Investment.SUBPROJECT
        ).select_related("administrative_level", "sector")
        for work in works:
            image = sector_image.get(work.sector.name, "eau")
            if work.project_status == Investment.COMPLETED:
                moments = [Attachment.INFRASTRUCTURE_IN_PROGRESS,
                           Attachment.COMPLETED_INFRASTRUCTURE]
            elif work.project_status in (Investment.IN_PROGRESS, Investment.PAUSED):
                moments = [Attachment.INFRASTRUCTURE_IN_PROGRESS]
            else:
                moments = [Attachment.COMMUNITY_PROCESS]
            for order, moment in enumerate(moments):
                attachments.append(Attachment(
                    adm=work.administrative_level,
                    investment=work,
                    url=(f"/static/images/demo/secteurs/{image}-"
                         f"{self.rng.randint(1, 3)}.svg"),
                    type=Attachment.PHOTO,
                    process_moment=moment,
                    name=f"{work.title} — {work.administrative_level.name}",
                    description=work.description,
                    order=order,
                    source="demo",
                ))

        Attachment.objects.bulk_create(attachments, batch_size=1000)

        # Give every village a cover photo for the list and gallery views.
        covers = {}
        for attachment in Attachment.objects.filter(
                adm__in=villages, process_moment=Attachment.COMMUNITY_PROCESS):
            covers.setdefault(attachment.adm_id, attachment)
        for village in villages:
            cover = covers.get(village.id)
            if cover:
                village.default_image = cover
        AdministrativeLevel.objects.bulk_update(
            villages, ["default_image"], batch_size=500)

        self.stdout.write(f"  {len(attachments)} photos")

    # -- investor carts ---------------------------------------------------

    def _create_packages(self, users, priorities):
        """A handful of funding baskets in each state of the approval flow."""
        investors = [user for email, user in users.items()
                     if not user.is_moderator and not user.is_superuser]
        moderator = users["moderateur@coso-demo.tg"]
        catalogue = list(Investment.objects.filter(
            investment_status=Investment.PRIORITY,
            project_status=Investment.NOT_FUNDED,
        ).values_list("id", flat=True))

        states = [
            (Package.PENDING_APPROVAL, PackageFundedInvestment.PENDING_APPROVAL),
            (Package.APPROVED, PackageFundedInvestment.APPROVED),
            (Package.REJECTED, PackageFundedInvestment.REJECTED),
            (Package.PENDING_SUBMISSION, PackageFundedInvestment.PENDING_APPROVAL),
        ]

        created = 0
        for investor in investors:
            for status, line_status in states:
                package = Package.objects.create(
                    user=investor,
                    status=status,
                    draft_status=status == Package.PENDING_SUBMISSION,
                    source=(investor.organization.name
                            if investor.organization else None),
                    review_by=moderator if status in (
                        Package.APPROVED, Package.REJECTED) else None,
                    rejection_reason=("Enveloppe déjà engagée sur un autre canton."
                                      if status == Package.REJECTED else None),
                )
                for investment_id in self.rng.sample(catalogue, self.rng.randint(2, 5)):
                    PackageFundedInvestment.objects.create(
                        package=package,
                        investment_id=investment_id,
                        status=line_status,
                    )
                created += 1
        self.stdout.write(f"  {created} investment packages")
