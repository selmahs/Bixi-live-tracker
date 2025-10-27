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

st.set_page_config(page_title="BIXI Live Tracker", page_icon="🚲",layout="wide",)
st.title("BIXI Montréal - Station Status")
st.markdown("Ce tableau de bord suit la disponibilité des vélos et bornes dans les stations BIXI de Montréal.")
