from config import GBFS_INDEX, UPDATE_INTERVAL_S
import pandas as pd
import requests
import time

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




feeds=getFeeds()
info_url = feeds["station_information"]
status_url = feeds["station_status"]
info = fetch_json(info_url) 
df_info = pd.DataFrame(info["data"]["stations"])
print("Station Information:")
print(df_info)
   