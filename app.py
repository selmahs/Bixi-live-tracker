from config import * 
from typing import Dict
from functions import *
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
import pandas as pd
import requests
import time
import folium
import streamlit as st

st.set_page_config(page_title="BIXI Live Tracker", page_icon="🚲",layout="wide",)
st.title("BIXI Montréal -Disponibilité en temps réel")
st.markdown("Ce tableau de bord suit la disponibilité des vélos et bornes dans les stations BIXI de Montréal.")


# Chargement des données

info_df, status_df, data = load_bixi_data()
for i in ['lat', 'lon']:
    if i in data.columns:
        data[i] = pd.to_numeric(data[i], errors='coerce')


# Indicateurs clés de performance (KPI)
col1, col2, col3 = st.columns(3)
with col1: 
    st.metric(label="Vélos disponibles maintenant", value=int(data["num_bikes_available"].sum()))
    st.metric(label="Vélos électriques disponibles maintenant", value=int(data["ebike"].sum()))
with col2:
    st.metric(label="Stations avec vélos disponibles", value=int((data["num_bikes_available"] > 0).sum()))
    st.metric(label="Stations avec vélos électriques disponibles", value=int((data["ebike"] > 0).sum()))
with col3:
    st.metric(label="Stations avec bornes disponibles", value=int((data["num_docks_available"] > 0).sum()))

# Sidebar

iamhere = 0
iamhere_return = 0
findmeabike = False
findmeadock = False
input_bike_modes = []

with st.sidebar:
    bike_method =  st .selectbox("Cherchez-vous à louer ou retourner un vélo?", ("Louer", "Retourner") )
    #cas ou on veut louer un velo
    if bike_method == "Louer":
        input_bike_modes = st.multiselect('Quel type de vélo voulez-vous louer?', ['Vélo électrique', 'Vélo mécanique'])
        st.subheader("Votre emplacement actuel:")
        input_street = st.text_input('Rue', '')
        input_city = st.text_input('Ville', 'Montréal')
        input_country = st.text_input('Pays', 'Canada')
        drive = st.checkbox("Je conduis une voiture jusqu'à la station BIXI.")
        findmeabike = st.button('Trouvez-moi un vélo !', type='primary')
        if findmeabike:
            if input_street != '':
                iamhere = geocode(input_street + ' ' + input_city + ' ' + input_country)
                if iamhere == '':
                    st.subheader(':red[Adresse invalide !]')
            else:
                st.subheader(':red[Veuillez saisir votre emplacement.]')

    #cas ou on veut retourner un velo
    else:
        st.subheader("Votre emplacement actuel:")
        input_street_return = st.text_input('Rue', '')
        input_city_return = st.text_input('Ville', 'Montréal')
        input_country_return = st.text_input('Pays', 'Canada')
        findmeadock = st.button('Trouvez-moi une borne de retour !', type='primary')
        if findmeadock:
            if input_street_return != '':
                iamhere_return = geocode(input_street_return + ' ' + input_city_return + ' ' + input_country_return)
                if iamhere_return == '':
                    st.subheader(':red[Adresse invalide !]')
            else:
                st.subheader(':red[Veuillez saisir votre emplacement.]')



#genere la carte 

center = [45.5017, -73.5673]  # Centre de Montréal


if (bike_method == 'Retourner' and not findmeadock) or (bike_method == 'Louer' and not findmeabike):
    m = folium.Map(location=center, zoom_start=13)

    for i, j in data.iterrows():
        marker_color = choose_station_color(int(j['num_bikes_available']))

        popup_text = folium.Popup(
                f"Nombre de vélos disponibles: {j['num_bikes_available']}<br>"
                f"Nombre de vélos mécaniques disponibles: {j['mechanical']}<br>"
                f"Nombre de vélos électriques: {j['ebike']}",
                max_width=300,
            )
        folium.CircleMarker(
            location=[j['lat'], j['lon']],
            radius=2,
            color=marker_color,
            #fill=True,
            #fill_color=marker_color,
            popup=popup_text,
        ).add_to(m)
    folium_static(m)    


#quand on veut rendre un velo , cad trouver une borne de retour
if findmeadock and input_street_return != '' and iamhere_return != '':
    chosen_station = get_dock_availability(iamhere_return, data)
    m1 = folium.Map(location=iamhere_return, zoom_start=16, tiles='cartodbpositron')
    for _, row in data.iterrows():
        marker_color = choose_station_color(int(row['num_bikes_available']))
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=2,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"Station ID: {row['station_id']}<br>"
                f"Vélos totaux disponibles: {row['num_bikes_available']}<br>"
                f"Vélos mécaniques disponibles: {row['mechanical']}<br>"
                f"Vélos électriques disponibles: {row['ebike']}",
                max_width=300,
            ),
        ).add_to(m1)
    folium.Marker(location=iamhere_return, popup='Vous êtes ici.', icon=folium.Icon(color='blue', icon='person', prefix='fa')).add_to(m1)
    if chosen_station:
        folium.Marker(location=(chosen_station[1], chosen_station[2]), popup='Retournez votre vélo ici.', icon=folium.Icon(color='red', icon='bicycle', prefix='fa')).add_to(m1)
        coordinates, duration = run_osrm(chosen_station, iamhere_return)
        if coordinates:
            folium.PolyLine(locations=coordinates, color='blue', weight=5, tooltip=f"Temps estimé ~ {duration} min pour y aller.").add_to(m1)
    folium_static(m1)


# itinéraire quand on veut LOUER un vélo
if findmeabike and input_street != '' and iamhere != '':

    internal_modes = []
    if 'Vélo électrique' in input_bike_modes:
        internal_modes.append('ebike')
    if 'Vélo mécanique' in input_bike_modes:
        internal_modes.append('mechanical')

    chosen_station = get_bike_availability(iamhere, data, internal_modes)

    m2 = folium.Map(location=iamhere, zoom_start=16, tiles='cartodbpositron')
    for _, row in data.iterrows():
        marker_color = choose_station_color(int(row['num_bikes_available']))
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=2,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"Station ID: {row['station_id']}<br>"
                f"Vélos totaux disponibles: {row['num_bikes_available']}<br>"
                f"Vélos mécaniques disponibles: {row['mechanical']}<br>"
                f"Vélos électriques disponibles: {row['ebike']}",
                max_width=300,
            ),
        ).add_to(m2)

    folium.Marker(
        location=iamhere,
        popup='Vous êtes ici.',
        icon=folium.Icon(color='blue', icon='person', prefix='fa')
    ).add_to(m2)

    if chosen_station:
        folium.Marker(
            location=(chosen_station[1], chosen_station[2]),
            popup='Louez votre vélo ici.',
            icon=folium.Icon(color='green', icon='bicycle', prefix='fa')
        ).add_to(m2)

        coordinates, duration = run_osrm(chosen_station, iamhere)
        if coordinates:
            folium.PolyLine(
                locations=coordinates,
                color='blue',
                weight=5,
                tooltip=f"Temps estimé ~ {duration} min pour y aller."
            ).add_to(m2)

    folium_static(m2)
