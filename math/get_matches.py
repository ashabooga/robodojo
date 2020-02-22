import numpy as np
import pandas as pd
import requests
import json
from datetime import date, timedelta
import time
import sqlite3
from sqlite3 import Error

today = date.today()
tdelta = timedelta(days=7)
one_week_date = today + tdelta

conn = sqlite3.connect('data.db') #Connecting to database
c = conn.cursor()

c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='previous_events_1920'")

#if the count is 1, then table exists
if c.fetchone()[0]==1 :
	previously_logged_events_1920_df = pd.read_sql_query("SELECT * FROM previous_events_1920", conn)
else:
	previously_logged_events_1920_df = pd.DataFrame()

event_request_1920 = requests.get(
    'https://theorangealliance.org/api/event?season_key=1920',
    headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
) #Calling for all this year's events

try: #COME BACK TO THIS IF WILL SAYS BETTER WAY
	events_1920 = json.loads(event_request_1920.content)
except:
	print(event_request_1920)
	time.sleep(15)

	event_request_1920 = requests.get(
		'https://theorangealliance.org/api/event?season_key=1920',
    	headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
	) #Calling for all this year's events
	events_1920 = json.loads(event_request_1920.content)

events_1920_df = pd.DataFrame(events_1920)


indexNames = events_1920_df[(events_1920_df["event_type_key"] == "OTHER") | (events_1920_df["event_type_key"] == "SCRIMMAGE")].index
events_1920_df.drop(indexNames , inplace=True) #Deleting certain types of events


def date_parse(x): #Formatting start_date for events, removing time
  list = []
  list = x.split("T")
  return list[0]

events_1920_df["start_date"] = events_1920_df["start_date"].apply(date_parse)

events_1920_df = events_1920_df[["event_key", "region_key", "event_code", "event_type_key", "event_name", "start_date", "city", "venue", "website"]]
events_1920_df = events_1920_df.sort_values("start_date")

future_events_1920_df = events_1920_df.loc[events_1920_df.start_date >= str(today)]
events_1920_df = events_1920_df.drop(events_1920_df[events_1920_df.start_date >= str(today)].index)

events_1920_df = events_1920_df.reset_index()
events_1920_df = events_1920_df.drop(columns=["index"])

if previously_logged_events_1920_df.empty == False:
	indexList = []
	for i in range(len(events_1920_df)):
		eventKey = events_1920_df.loc[i, "event_key"]
		if eventKey not in previously_logged_events_1920_df.event_key.values:
			indexList.append(i)
		else:
			indexList.append(i)



events_1920_df.to_sql("previous_events_1920", con=conn, if_exists="replace")


#MOVING ON TO LOOKING FOR USEABLE FUTURE EVENTS

future_events_1920_df = future_events_1920_df.loc[future_events_1920_df["start_date"] <= str(one_week_date)]
future_matches_df = pd.DataFrame(columns = list(events_1920_df))

for i in future_events_1920_df.event_key:
	url = 'https://theorangealliance.org/api/{}/matches'.format(i)
	while True:
		try:
			event_matches_request = requests.get(
	    		url,
	    		headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
			)
			event_matches = json.loads(event_matches_request.content)
			break
		except:
			print(event_matches_request)
			time.sleep(15)
			event_matches_request = requests.get(
		    	url,
		    	headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
			)
			if str(event_matches_request) == "<Response [429]>":
				print("still didn't work")
			pass

	if str(event_matches) != "{'_code': 404, '_message': 'Content not found.'}":
		event_matches_df = pd.DataFrame(event_matches)
		future_matches_df.append(event_matches_df)

print(future_matches_df.shape)
print(future_events_1920_df.loc[(future_events_1920_df["start_date"] == min(future_events_1920_df.start_date)) and (future_events_1920_df["event_type_key"] == "QUAL")]["event_name"])
print(min(future_events_1920_df.start_date))



conn.close()