import pandas as pd
import requests
import time
import math
import folium
import streamlit as st
import json
import urllib.request
import datetime as dt
from config import *
from typing import  Dict, List,Sequence, Tuple, Optional


#retourne un dictionnaire avec les noms des flux et leurs URL à partir de l'index GBFS: {feed_name: feed_url}
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def getFeeds(index_url=GBFS_INDEX, lang= "fr")-> dict:
    r = requests.get(index_url, timeout=20)
    response = requests.get(GBFS_INDEX, timeout=20)
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
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()

#Charge station_information + station_status et renvoie (info_df, status_df, merged_df).
#   merged_df inclut les colonnes :
#   station_id, name, lat, lon, capacity,
#   num_bikes_available, num_docks_available, ebike, mechanical,
#   is_renting, is_returning
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_bixi_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    feeds = getFeeds()  
    info = fetch_json(feeds["station_information"]) 
    status = fetch_json(feeds["station_status"])
    df_info = pd.DataFrame(info["data"]["stations"])
    df_status = pd.DataFrame(status["data"]["stations"])
    df_merged = pd.merge(df_info, df_status, on="station_id", how="inner")
    return df_merged


def choose_station_color(n_bikes_available: int, orange_max: int = ORANGE_MAX) -> str:
    if n_bikes_available== 0:
        return "red"
    if 1 <= n_bikes_available <= orange_max:
        return "orange"
    return "green"

# Géocodage via Nominatim (respecte User-Agent). Retourne [lat, lon] ou ''."""
def geocode(address: str)-> Tuple[float, float]|str:
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "bixi-live-tracker/1.0 (edu project)"},
            timeout=20,)
        r.raise_for_status()
        results = r.json()
        if not results:
            return [float(results[0]["lat"]), float(results[0]["lon"])]
    except Exception:
        return ''

#calcule distance en mètres entre deux points, lat et lon
def calculate_distance(coord1: Sequence[float], coord2: Sequence[float]) -> float:
    R = 6371000.0  # Rayon moyen de la Terre en mètres
    lat1= math.radians(coord1[0])
    lon1 = math.radians(coord1[1])
    lat2 = math.radians(coord2[0])
    lon2 =  math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance

def get_bike_availability(user_location: Sequence[float], stations_df: pd.DataFrame, bike_types: List[str]) -> Tuple[str, float, float] | None:    
    pass
    pass
def get_dock_availability(df: pd.DataFrame, station_id: str) -> Optional[int]:
    pass

def run_osrm(chosen_station: Tuple[str, float, float]| None, origin: Sequence[float]):
    pass

"""
def choose_station_color(bikes_available: int, orange_max: int = ORANGE_MAX) -> str:
    if bikes_available== 0:
        return "red"
    if 1 <= bikes_available <= orange_max:
        return "orange"
    return "green"

def enrich_modes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ebike"]=0

    pass

"""


