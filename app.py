from config import *
from typing import Dict
from functions import *
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import pandas as pd
import requests
import time
import folium
import streamlit as st

st.set_page_config(
    page_title="BIXI Live Tracker",
    page_icon="🚲",
    layout="wide",
)
st.title(" BIXI  - disponibilité en direct")
st.markdown("Application de suivi en direct des vélos BIXI disponibles aux stations de Montréal.")

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    refresh_sec = st.number_input("Rafraîchissement (s)", 5, 120, value=UPDATE_INTERVAL_S, step=5)
with col2:
    orange_max = st.number_input("Seuil orange (N)", 1, 20, value=ORANGE_MAX, step=1)
with col3:
    only_open = st.checkbox("Afficher uniquement les stations en location (is_renting)", value=True)

@st.cache_data(ttl=20, show_spinner=False)
def get_df_cached():
    return load_data()

df = get_df_cached().copy()
if only_open and "is_renting"in df.columns:
    df = df[df["is_renting"] == 1].copy()

if df.empty:
    st.warning("Aucune station disponible avec les critères sélectionnés.")
    st.stop()


colA, colB, colC = st.columns(3)
with colA:
    st.metric("🚲 Vélos disponibles (total)", int(df["num_bikes_available"].sum()))
with colB:
    st.metric("🏟️ Stations avec des vélos", int((df["num_bikes_available"] > 0).sum()))
with colC:
    st.metric("🅿️ Stations avec des bornes libres", int((df["num_docks_available"] > 0).sum()))
  
def get_center(df=df):
    if  df.empty:
       return [45.508, -73.587]
    else:
        return [float(df["lat"].mean()), float(df["lon"].mean())]
 
center = get_center()
m = folium.Map(location=center, zoom_start=13, tiles="cartodbpositron", control_scale=True)
use_clusters = st.sidebar.checkbox("Grouper les points (clusters)", value=True)
layer = MarkerCluster().add_to(m) if use_clusters else m

for _, row in df.iterrows():
    name = row.get("name", "Station")
    lat = float(row["lat"])
    lon = float(row["lon"])
    capacity = row.get("capacity", None)
    bikes = int(row.get("num_bikes_available", 0))
    docks = int(row.get("num_docks_available", 0))

    popup_html = (
        f"<b>{name}</b><br>"
        f"Vélos dispo : {bikes}<br>"
        f"Bornes libres : {docks}<br>"
        f"Capacité : {capacity if pd.notna(capacity) else 'N/A'}"
    )

    folium.CircleMarker(
        location=[lat, lon],
        color=choose_station_color(bikes, orange_max),
        fill=True,
        fill_opacity=0.85,
        popup=popup_html,
    ).add_to(layer)

st_folium(m, width=680, height=None)

with st.expander("Voir le tableau brut"):
    cols = ["name", "lat", "lon", "capacity", "num_bikes_available", "num_docks_available", "is_renting", "last_reported"]
    cols = [c for c in cols if c in df.columns]
    st.dataframe(df[cols].sort_values("num_bikes_available", ascending=False), use_container_width=True)

st.sidebar.button("🔄 Rafraîchir maintenant", on_click=st.experimental_rerun)
