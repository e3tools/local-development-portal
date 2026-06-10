# Journal des modifications - 9 juin 2026

Ce document détaille les modifications apportées au système aujourd'hui.

## Corrections et améliorations

### 1. Correction de l'import manquant dans cosomis/views.py

**Problème** : Le décorateur `@login_required` était utilisé sans avoir été importé, causant une erreur `NameError` au démarrage du serveur.

**Solution** : Ajout de l'import manquant dans le fichier `cosomis/views.py` :
```python
from django.contrib.auth.decorators import login_required
```

**Fichiers modifiés** :
- `cosomis/views.py`

---

### 2. Internationalisation de la modal de dépassement de budget

**Contexte** : La modal d'alerte de dépassement de budget sur la page "Financer un projet" s'affichait uniquement en français, même lorsque l'utilisateur sélectionnait l'anglais comme langue.

**Modifications apportées** :

#### Template HTML (`investments/templates/investments/list.html`)
Remplacement de tous les textes en dur par des tags de traduction Django :
- Titre de la modal : `{% translate 'Budget exceeded!' %}`
- Message d'explication : `{% translate 'The selected funding exceeds...' %}`
- Libellés : `{% translate 'Available funds' %}`, `{% translate 'Selected funding' %}`, `{% translate 'Overage' %}`
- Bouton : `{% translate 'Close' %}`

#### Fichiers de traduction
**Français** (`locale/fr/LC_MESSAGES/django.po`) :
- Budget exceeded! → Budget dépassé !
- Available funds → Fonds disponibles
- Selected funding → Financement sélectionné
- Overage → Dépassement


### 3. Éclatement de l'affichage du montant total des investissements

**Besoin** : Sur la page de détail d'un projet, l'utilisateur voit trois informations distinctes au lieu d'une seule carte "Montant total des investissements" :
1. Le budget total du projet
2. Le montant déjà engagé (investissements dans des paquets approuvés ou en attente)
3. Le montant disponible (budget - engagé)

Le montant engagé inclut :
- Les investissements avec statut `PENDING_APPROVAL` (en attente d'approbation)
- Les investissements avec statut `APPROVED` (approuvés)

#### Modifications frontend (`administrativelevels/templates/project/detail.html`)
Remplacement de l'unique carte verte par trois cartes distinctes :

**1. Budget du projet** (carte bleue avec icône wallet)
- Affiche : `project.total_amount`
- Libellé : "Budget du projet" / "Project Budget"

**2. Déjà engagé** (carte rouge avec icône lock)
- Affiche : `already_committed`
- Libellé : "Déjà engagé" / "Already Committed"

**3. Fonds disponibles** (carte verte avec icône money-bill)
- Affiche : `available_funds`
- Libellé : "Fonds disponibles" / "Available Funds"

La quatrième carte "Dernière mise à jour" reste inchangée.

#### Traductions ajoutées
**Français** :
- Project Budget → Budget du projet
- Already Committed → Déjà engagé
- Available Funds → Fonds disponibles

---
