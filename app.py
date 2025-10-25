from config import GBFS_INDEX, UPDATE_INTERVAL_S
import pandas as pd
import requests
import time


def getGbfs(index_url=GBFS_INDEX, lang= "fr")-> dict:
    response = requests.get(GBFS_INDEX)
    response.raise_for_status()



