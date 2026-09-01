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
import datetime as dt


# =========================================================
# CONFIGURATION DE LA PAGE
# =========================================================

st.set_page_config(
    page_title="BIXI Live Tracker",
    page_icon="🚲",
    layout="wide",
)

st.title("🚲 BIXI Montréal - Disponibilité en temps réel")

st.markdown(
    """
    Ce tableau de bord suit la disponibilité des vélos et des bornes
    dans les stations BIXI de Montréal et estime la demande horaire
    à l'aide de modèles de machine learning.
    """
)


# =========================================================
# CHARGEMENT DES DONNÉES
# =========================================================

info_df, status_df, data = load_bixi_data()

for i in ["lat", "lon"]:
    if i in data.columns:
        data[i] = pd.to_numeric(data[i], errors="coerce")


# =========================================================
# INDICATEURS CLÉS DE PERFORMANCE
# =========================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Vélos disponibles maintenant",
        value=int(data["num_bikes_available"].sum()),
    )

    st.metric(
        label="Vélos électriques disponibles",
        value=int(status_df["num_ebikes_available"].sum()),
    )


with col2:
    st.metric(
        label="Stations avec vélos disponibles",
        value=int((data["num_bikes_available"] > 0).sum()),
    )

    st.metric(
        label="Stations avec vélos électriques",
        value=int((status_df["num_ebikes_available"] > 0).sum()),
    )


with col3:
    st.metric(
        label="Stations avec bornes disponibles",
        value=int((data["num_docks_available"] > 0).sum()),
    )


# =========================================================
# SIDEBAR
# =========================================================

iamhere = 0
iamhere_return = 0

findmeabike = False
findmeadock = False

input_bike_modes = []


with st.sidebar:

    st.header("Recherche de station")

    bike_method = st.selectbox(
        "Cherchez-vous à louer ou retourner un vélo ?",
        ("Louer", "Retourner"),
    )

    # -----------------------------------------------------
    # LOUER
    # -----------------------------------------------------

    if bike_method == "Louer":

        input_bike_modes = st.multiselect(
            "Quel type de vélo voulez-vous louer ?",
            ["Vélo électrique", "Vélo mécanique"],
        )

        st.subheader("Votre emplacement actuel")

        input_street = st.text_input("Rue", "")
        input_city = st.text_input("Ville", "Montréal")
        input_country = st.text_input("Pays", "Canada")

        drive = st.checkbox(
            "Je conduis une voiture jusqu'à la station BIXI."
        )

        findmeabike = st.button(
            "Trouvez-moi un vélo !",
            type="primary",
        )

        if findmeabike:

            if input_street != "":

                iamhere = geocode(
                    input_street
                    + " "
                    + input_city
                    + " "
                    + input_country
                )

                if iamhere == "":
                    st.error("Adresse invalide !")

            else:
                st.error("Veuillez saisir votre emplacement.")


    # -----------------------------------------------------
    # RETOURNER
    # -----------------------------------------------------

    else:

        st.subheader("Votre emplacement actuel")

        input_street_return = st.text_input(
            "Rue",
            "",
            key="return_street",
        )

        input_city_return = st.text_input(
            "Ville",
            "Montréal",
            key="return_city",
        )

        input_country_return = st.text_input(
            "Pays",
            "Canada",
            key="return_country",
        )

        findmeadock = st.button(
            "Trouvez-moi une borne de retour !",
            type="primary",
        )

        if findmeadock:

            if input_street_return != "":

                iamhere_return = geocode(
                    input_street_return
                    + " "
                    + input_city_return
                    + " "
                    + input_country_return
                )

                if iamhere_return == "":
                    st.error("Adresse invalide !")

            else:
                st.error("Veuillez saisir votre emplacement.")


# =========================================================
# CARTE + PRÉDICTION
# =========================================================

st.divider()

map_col, pred_col = st.columns([2, 1])

center = [45.5017, -73.5673]


# =========================================================
# CARTE
# =========================================================

with map_col:

    st.subheader("🗺️ Stations BIXI")


    # -----------------------------------------------------
    # CARTE PAR DÉFAUT
    # -----------------------------------------------------

    if (
        (bike_method == "Retourner" and not findmeadock)
        or
        (bike_method == "Louer" and not findmeabike)
    ):

        m = folium.Map(
            location=center,
            zoom_start=13,
        )

        for _, row in data.iterrows():

            marker_color = choose_station_color(
                int(row["num_bikes_available"])
            )

            popup_text = folium.Popup(
                f"<b>{row.get('name', 'Station BIXI')}</b><br>"
                f"Vélos disponibles : {row['num_bikes_available']}<br>"
                f"Vélos mécaniques : {row['mechanical']}<br>"
                f"Vélos électriques : {row['ebike']}<br>"
                f"Bornes disponibles : {row['num_docks_available']}",
                max_width=300,
            )

            folium.CircleMarker(
                location=[
                    row["lat"],
                    row["lon"],
                ],
                radius=2,
                color=marker_color,
                popup=popup_text,
            ).add_to(m)

        folium_static(m)


    # -----------------------------------------------------
    # RETOURNER UN VÉLO
    # -----------------------------------------------------

    if (
        findmeadock
        and input_street_return != ""
        and iamhere_return != ""
    ):

        chosen_station = get_dock_availability(
            iamhere_return,
            data,
        )

        m1 = folium.Map(
            location=iamhere_return,
            zoom_start=16,
            tiles="cartodbpositron",
        )

        for _, row in data.iterrows():

            marker_color = choose_station_color(
                int(row["num_bikes_available"])
            )

            folium.CircleMarker(
                location=[
                    row["lat"],
                    row["lon"],
                ],
                radius=2,
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.7,
                popup=folium.Popup(
                    f"Station ID : {row['station_id']}<br>"
                    f"Vélos disponibles : {row['num_bikes_available']}<br>"
                    f"Vélos mécaniques : {row['mechanical']}<br>"
                    f"Vélos électriques : {row['ebike']}<br>"
                    f"Bornes disponibles : {row['num_docks_available']}",
                    max_width=300,
                ),
            ).add_to(m1)


        folium.Marker(
            location=iamhere_return,
            popup="Vous êtes ici.",
            icon=folium.Icon(
                color="blue",
                icon="person",
                prefix="fa",
            ),
        ).add_to(m1)


        if chosen_station:

            folium.Marker(
                location=(
                    chosen_station[1],
                    chosen_station[2],
                ),
                popup="Retournez votre vélo ici.",
                icon=folium.Icon(
                    color="red",
                    icon="bicycle",
                    prefix="fa",
                ),
            ).add_to(m1)


            coordinates, duration = run_osrm(
                chosen_station,
                iamhere_return,
            )

            if coordinates:

                folium.PolyLine(
                    locations=coordinates,
                    color="blue",
                    weight=5,
                    tooltip=(
                        f"Temps estimé ~ {duration} min "
                        f"pour y aller."
                    ),
                ).add_to(m1)


        folium_static(m1)


    # -----------------------------------------------------
    # LOUER UN VÉLO
    # -----------------------------------------------------

    if (
        findmeabike
        and input_street != ""
        and iamhere != ""
    ):

        internal_modes = []

        if "Vélo électrique" in input_bike_modes:
            internal_modes.append("ebike")

        if "Vélo mécanique" in input_bike_modes:
            internal_modes.append("mechanical")


        chosen_station = get_bike_availability(
            iamhere,
            data,
            internal_modes,
        )


        m2 = folium.Map(
            location=iamhere,
            zoom_start=16,
            tiles="cartodbpositron",
        )


        for _, row in data.iterrows():

            marker_color = choose_station_color(
                int(row["num_bikes_available"])
            )

            folium.CircleMarker(
                location=[
                    row["lat"],
                    row["lon"],
                ],
                radius=2,
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.7,
                popup=folium.Popup(
                    f"Station ID : {row['station_id']}<br>"
                    f"Vélos disponibles : {row['num_bikes_available']}<br>"
                    f"Vélos mécaniques : {row['mechanical']}<br>"
                    f"Vélos électriques : {row['ebike']}",
                    max_width=300,
                ),
            ).add_to(m2)


        folium.Marker(
            location=iamhere,
            popup="Vous êtes ici.",
            icon=folium.Icon(
                color="blue",
                icon="person",
                prefix="fa",
            ),
        ).add_to(m2)


        if chosen_station:

            folium.Marker(
                location=(
                    chosen_station[1],
                    chosen_station[2],
                ),
                popup="Louez votre vélo ici.",
                icon=folium.Icon(
                    color="green",
                    icon="bicycle",
                    prefix="fa",
                ),
            ).add_to(m2)


            coordinates, duration = run_osrm(
                chosen_station,
                iamhere,
            )

            if coordinates:

                folium.PolyLine(
                    locations=coordinates,
                    color="blue",
                    weight=5,
                    tooltip=(
                        f"Temps estimé ~ {duration} min "
                        f"pour y aller."
                    ),
                ).add_to(m2)


        folium_static(m2)


# =========================================================
# PRÉDICTION LIGHTGBM
# =========================================================

with pred_col:

    st.subheader("📈 Prédiction de la demande")

    st.caption(
        "Nombre estimé de départs par heure pour la station sélectionnée."
    )


    selected_name = st.selectbox(
        "Choisissez une station",
        data["name"].dropna().unique(),
    )


    heures = list(range(24))


    predictions = [
        predict_hourly_demand(
            selected_name,
            dt.datetime.now().replace(
                hour=h,
                minute=0,
                second=0,
            ),
        )
        for h in heures
    ]


    pred_df = pd.DataFrame(
        {
            "Heure": heures,
            "Départs prédits": predictions,
        }
    )


    st.bar_chart(
        pred_df.set_index("Heure"),
        height=400,
    )

    st.caption(
        "Modèle actuellement utilisé : LightGBM"
    )


# =========================================================
# COMPARAISON DES MODÈLES
# =========================================================

st.divider()

st.header("🧠 Comparaison des modèles")

st.markdown(
    """
    Deux approches ont été entraînées sur les données historiques BIXI
    afin de prédire le **nombre de départs par station et par heure**.

    **LightGBM** est comparé à un réseau de neurones **MLP PyTorch**
    utilisant notamment un embedding pour représenter les stations.
    """
)


# =========================================================
# MÉTRIQUES
# =========================================================

lightgbm_mae = 4.58
lightgbm_rmse = 7.30

pytorch_mae = 6.44
pytorch_rmse = 10.86


lightgbm_col, pytorch_col = st.columns(2)


# ---------------------------------------------------------
# LIGHTGBM
# ---------------------------------------------------------

with lightgbm_col:

    st.subheader("LightGBM")

    st.caption(
        "Modèle de gradient boosting basé sur des arbres de décision."
    )

    mae_col, rmse_col = st.columns(2)

    with mae_col:

        st.metric(
            label="MAE",
            value=f"{lightgbm_mae:.2f}",
            help=(
                "Mean Absolute Error : erreur absolue moyenne "
                "en nombre de départs par heure."
            ),
        )

    with rmse_col:

        st.metric(
            label="RMSE",
            value=f"{lightgbm_rmse:.2f}",
            help=(
                "Root Mean Squared Error : pénalise davantage "
                "les erreurs importantes."
            ),
        )


    st.success(
        "✓ Meilleures performances sur les données de test"
    )


# ---------------------------------------------------------
# PYTORCH
# ---------------------------------------------------------

with pytorch_col:

    st.subheader("PyTorch MLP")

    st.caption(
        "Réseau de neurones avec embedding des stations BIXI."
    )

    mae_col, rmse_col = st.columns(2)

    with mae_col:

        st.metric(
            label="MAE",
            value=f"{pytorch_mae:.2f}",
            help=(
                "Mean Absolute Error : erreur absolue moyenne "
                "en nombre de départs par heure."
            ),
        )

    with rmse_col:

        st.metric(
            label="RMSE",
            value=f"{pytorch_rmse:.2f}",
            help=(
                "Root Mean Squared Error : pénalise davantage "
                "les erreurs importantes."
            ),
        )


    st.info(
        "Réseau de neurones expérimental avec embeddings"
    )


# =========================================================
# GRAPHIQUE COMPARATIF
# =========================================================

st.subheader("Performances sur les données de test")


comparison_df = pd.DataFrame(
    {
        "LightGBM": [
            lightgbm_mae,
            lightgbm_rmse,
        ],
        "PyTorch MLP": [
            pytorch_mae,
            pytorch_rmse,
        ],
    },
    index=[
        "MAE",
        "RMSE",
    ],
)


st.bar_chart(
    comparison_df,
    height=400,
)


# =========================================================
# INTERPRÉTATION
# =========================================================

mae_improvement = (
    (pytorch_mae - lightgbm_mae)
    / pytorch_mae
    * 100
)

rmse_improvement = (
    (pytorch_rmse - lightgbm_rmse)
    / pytorch_rmse
    * 100
)


st.subheader("Résultat")


result_col1, result_col2 = st.columns(2)


with result_col1:

    st.metric(
        "Réduction de la MAE",
        f"{mae_improvement:.1f} %",
    )


with result_col2:

    st.metric(
        "Réduction de la RMSE",
        f"{rmse_improvement:.1f} %",
    )


st.success(
    """
    **LightGBM est actuellement le modèle retenu pour l'application.**

    Il obtient une erreur plus faible que le réseau de neurones PyTorch
    sur les données de test. Ce résultat montre que, pour les variables
    tabulaires actuellement utilisées dans ce projet, LightGBM offre
    de meilleures performances prédictives.
    """
)