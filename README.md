# Bixi-live-tracker

## Ce que le projet fait

BIXI Live Tracker est un site web interactif construit avec Streamlit.
Il affiche en temps réel la disponibilité des vélos dans les stations BIXI de Montréal, à partir du flux officiel GBFS (General Bikeshare Feed Specification).<br>

Le site permet de :<br>

- Visualiser toutes les stations sur une carte dynamique.<br>

- Distinguer les vélos mécaniques et les vélos électriques (e-bikes).<br>

- Trouver la station la plus proche pour louer ou retourner un vélo.<br>

- Consulter des indicateurs clés sur la flotte BIXI en direct.<br> 

## Pourquoi le projet est utile


## Prise en main du projet 

<ins> Installation :</ins> <br>

```
# Cloner le dépôt
git clone https://github.com/<votre-nom>/bixi-live-tracker.git
cd bixi-live-tracker

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

```
<ins>Lancement de l'application:</ins> <br>

```
streamlit run app.py
```
Le site sera accessible sur<br>
👉 http://localhost:8501

## Fonctionnalités principales

### Carte interactive
Affiche toutes les stations BIXI avec un code couleur : rouge (aucun vélo), orange (peu de vélos), vert (disponibilité normale).
### Séparation e-bike / mécanique
Les vélos électriques (**ebike**) et mécaniques (**mechanical**) sont comptés séparément.
### Indicateurs clés (KPI)
Totaux de vélos, d’e-bikes, de stations actives et de bornes libres.
### Recherche géographique
Permet de saisir une adresse pour trouver la station la plus proche.
### Itinéraire automatique
Affiche un trajet piéton et la durée estimée grâce à l’API OSRM.