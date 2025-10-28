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

    feed_map: Dict[str, str] = getFeeds()  
    station_info_url: str | None = feed_map.get("station_information")
    station_status_url: str | None = feed_map.get("station_status")
    if not station_info_url or not station_status_url:
        raise RuntimeError(
            "Flux GBFS requis introuvables (station_information / station_status)"
        )
    station_info_list = fetch_json(station_info_url).get("data", {}).get("stations", [])
    station_status_list = fetch_json(station_status_url).get("data", {}).get("stations", [])

    station_info_df = pd.DataFrame(station_info_list)
    station_status_df = pd.DataFrame(station_status_list)

    for coord in ("lat", "lon"):
        if coord in station_info_df.columns:
            station_info_df[coord] = pd.to_numeric(station_info_df[coord], errors="coerce")
    for col in ("num_bikes_available", "num_docks_available"):
        if col in station_status_df.columns:
            station_status_df[col] = (
                pd.to_numeric(station_status_df[col], errors="coerce")
                .fillna(0)
                .astype(int)
            )
        else:
            station_status_df[col] = 0

    has_type_breakdown = "num_bikes_available_types" in station_status_df.columns
    ebike_counts: list[int] = []
    mechanical_counts: list[int] = []

    for i, station in station_status_df.iterrows():
        ebikes = 0
        mechanical = 0
        types_obj = station.get("num_bikes_available_types")

        if has_type_breakdown and isinstance(types_obj, dict):
            ebikes = int(types_obj.get("ebike", 0))
            mechanical = int(types_obj.get("mechanical", 0))
        else:
            mechanical = int(station.get("num_bikes_available", 0))

        ebike_counts.append(ebikes)
        mechanical_counts.append(mechanical)

    station_status_df["ebike"] = ebike_counts
    station_status_df["mechanical"] = mechanical_counts

    for state_col in ("is_renting", "is_returning"):
        if state_col not in station_status_df.columns:
            station_status_df[state_col] = 1

    stations_df = station_info_df.merge(
        station_status_df,
        on="station_id",
        how="left",
        suffixes=("", "_status"),
    )

    columns_to_keep = ["station_id", "name", "lat", "lon", "capacity","num_bikes_available", "num_docks_available", "ebike", "mechanical", "is_renting", "is_returning"]
    for col in columns_to_keep:
        if col not in stations_df.columns:
            stations_df[col] = 0 if col not in ("name", "lat", "lon") else None

    for col in ("num_bikes_available", "num_docks_available","ebike", "mechanical", "is_renting", "is_returning"):
        stations_df[col] = (pd.to_numeric(stations_df[col], errors="coerce").fillna(0).astype(int))

    return station_info_df, station_status_df, stations_df[columns_to_keep]

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



#   Trouve la station la plus proche qui respecte la demande:  
#   - bike_types peut contenir 'ebike' et/ou 'mechanical';
#   - si vide, n'importe quel vélo (>0) convient.
#   Retour: (station_id, lat, lon) ou None.

def get_bike_availability(user_location: Sequence[float], stations_df: pd.DataFrame, bike_types: List[str]) -> Tuple[str, float, float] | None:    
    nearest_station : Tuple[str, float, float]| None = None
    min_distance = float('inf')

    for i, station in stations_df.iterrows():
        if not bike_types:
            has_available_bikes = station["num_bikes_available"]>0
        else:
            needs_ebike = "ebike" in bike_types
            needs_mech = "mechanical" in bike_types
            ok_ebike = (station["ebike"] > 0) if needs_ebike else True
            ok_mech = (station["mechanical"] > 0) if needs_mech else True
            has_required_bike = ok_ebike and ok_mech

        if not has_required_bike: 
            continue

        distance = calculate_distance(user_location, (station["lat"], station["lon"]))
        if distance < min_distance:
            min_distance = distance
            nearest_station = (station["station_id"], station["lat"], station["lon"])

        if nearest_station is None:
            for _, station in stations_df[stations_df["num_bikes_available"] > 0].iterrows():
                distance = calculate_distance(user_location, (station["lat"], station["lon"]))
                if distance < best_distance:
                    best_distance = distance
                    nearest_station = (station["station_id"], float(station["lat"]), float(station["lon"]))

    return nearest_station

# Trouve la station la plus proche avec au moins un ancrage libre.
# Retour: (station_id, lat, lon) ou None.

def get_dock_availability(user_location: Sequence[float], stations_df: pd.DataFrame) -> Tuple[str, float, float] | None:
    nearest_station : Tuple[str, float, float]| None = None
    min_distance = float('inf')

    for _, station in stations_df[stations_df["num_docks_available"] > 0].iterrows():
        distance = calculate_distance(user_location, (station["lat"], station["lon"]))
        if distance < min_distance:
            min_distance = distance
            nearest_station = (station["station_id"], station["lat"], station["lon"])
    return nearest_station

# Appel OSRM pour itinéraire entre origin et chosen_station.
def run_osrm(selected_station: Tuple[str, float, float] | None, user_location: Sequence[float]) -> Tuple[list[tuple[float, float]], int | None]:
    if not selected_station or not user_location:
        return [], None
    user_lat, user_lon = user_location
    station_id, station_lat, station_lon = selected_station

    try:

        osrm_url = ( f"https://router.project-osrm.org/route/v1/foot/" f"{user_lon},{user_lat};{station_lon},{station_lat}")
        params = {"overview": "full", "geometries": "geojson"}
        
        response = requests.get(osrm_url, params=params, timeout=20)
        response.raise_for_status() 
        data = response.json()
        route=data.get("routes", [])
        if not route:
            return [], None
        
        best_route = route[0]
        route_duration_min = round(best_route.get("duration", 0) / 60)
        route_coords = best_route.get("geometry", {}).get("coordinates", [])

        route_latlon = [(lat, lon) for lon, lat in route_coords]
        return route_latlon, route_duration_min

    except Exception:
        return [], None


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


