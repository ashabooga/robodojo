import numpy as np
import pandas as pd
import requests
import json
from datetime import date
import sqlite3
from sqlite3 import Error

today = date.today()

event_request_1920 = requests.get(
    'https://theorangealliance.org/api/event?season_key=1920',
    headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
)

event_data_1920 = json.loads(event_request_1920.content)
event_data_1920_df = pd.DataFrame(event_data_1920)

indexNames = event_data_1920_df[(event_data_1920_df["event_type_key"] == "OTHER") | (event_data_1920_df["event_type_key"] == "SCRIMMAGE")].index
event_data_1920_df.drop(indexNames , inplace=True)

conn = sqlite3.connect(../data.db)