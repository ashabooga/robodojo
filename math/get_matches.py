import numpy as np
import pandas as pd
import requests
import json
from datetime import date, timedelta, datetime
import time
import sqlite3
from sqlite3 import Error

today = date.today()
tdelta = timedelta(days=7)
one_week_date = today + tdelta
day_time = datetime.today().strftime('%A, ')

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

indexList = []
eventList = []

if previously_logged_events_1920_df.empty == False:
	for i in range(len(events_1920_df)):
		eventKey = events_1920_df.loc[i, "event_key"]
		if eventKey not in previously_logged_events_1920_df.event_key.values:
			indexList.append(i)
			eventList.append(events_1920_df.loc[i, "event_key"])
else:
	indexList = list(range(len(events_1920_df)))
	eventList = list(events_1920_df.event_key.values)



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

future_matches_df.to_sql("future_matches_1920", con=conn, if_exists="replace")

# MOVING ON TO IMPORTING NEW MATCHES

all_matches_1920_df = pd.DataFrame()
useable_matches_1920_df = pd.DataFrame()

if len(eventList) != 0 or future_matches_df.empty != True:
	if len(eventList) !=0:
		for i in eventList:
			index = events_1920_df.index[events_1920_df["event_key"] == i][0]
			url = 'https://theorangealliance.org/api/{}/matches'.format(i)
			while True:
				try:
					match_request = requests.get(
						url,
						headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
					)
					match_data = json.loads(match_request.content)
					break
				except:
					print("stopped at {}, row = {} out of {}".format(i, index, len(eventList)))
					time.sleep(15)
					match_request = requests.get(
						url,
						headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
					)
					if str(match_request) == "<Response [429]>":
						print("still didn't work")
					pass
			if all_matches_1920_df.empty == True:
				all_matches_1920_df = pd.DataFrame(match_data, index=[0])
				useable_matches_1920_df = pd.DataFrame(match_data, index=[0])
			else:
				new_match_data = pd.DataFrame(match_data, index=[0])
				all_matches_1920_df = all_matches_1920_df.append(new_match_data)
				useable_matches_1920_df = useable_matches_1920_df.append(new_match_data)
	if future_matches_df.empty != True:
		for i in future_matches_df.event_key:
			index = future_matches_df.index[future_matches_df["event_key"] == i][0]
			url = 'https://theorangealliance.org/api/{}/matches'.format(i)
			while True:
				try:
					match_request = requests.get(
						url,
						headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
					)
					match_data = json.loads(match_request.content)
					break
				except:
					print("stopped at {}, row = {} out of {}".format(i, index, len(DataFrame.index)))
					time.sleep(15)
					match_request = requests.get(
						url,
						headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
					)
					if str(match_request) == "<Response [429]>":
						print("still didn't work")
					pass
			if all_matches_1920_df.empty == True:
				all_matches_1920_df = pd.DataFrame(match_data, index=[0])
			else:
				new_match_data = pd.DataFrame(match_data, index=[0])
				all_matches_1920_df = all_matches_1920_df.append(new_match_data)
else:
	print("Not doing stuff")

if all_matches_1920_df.empty == False:
	all_matches_1920_df = all_matches_1920_df[["match_key", "event_key", "red_score", "blue_score", "red_penalty", "blue_penalty", "red_auto_score", "blue_auto_score", "red_tele_score", "blue_tele_score", "red_end_score", "blue_end_score", "participants"]]
	useable_matches_1920_df = useable_matches_1920_df[["match_key", "event_key", "red_score", "blue_score", "red_penalty", "blue_penalty", "red_auto_score", "blue_auto_score", "red_tele_score", "blue_tele_score", "red_end_score", "blue_end_score", "participants"]]
	all_matches_1920_df = all_matches_1920_df.dropna()
	useable_matches_1920_df = useable_matches_1920_df.dropna()

	all_matches_1920_df = all_matches_1920_df.reset_index()
	all_matches_1920_df = all_matches_1920_df.drop(columns=["index"])

	useable_matches_1920_df = useable_matches_1920_df.reset_index()
	useable_matches_1920_df = useable_matches_1920_df.drop(columns=["index"])

all_matches_1920_df.to_sql("all_matches", con=conn, if_exists="append")
useable_matches_1920_df.to_sql("useable_matches", con=conn, if_exists="append")

conn.close()