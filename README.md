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

Ce projet permet de visualiser en temps réel la disponibilité des vélos BIXI à Montréal.
Il facilite la planification des déplacements urbains en aidant les utilisateurs à trouver rapidement une station avec des vélos ou des bornes libres à proximité.
Le projet permet aussi de choisir entre un vélo mécanique ou un e-bike, afin d’afficher seulement les stations qui en offrent.

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

## Données exploité
Le site repose sur des données ouvertes fournies par BIXI Montréal via la spécification GBFS (General Bikeshare Feed Specification) — un standard mondial utilisé par la plupart des services de vélopartage.<br>

📡 Source principale :<br>
GBFS_INDEX = "https://gbfs.velobixi.com/gbfs/2-2/gbfs.json"<br>

Cette URL agit comme un index qui liste tous les flux JSON publics disponibles (sous licence open data), notamment :

station_information.json → contient les métadonnées de chaque station (nom, coordonnées, capacité totale, etc.)

station_status.json → fournit l’état en temps réel des stations (vélos disponibles, bornes libres, types de vélos, etc.)

## Fonctionnalités principales
<h2 align="center">🌍 Aperçu du site</h2>
<p align="center">
  <img src="./apercuSite.png" alt="Aperçu du site BIXI Live Tracker" width="600">
</p>
###  🗺️Carte interactive
Affiche toutes les stations BIXI avec un code couleur : rouge (aucun vélo), orange (peu de vélos), vert (disponibilité normale).
### 🚲 Séparation e-bike / mécanique
Les vélos électriques (**ebike**) et mécaniques (**mechanical**) sont comptés séparément.
### 📊 Indicateurs clés (KPI)
Totaux de vélos, d’e-bikes, de stations actives et de bornes libres.
### 📍 Recherche géographique
Permet de saisir une adresse pour trouver la station la plus proche.
### 🚶Itinéraire automatique
Affiche un trajet piéton et la durée estimée grâce à l’API OSRM.

## 🧰 Technologies
- **Langage :** Python 3.12  
- **Framework :** Streamlit  
- **Librairies principales :** pandas, folium, requests  
- **API :** GBFS (BIXI Montréal), OSRM (itinéraires)