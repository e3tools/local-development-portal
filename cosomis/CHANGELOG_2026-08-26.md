# Journal des modifications - 26 août 2026

Ce document détaille les modifications apportées au système aujourd'hui, sur la branche `fix/investment-rejection-sync`.

## Corrections et améliorations

### 1. Affichage du statut par sous-projet sur la page de détail d'un paquet

**Problème** : Sur la page "Packages > Détail" (`investments:package_detail`) consultée par l'utilisateur de l'organisation, le tableau des investissements n'affichait aucun statut individuel. Quand un paquet était "Partiellement traité", il était impossible de savoir quel(s) sous-projet(s) avaient été approuvés ou rejetés — contrairement à la page de revue du modérateur qui affiche cette information par ligne.

**Solution** :
- `PackageDetailView.get_context_data` (`investments/views.py`) fournit désormais `package_investments` (les lignes `PackageFundedInvestment`, qui portent le statut par sous-projet), en plus du total de financement qui exclut maintenant les sous-projets rejetés.
- Le template `investments/templates/investments/package.html` boucle sur cette nouvelle liste, ajoute une colonne **Statut** avec badges Approuvé/Rejeté/En attente, et reprend le popup d'affichage de la raison de rejet (modal + JS) du template de revue du modérateur.

**Fichiers modifiés** :
- `investments/views.py`
- `investments/templates/investments/package.html`

---

### 2. Tableau "Financer un projet" tronqué — colonnes non visibles

**Problème** : Sur la page "Financer un projet" (`investments:home_investments`), le tableau des investissements (11 colonnes) était rogné sur la droite sans aucune barre de défilement horizontale — les colonnes "Priorité de la population" et "Historique" étaient inaccessibles.

**Cause** : Le conteneur `.investments-table-stage` avait une règle `overflow: hidden`, qui rognait silencieusement le tableau dès que sa largeur naturelle dépassait celle de la carte, au lieu de laisser défiler ou de replier proprement les colonnes via le mécanisme responsive de DataTables.

**Solution** : Remplacement par `overflow-x: auto; overflow-y: hidden;` pour permettre le défilement horizontal jusqu'aux colonnes manquantes, sans affecter le positionnement de l'overlay de chargement (squelette).

**Fichiers modifiés** :
- `investments/templates/investments/list.html`

---

### 3. Montants et compteurs non mis à jour après le rejet d'un investissement

**Problème** : Quand un sous-projet était rejeté par un modérateur, `PackageFundedInvestment.reject()` vidait bien `investment.funded_by` / `investment.project_status`, mais conservait la ligne du paquet (statut passé à "Rejeté", sans suppression). Plusieurs agrégats parcouraient encore l'ancienne relation many-to-many `Package.funded_investments` sans filtrer ce statut, et continuaient donc à compter/sommer les investissements rejetés :
- La page **Liste des projets** (colonnes "Nombre d'investissements" / "Total des fonds" et le total en pied de tableau).
- `Package.estimated_final_cost()`, utilisé sur 4 pages (onglet Paquets du projet, listes de revue du modérateur et de l'investisseur).
- Le total "Total funding selected" sur la page de détail d'un paquet.
- Les totaux d'investissements par organisation et par utilisateur sur la page Profil.

**Solution** : Chaque requête concernée filtre désormais explicitement sur le statut du paquet (`PENDING_APPROVAL` ou `APPROVED`, en excluant `REJECTED`), en s'appuyant sur la table de liaison `PackageFundedInvestment` plutôt que sur la relation many-to-many brute.

**Vérification** : sur le projet "FACILITE DE PRÉVENTION POUR LE GOLFE DE GUINNE" (paquet contenant un sous-projet rejeté de 20 000 000 FCFA), la liste des projets passe de `2 investissements / 70 000 000 FCFA` à `1 investissement / 50 000 000 FCFA` une fois la correction appliquée.

**Fichiers modifiés** :
- `administrativelevels/views.py` (`ProjectListView`)
- `investments/models.py` (`Package.estimated_final_cost`)
- `investments/views.py` (`PackageDetailView`, `ProfileTemplateView`)

---
