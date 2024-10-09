#### French Version
# Manuel d'Utilisation : Comment Utiliser le Modèle CSV pour Télécharger des Investissements

Ce guide explique comment remplir le modèle CSV pour télécharger des données d'investissement sur la plateforme. Vous apprendrez également comment utiliser des fichiers complémentaires pour obtenir les identifiants de village et de secteur, et comment enregistrer correctement votre fichier CSV à l'aide de **Microsoft Excel** pour un téléchargement réussi.

## Qu'est-ce qu'un CSV ?

CSV (Comma Separated Values) est un format de fichier utilisé pour stocker des données tabulaires telles que des chiffres et du texte. Chaque ligne dans un fichier CSV correspond à une ligne dans un tableau, et les valeurs sont séparées par des virgules. C'est un format simple et largement utilisé pour échanger des données entre différents systèmes.

### Comment Ouvrir et Manipuler le Fichier CSV avec Excel

#### Ouvrir le Fichier CSV dans Excel

1. Ouvrez **Microsoft Excel**.
2. Cliquez sur **Fichier** dans le coin supérieur gauche de l'écran.
3. Cliquez sur **Ouvrir** dans le menu.
4. Dans la boîte de dialogue de fichier, naviguez jusqu'à l'emplacement où le fichier CSV est enregistré.
5. Si vous ne voyez pas le fichier CSV dans la liste, assurez-vous que le menu déroulant du type de fichier (à côté de la zone du nom de fichier) est réglé pour afficher **Tous les fichiers** ou **Fichiers CSV**.
6. Sélectionnez le fichier CSV (par exemple, `projet_investissements_modele.csv`) et cliquez sur **Ouvrir**.

Excel ouvrira le fichier, affichant les données dans un format tabulaire similaire à une feuille de calcul.

#### Remplir le Fichier CSV dans Excel

- Vous pouvez maintenant éditer le fichier CSV comme n'importe quelle feuille de calcul Excel. Saisissez les données requises dans les colonnes respectives (reportez-vous aux instructions ci-dessous pour savoir comment remplir chaque champ).
- Soyez prudent avec l'utilisation de formats spéciaux (par exemple, gras, couleurs), car cela ne sera pas enregistré dans le fichier CSV.

#### Enregistrer le Fichier

1. Après avoir rempli les champs, cliquez sur **Fichier** > **Enregistrer sous**.
2. Dans la boîte de dialogue, sélectionnez l'emplacement où vous souhaitez enregistrer le fichier.
3. Dans le menu déroulant "Type de fichier", sélectionnez **CSV (délimité par des virgules) (*.csv)**.
4. Cliquez sur **Enregistrer**. Excel peut afficher un avertissement disant "Certaines fonctionnalités de votre classeur pourraient être perdues si vous l'enregistrez en CSV." Ceci est normal ; cliquez sur **Oui** pour continuer l'enregistrement du fichier au format CSV.

---

## Instructions pour Remplir le Modèle CSV

### Champs dans le CSV

1. **Classement** :
   - Entrez la priorité ou le rang de l'investissement sous forme de valeur numérique (par exemple, 1, 2, 3).

2. **Identifiant du Village** :
   - Chaque village a un `village_id` unique. Utilisez le fichier complémentaire fourni pour trouver le `village_id` correct correspondant à votre village cible.

3. **Titre** :
   - Entrez le titre du projet d'investissement (par exemple, "Rénovation de l'école"). Il doit s'agir d'un titre court et descriptif.

4. **Structure Responsable** :
   - Fournissez le nom de l'entité ou du département responsable de la mise en œuvre du projet d'investissement (par exemple, "Ministère de la Santé").

5. **Identifiant du Secteur** :
   - Chaque secteur (par exemple, éducation, santé) a un `sector_id` unique. Reportez-vous au fichier complémentaire des identifiants de secteur pour trouver le `sector_id` correct pour votre projet.

6. **Coût Estimé** :
   - Entrez le coût estimé de l'investissement en monnaie locale (par exemple, 500000 pour cinq cent mille).

7. **Date de Début** :
   - Spécifiez la date de début du projet au format `AAAA-MM-JJ` (par exemple, 2023-01-31).

8. **Durée** :
   - Entrez la durée prévue du projet en jours (par exemple, 30 pour un projet d'un mois).

9. **Retards Consommés** :
   - Entrez le nombre de jours de retard du projet, le cas échéant. Utilisez "0" s'il n'y a eu aucun retard.

10. **Taux d'Exécution Physique** :
    - Entrez l'avancement physique du projet en pourcentage (de 0 à 100). Par exemple, entrez `50` si le projet est à mi-parcours.

11. **Taux de Mise en Œuvre Financière** :
    - Entrez le pourcentage de fonds qui ont été décaissés pour le projet par rapport au coût total estimé (de 0 à 100). Par exemple, `40` signifie que 40 % des fonds ont été dépensés.

12. **Statut du Projet** :
    - Choisissez le statut du projet parmi les options suivantes et entrez la lettre correspondante :
      - **N** : Non financé
      - **F** : Financé
      - **I** : En cours
      - **C** : Terminé
      - **P** : Suspendu

## Fichiers Complémentaires

- **Identifiants des Villages** : Un fichier séparé est fourni avec une liste de villages et leurs `village_id` correspondants. Utilisez ce fichier pour localiser l'ID correct pour votre investissement.

- **Identifiants des Secteurs** : Un autre fichier est fourni avec une liste de secteurs et leurs `sector_id` correspondants. Utilisez ce fichier pour vous assurer que vous sélectionnez le bon secteur pour l'investissement.

---

## Comment Télécharger le Fichier CSV

- Après avoir rempli le CSV, assurez-vous que tous les champs sont corrects et bien formatés.
- Enregistrez le fichier au format CSV (délimité par des virgules) (*.csv) en suivant les étapes décrites ci-dessus.
- Allez dans la section de téléchargement de la plateforme et suivez les instructions pour télécharger votre fichier CSV.
- Le système traitera le fichier et affichera les résultats, indiquant si le téléchargement a réussi ou si des erreurs sont survenues.

---

Pour toute question ou assistance, veuillez contacter le support.

---

#### English Version

# User Manual: How to Use the CSV Template for Uploading Investments

This guide explains how to fill out the CSV template for uploading investment data to the platform. You will also learn how to use complementary files to obtain village and sector IDs, and how to correctly save your CSV file using **Microsoft Excel** for a successful upload.

## What is a CSV?

CSV (Comma Separated Values) is a file format used to store tabular data such as numbers and text. Each line in a CSV file corresponds to a row in a table, and the values are separated by commas. It is a simple, widely used format for exchanging data between different systems.

### How to Open and Handle the CSV File Using Excel

#### Opening the CSV File in Excel

1. Open **Microsoft Excel**.
2. Click on **File** in the top-left corner of the screen.
3. Click **Open** from the menu.
4. In the file dialog box, navigate to the location where the CSV file is saved.
5. If you do not see the CSV file in the list, ensure that the file type dropdown (next to the file name box) is set to show **All Files** or **CSV files**.
6. Select the CSV file (e.g., `project_investments_template.csv`) and click **Open**.

Excel will open the file, displaying the data in a tabular format similar to a spreadsheet.

#### Filling Out the CSV in Excel

- You can now edit the CSV file just like any Excel spreadsheet. Enter the required data in the respective columns (refer to the instructions below on how to fill each field).
- Be cautious about using special formatting (e.g., bold, colors), as this will not be saved in the CSV file.

#### Saving the File

1. After filling in the fields, click **File** > **Save As**.
2. In the dialog box, select the location where you want to save the file.
3. From the “Save as type” dropdown menu, select **CSV (Comma delimited) (*.csv)**.
4. Click **Save**. Excel may show a warning saying "Some features in your workbook might be lost if you save it as CSV." This is normal; click **Yes** to proceed with saving the file in CSV format.

---

## Instructions for Filling Out the CSV Template

### Fields in the CSV

1. **Ranking**:
   - Enter the priority or rank of the investment as a numeric value (e.g., 1, 2, 3).

2. **Village ID**:
   - Each village has a unique `village_id`. Use the complementary file provided to find the correct `village_id` corresponding to your targeted village.

3. **Title**:
   - Enter the title of the investment project (e.g., "School Renovation"). This should be a short and descriptive title.

4. **Responsible Structure**:
   - Provide the name of the entity or department responsible for implementing the investment project (e.g., "Ministry of Health").

5. **Sector ID**:
   - Each sector (e.g., education, healthcare) has a unique `sector_id`. Refer to the complementary sector ID file to find the correct `sector_id` for your project.

6. **Estimated Cost**:
   - Enter the estimated cost of the investment in local currency (e.g., 500000 for five hundred thousand).

7. **Start Date**:
   - Specify the start date of the project in the format `YYYY-MM-DD` (e.g., 2023-01-31).

8. **Duration**:
   - Enter the planned duration of the project in days (e.g., 30 for a month-long project).

9. **Delays Consumed**:
   - Enter the number of days the project has been delayed, if applicable. Use "0" if there have been no delays.

10. **Physical Execution Rate**:
    - Enter the physical progress of the project as a percentage (from 0 to 100). For example, enter `50` if the project is halfway done.

11. **Financial Implementation Rate**:
    - Enter the percentage of funds that have been disbursed for the project compared to the total estimated cost (from 0 to 100). For example, `40` means 40% of the funds have been spent.

12. **Project Status**:
    - Choose the project status from the following options and enter the corresponding letter:
      - **N**: Not Funded
      - **F**: Funded
      - **I**: In Progress
      - **C**: Completed
      - **P**: Paused


## Complementary Files 

- **Village IDs:** A separate file is provided with a list of villages and their corresponding village_id. Use this file to locate the correct ID for your investment. 

- **Sector IDs:** Another file is provided with a list of sectors and their corresponding sector_id. Use this file to ensure you are selecting the correct sector for the investment.

---

## How to Upload the CSV File

- After filling out the CSV, ensure that all fields are correct and properly formatted.
- Save the file in CSV (Comma delimited) (*.csv) format using the steps described above.
- Go to the upload section of the platform and follow the prompts to upload your CSV file.
- The system will process the file and display the results, indicating whether the upload was successful or if any errors occurred.

---
For further questions or assistance, please contact support.