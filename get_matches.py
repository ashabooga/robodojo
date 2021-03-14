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
# day_time = datetime.today().strftime('%A')

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
events_1920 = json.loads(event_request_1920.content)
events_1920_df = pd.DataFrame(events_1920)


indexNames = events_1920_df[(events_1920_df["event_type_key"] == "OTHER") | (events_1920_df["event_type_key"] == "SCRIMMAGE")].index
events_1920_df.drop(indexNames, inplace=True) #Deleting certain types of events


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

future_events_1920_df = future_events_1920_df.reset_index()
future_events_1920_df = future_events_1920_df.drop(columns=["index"])

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

for i in future_events_1920_df.event_key:
	while True:
		try:
			event_matches_request = requests.get(
				'https://theorangealliance.org/api/{}/matches'.format(i),
				headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
			)
			event_matches = json.loads(event_matches_request.content)
			break
		except:
			print(event_matches_request)
			time.sleep(15)
			event_matches_request = requests.get(
				'https://theorangealliance.org/api/{}/matches'.format(i),
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

useable_matches_1920_df = pd.DataFrame()

c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='all_matches_1920'")

#if the count is 1, then table exists
if c.fetchone()[0]==1 :
	previously_logged_matches_1920_df = pd.read_sql_query("SELECT * FROM all_matches_1920", conn)
else:
	previously_logged_matches_1920_df = pd.DataFrame()

previously_logged_event_keys = previously_logged_matches_1920_df["event_key"].unique().tolist()

lastSize = 500
count = 1
all_matches_df = pd.DataFrame()
while lastSize == 500:
	while True:
		try:
			matches_start_request = requests.get(
				'https://theorangealliance.org/api/match/all/1920?start={}'.format(count*500),
				headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
			)
			matches_start = json.loads(matches_start_request.content)
			break
		except:
			pass
	if all_matches_df.empty == True:
		all_matches_df = pd.DataFrame(matches_start)
	else:
		new_match_df = pd.DataFrame(matches_start)
		all_matches_df = all_matches_df.append(new_match_df)
	lastSize = len(event_data)
	count = count + 1

events_with_matches_keys = all_matches_df["event_key"].unique().tolist()

all_matches_df = all_matches_df.drop()


# if len(eventList) != 0 or future_matches_df.empty == False:
# 	if len(eventList) !=0:
# 		for i in eventList:
# 			index = events_1920_df.index[events_1920_df["event_key"] == i][0]
# 			while True:
# 				try:
# 					match_request = requests.get(
# 						'https://theorangealliance.org/api/{}/matches'.format(i),
# 						headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
# 					)
# 					if str(match_request) == "<Response [400]>" or str(match_request) == "<Response [404]>":
# 						print("Skipped event {}, row = {} out of {}".format(i, index, len(eventList)))
# 						break
# 					else:
# 						match_data = json.loads(match_request.content)
# 						if all_matches_1920_df.empty == True:
# 							all_matches_1920_df = pd.DataFrame(match_data, index=[0])
# 							future_matches_1920_df = pd.DataFrame(match_data, index=[0])
# 						else:
# 							new_match_data = pd.DataFrame(match_data, index=[0])
# 							all_matches_1920_df = all_matches_1920_df.append(new_match_data)
# 							useable_matches_1920_df = useable_matches_1920_df.append(new_match_data)
# 					break
# 				except:
# 					print("stopped at {}, row = {} out of {}".format(i, index, len(eventList)))
# 					time.sleep(15)
# 					match_request = requests.get(
# 						'https://theorangealliance.org/api/{}/matches'.format(i),
# 						headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
# 					)
# 					if str(match_request) == "<Response [429]>":
# 						print("trying again")
# 					pass
# 	if future_matches_df.empty == False:
# 		for i in future_matches_df.event_key:
# 			index = future_matches_df.index[future_matches_df["event_key"] == i][0]
# 			while True:
# 				try:
# 					match_request = requests.get(
# 						'https://theorangealliance.org/api/{}/matches'.format(i),
# 						headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
# 					)
# 					if str(match_request) == "<Response [400]>" or str(match_request) == "<Response [404]>":
# 						print("Skipped event {}, row = {} out of {}".format(i, index, len(DataFrame.index)))
# 						break
# 					else:
# 						match_data = json.loads(match_request.content)
# 						if all_matches_1920_df.empty == True:
# 							all_matches_1920_df = pd.DataFrame(match_data, index=[0])
# 						else:
# 							new_match_data = pd.DataFrame(match_data, index=[0])
# 							all_matches_1920_df = all_matches_1920_df.append(new_match_data)
# 					break
# 				except:
# 					print("stopped at {}, row = {} out of {}".format(i, index, len(DataFrame.index)))
# 					time.sleep(15)
# 					match_request = requests.get(
# 						'https://theorangealliance.org/api/{}/matches'.format(i),
# 						headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
# 					)
# 					if str(match_request) == "<Response [429]>":
# 						print("trying again")
# 					pass

# else:
# 	print("No new matches to add")

# if all_matches_1920_df.empty == False:
	# all_matches_1920_df = all_matches_1920_df[["match_key", "event_key", "red_score", "blue_score", "red_penalty", "blue_penalty", "red_auto_score", "blue_auto_score", "red_tele_score", "blue_tele_score", "red_end_score", "blue_end_score", "participants"]]
	# useable_matches_1920_df = useable_matches_1920_df[["match_key", "event_key", "red_score", "blue_score", "red_penalty", "blue_penalty", "red_auto_score", "blue_auto_score", "red_tele_score", "blue_tele_score", "red_end_score", "blue_end_score", "participants"]]


	# all_matches_1920_df["score_diff"] = all_matches_1920_df["red_score"] - all_matches_1920_df["blue_score"]
	# useable_matches_1920_df["score_diff"] = useable_matches_1920_df["red_score"] - useable_matches_1920_df["blue_score"]

	# def winner_num(x):
	# 	if x > 0:
	# 		return 0
	# 	if x < 0:
	# 		return 1
	# 	return 2

	# all_matches_1920_df["match_winner"] = all_matches_1920_df["score_diff"].apply(winner_num)
	# useable_matches_1920_df["match_winner"] = useable_matches_1920_df["score_diff"].apply(winner_num)

	# row_num = 0

	# for i in all_matches_1920_df["participants"]:
	# 	participantsL = []
	# 	for j in i.split(","):
	# 		if "'team': " in j:
	# 			team = j.split(" ")[3]
	# 			team = int(str(team).replace("'", ""))
	# 			team = int(team)
	# 			participantsL.append(team)

	# 	if len(participantsL) == 4:
	# 		all_matches_1920_df.loc[row_num, "red_team_1"] = participantsL[0]
	# 		all_matches_1920_df.loc[row_num, "red_team_2"] = participantsL[1]
	# 		all_matches_1920_df.loc[row_num, "blue_team_1"] = participantsL[2]
	# 		all_matches_1920_df.loc[row_num, "blue_team_2"] = participantsL[3]
	# 	else:
	# 		all_matches_1920_df = all_matches_1920_df.drop(row_num)
	# 	row_num = row_num + 1

	# row_num = 0

	# for i in useable_matches_1920_df["participants"]:
	# 	participantsL = []
	# 	for j in i.split(","):
	# 		if "'team': " in j:
	# 			team = j.split(" ")[3]
	# 			team = int(str(team).replace("'", ""))
	# 			team = int(team)
	# 			participantsL.append(team)

	# 	if len(participantsL) == 4:
	# 		useable_matches_1920_df.loc[row_num, "red_team_1"] = participantsL[0]
	# 		useable_matches_1920_df.loc[row_num, "red_team_2"] = participantsL[1]
	# 		useable_matches_1920_df.loc[row_num, "blue_team_1"] = participantsL[2]
	# 		useable_matches_1920_df.loc[row_num, "blue_team_2"] = participantsL[3]
	# 	else:
	# 		useable_matches_1920_df = useable_matches_1920_df.drop(row_num)
	# 	row_num = row_num + 1

	# all_matches_1920_df = all_matches_1920_df.dropna()
	# useable_matches_1920_df = useable_matches_1920_df.dropna()

	# all_matches_1920_df = all_matches_1920_df.reset_index()
	# all_matches_1920_df = all_matches_1920_df.drop(columns=["index"])

	# useable_matches_1920_df = useable_matches_1920_df.reset_index()
	# useable_matches_1920_df = useable_matches_1920_df.drop(columns=["index"])

	# all_matches_1920_df.to_sql("all_matches_1920", con=conn, if_exists="append")
	# useable_matches_1920_df.to_sql("useable_matches_1920", con=conn, if_exists="append")

# print(list(events_1920_df))

print(future_events_1920_df.loc[future_events_1920_df.event_name == "2020 Pennsylvania Championship"])

conn.close()