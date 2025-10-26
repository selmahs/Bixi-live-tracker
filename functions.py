from config import *
from typing import Dict
import pandas as pd
import requests
import time
import folium
import streamlit as st


#retourne un dictionnaire avec les noms des flux et leurs URL à partir de l'index GBFS: {feed_name: feed_url}
def getFeeds(index_url=GBFS_INDEX, lang= "fr")-> dict:
    response = requests.get(GBFS_INDEX)
    response.raise_for_status()
    root = response.json()

    data = root.get("data", {})
    # dictionnaire qui contient la langue
    lang_data = data.get(lang, {}) 
    # liste des dictionnaires:system_information , system_alert, station_status, vehicule_types , station_information
    feeds_list = lang_data.get("feeds", []) 
    #avec dictionnaire affichage: "station_information": "https://.../station_information.json",
    return  {feed["name"]: feed["url"] for feed in feeds_list}


#telechargement et retourne des données json à partir d'une URL
def fetch_json(url: str) -> dict:
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

#charge les données des stations et retourne un DataFrame fusionné avec les informations et le statut des stations
def load_data() -> pd.DataFrame:
    feeds = getFeeds()  
    info = fetch_json(feeds["station_information"]) 
    status = fetch_json(feeds["station_status"])
    df_info = pd.DataFrame(info["data"]["stations"])
    df_status = pd.DataFrame(status["data"]["stations"])
    df_merged = pd.merge(df_info, df_status, on="station_id", how="inner")
    return df_merged

def choose_station_color(bikes_available: int, orange_max: int = ORANGE_MAX) -> str:
    if bikes_available== 0:
        return "red"
    if 1 <= bikes_available <= orange_max:
        return "orange"
    return "green"



