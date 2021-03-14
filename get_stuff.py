import numpy as np
import pandas as pd
import requests
import json
from datetime import date, timedelta, datetime
import time
import sqlite3
from sqlite3 import Error
import statistics

are_new_matches = False
needs_math_done = False
today = date.today()

conn = sqlite3.connect('data.db') #Connecting to database
c = conn.cursor()

event_request_1920 = requests.get(
	'https://theorangealliance.org/api/event?season_key=1920',
	headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
) #Calling for all this year's events
events_1920 = json.loads(event_request_1920.content)
events_1920_df = pd.DataFrame(events_1920)


def date_parse(x): #Formatting start_date for events, removing time
	list = []
	list = x.split("T")
	return list[0]

events_1920_df["start_date"] = events_1920_df["start_date"].apply(date_parse)

events_1920_df = events_1920_df[["event_key", "region_key", "event_code", "event_type_key", "event_name", "start_date", "city", "venue", "website"]]
events_1920_df = events_1920_df.sort_values("start_date")

events_1920_df = events_1920_df.reset_index()
events_1920_df = events_1920_df.drop(columns=["index"])
events_list_by_date = []

events_1920_df.to_sql("events_1920", con=conn, if_exists="replace")

#MOVING ON TO GETTING MATCHES

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
			print("Stopped while importing matches")
			time.sleep(30)
			pass
	if all_matches_df.empty == True:
		all_matches_df = pd.DataFrame(matches_start)
	else:
		new_match_df = pd.DataFrame(matches_start)
		all_matches_df = all_matches_df.append(new_match_df)
	lastSize = len(matches_start)
	count = count + 1

events_with_matches_keys = all_matches_df["event_key"].unique().tolist()

all_matches_df = all_matches_df.reset_index()
all_matches_df = all_matches_df.drop(columns=["index"])

print(all_matches_df.loc[0, "participants"])

def order_num(x):
	try:
		return events_list_by_date.index(x)
	except:
		return -1

c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='matches_1920'")

if c.fetchone()[0]>0 :
	previously_logged_matches_1920_df = pd.read_sql_query("SELECT * FROM matches_1920", conn)
else:
	previously_logged_matches_1920_df = pd.DataFrame()


all_matches_df = all_matches_df.sort_values("match_start_time")

all_matches_df = all_matches_df.reset_index()
all_matches_df = all_matches_df.drop(columns=["index"])

unadded_matches_df = pd.DataFrame(all_matches_df)

if previously_logged_matches_1920_df.empty == False:
	previously_logged_mkeys = previously_logged_matches_1920_df["match_key"].tolist()
	unadded_matches_df = unadded_matches_df.drop(unadded_matches_df.loc[unadded_matches_df["match_key"].isin(previously_logged_mkeys)], axis=1)

unadded_matches_df = unadded_matches_df.reset_index()
unadded_matches_df = unadded_matches_df.drop(columns=["index"])

if unadded_matches_df.empty == False:
	are_new_matches = True
	unadded_event_keys = unadded_matches_df["event_key"].unique().tolist()

if are_new_matches:
	event_matches_df = pd.DataFrame()
	bad_events_list = []
	for i in unadded_event_keys:
		index = unadded_event_keys.index(i)
		while True:
			try:
				event_matches_request = requests.get(
					'https://theorangealliance.org/api/event/{}/matches'.format(i),
					headers={'Content-Type': 'application/json', 'X-TOA-Key': 'ef98a4e91bcabfcc23d2241046f3894e3521ab605a30af96b2f0c6a30f0fdcdf', 'X-Application-Origin': 'roboDojo'},
				)
				event_matches = json.loads(event_matches_request.content)
				break
			except:
				print(event_matches_request)
				print("stopped at {}, row = {} out of {}".format(i, index, len(unadded_event_keys)))
				time.sleep(15)
				pass

		if event_matches_df.empty == True:
			event_matches_df = pd.DataFrame(event_matches)
		else:
			new_match_df2 = pd.DataFrame(event_matches)
			if new_match_df2.empty == True:
				bad_events_list.append(i)
			event_matches_df = event_matches_df.append(new_match_df2)

	if len(bad_events_list) > 0:
		event_matches_df = event_matches_df.drop(event_matches_df.loc[event_matches_df["event_key"].isin(bad_events_list)])
	event_matches_df = event_matches_df.reset_index()
	event_matches_df = event_matches_df.drop(columns=["index"])

	row_num = 0
	finals_indexes = []

	for i in event_matches_df["participants"]:
		participantsL = []
		i_string = str(i)
		for j in i_string.split(","):
			if "'team': " in j:
				team = j.split(" ")[3]
				team = int(str(team).replace("'", ""))
				team = int(team)
				participantsL.append(team)

		if len(participantsL) == 4:
			event_matches_df.loc[row_num, "red_team_1"] = participantsL[0]
			event_matches_df.loc[row_num, "red_team_2"] = participantsL[1]
			event_matches_df.loc[row_num, "blue_team_1"] = participantsL[2]
			event_matches_df.loc[row_num, "blue_team_2"] = participantsL[3]
		else:
			finals_indexes.append(row_num)

		if row_num % 1000 == 0:
			print(row_num)

		row_num = row_num + 1

	event_matches_df = event_matches_df.drop(finals_indexes)
	event_matches_df = event_matches_df.drop(columns=["tournament_level", "scheduled_time", "match_name", "play_number", "field_number", "prestart_time", "prestart_count", "cycle_time", "video_url", "participants"])
	event_matches_df = previously_logged_matches_1920_df.append(event_matches_df)

	used_events_list = event_matches_df["event_key"].unique().tolist()
	used_events_df = events_1920_df.loc[events_1920_df["event_key"].isin(used_events_list)]
	used_events_df = used_events_df.sort_values("start_date")
	event_matches_df = event_matches_df.reset_index()
	event_matches_df = event_matches_df.drop(columns=["index"])

	event_matches_df.to_sql("matches_1920", con=conn, if_exists="replace")

else:
	event_matches_df = previously_logged_matches_1920_df
	print("No new matches")


print("MOVING ON TO MATH")

c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='ML_matches_1920'")

if c.fetchone()[0]>0 :
	previously_logged_ml_matches_df = pd.read_sql_query("SELECT * FROM ML_matches_1920", conn)
else:
	previously_logged_ml_matches_df = pd.DataFrame()

if previously_logged_ml_matches_df.empty == True:
	event_matches_df = previously_logged_matches_1920_df
	needs_math_done = True

def winner_num(x):
	if x > 0:
		return 0
	if x < 0:
		return 1
	return 2



ml_all_matches_df = event_matches_df
ml_all_matches_df["score_diff_red"] = ml_all_matches_df["red_score"] - ml_all_matches_df["blue_score"]
ml_all_matches_df["score_diff_blue"] = ml_all_matches_df["blue_score"] - ml_all_matches_df["red_score"]

ml_all_matches_df["score_diff_red_auto"] = ml_all_matches_df["red_auto_score"] - ml_all_matches_df["blue_auto_score"]
ml_all_matches_df["score_diff_blue_auto"] = ml_all_matches_df["blue_auto_score"] - ml_all_matches_df["red_auto_score"]

ml_all_matches_df["score_diff_red_tele"] = ml_all_matches_df["red_tele_score"] - ml_all_matches_df["blue_tele_score"]
ml_all_matches_df["score_diff_blue_tele"] = ml_all_matches_df["blue_tele_score"] - ml_all_matches_df["red_tele_score"]

ml_all_matches_df["score_diff_red_end"] = ml_all_matches_df["red_end_score"] - ml_all_matches_df["blue_end_score"]
ml_all_matches_df["score_diff_blue_end"] = ml_all_matches_df["blue_end_score"] - ml_all_matches_df["red_end_score"]

ml_all_matches_df["match_winner"] = ml_all_matches_df["score_diff_red"].apply(winner_num)


teamsList = []
ml_all_matches_df["red_team_1"].apply(lambda x: teamsList.append(x))
ml_all_matches_df["red_team_2"].apply(lambda x: teamsList.append(x))
ml_all_matches_df["blue_team_1"].apply(lambda x: teamsList.append(x))
ml_all_matches_df["blue_team_2"].apply(lambda x: teamsList.append(x))

teams = pd.DataFrame()
teams["team_numbers"] = teamsList
teams = teams.sort_values("team_numbers")
teamsList = teams["team_numbers"].unique()


ml_all_matches_df = ml_all_matches_df.reset_index()
ml_all_matches_df = ml_all_matches_df.drop(columns=["index"])


team_games_played = {}
team_games_played_per_comp = {}
team_comps_played = {}
teams_in_events = {}
previous_oprs = {}
previous_auto_oprs = {}
previous_tele_oprs = {}
previous_end_oprs = {}
previous_ccwms = {}
previous_auto_ccwms = {}
previous_tele_ccwms = {}
previous_end_ccwms = {}
previous_scores = {}
previous_auto_scores = {}
previous_tele_scores = {}
previous_end_scores = {}
previous_comp = ""

unique_event_keys = ml_all_matches_df["event_key"].unique().tolist()
for i in unique_event_keys:
	teamsListEvents = []
	ml_all_matches_df["red_team_1"].loc[ml_all_matches_df["event_key"] == i].apply(lambda x: teamsListEvents.append(x))
	ml_all_matches_df["red_team_2"].loc[ml_all_matches_df["event_key"] == i].apply(lambda x: teamsListEvents.append(x))
	ml_all_matches_df["blue_team_1"].loc[ml_all_matches_df["event_key"] == i].apply(lambda x: teamsListEvents.append(x))
	ml_all_matches_df["blue_team_2"].loc[ml_all_matches_df["event_key"] == i].apply(lambda x: teamsListEvents.append(x))
	teamsUniqueList = set(teamsListEvents)
	teamsListEvents = list(teamsUniqueList)
	teams_in_events.update({i: teamsListEvents})

for i in teamsList:
	team_games_played.update({i: 0})
	team_games_played_per_comp.update({i: 0})
	team_comps_played.update({i: 0})
	previous_oprs.update({i: list([])})
	previous_auto_oprs.update({i: list([])})
	previous_tele_oprs.update({i: list([])})
	previous_end_oprs.update({i: list([])})
	previous_ccwms.update({i: list([])})
	previous_auto_ccwms.update({i: list([])})
	previous_tele_ccwms.update({i: list([])})
	previous_end_ccwms.update({i: list([])})
	previous_scores.update({i: list([])})
	previous_auto_scores.update({i: list([])})
	previous_tele_scores.update({i: list([])})
	previous_end_scores.update({i: list([])})

is_first_match = False
is_new_comp = False
previous_comp = ""

for i in range(len(ml_all_matches_df)):
	red_team_1 = ml_all_matches_df.loc[i, "red_team_1"]
	red_team_2 = ml_all_matches_df.loc[i, "red_team_2"]
	blue_team_1 = ml_all_matches_df.loc[i, "blue_team_1"]
	blue_team_2 = ml_all_matches_df.loc[i, "blue_team_2"]

	if i in index_first_matches_list:
		ml_all_matches_df.loc[i, "isFirstMatch"] = True
	else:
		ml_all_matches_df.loc[i, "isFirstMatch"] = False

	event_key = ml_all_matches_df.loc[i, "event_key"]
	
	ml_all_matches_df.loc[i, "red_team_1_games_played"] = team_games_played[red_team_1]
	ml_all_matches_df.loc[i, "red_team_2_games_played"] = team_games_played[red_team_2]
	ml_all_matches_df.loc[i, "blue_team_1_games_played"] = team_games_played[blue_team_1]
	ml_all_matches_df.loc[i, "blue_team_2_games_played"] = team_games_played[blue_team_2]

	ml_all_matches_df.loc[i, "red_team_1_games_played_per_comp"] = team_games_played_per_comp[red_team_1]
	ml_all_matches_df.loc[i, "red_team_2_games_played_per_comp"] = team_games_played_per_comp[red_team_2]
	ml_all_matches_df.loc[i, "blue_team_1_games_played_per_comp"] = team_games_played_per_comp[blue_team_1]
	ml_all_matches_df.loc[i, "blue_team_2_games_played_per_comp"] = team_games_played_per_comp[blue_team_2]

	ml_all_matches_df.loc[i, "red_team_1_comps_played"] = team_comps_played[red_team_1]
	ml_all_matches_df.loc[i, "red_team_2_comps_played"] = team_comps_played[red_team_2]
	ml_all_matches_df.loc[i, "blue_team_1_comps_played"] = team_comps_played[blue_team_1]
	ml_all_matches_df.loc[i, "blue_team_2_comps_played"] = team_comps_played[blue_team_2]

	if event_key != previous_comp:
		playersListRedTEMPLATE = []
		playersListBlueTEMPLATE = []
		for j in teams_in_events[event_key]:
			playersListRedTEMPLATE.append(0)
			playersListBlueTEMPLATE.append(0)

		playersListRed = playersListRedTEMPLATE.copy()
		playersListBlue = playersListBlueTEMPLATE.copy()

		playersListRed[teams_in_events[event_key].index(red_team_1)] = 1
		playersListRed[teams_in_events[event_key].index(red_team_2)] = 1
		playersListBlue[teams_in_events[event_key].index(blue_team_1)] = 1
		playersListBlue[teams_in_events[event_key].index(blue_team_2)] = 1

		teamsArray = np.array(playersListRed)
		teamsArray = np.vstack([teamsArray, playersListBlue])

		scoresArray = np.array(ml_all_matches_df.loc[i, "red_score"])
		scoresArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "blue_score"]])

		marginsArray = np.array(ml_all_matches_df.loc[i, "score_diff"])
		marginsArray = np.vstack([marginsArray, ml_all_matches_df.loc[i, "blue_score"] - ml_all_matches_df.loc[i, "red_score"]])
	else:
		playersListRed = playersListRedTEMPLATE.copy()
		playersListBlue = playersListBlueTEMPLATE.copy()

		playersListRed[teams_in_events[event_key].index(red_team_1)] = 1
		playersListRed[teams_in_events[event_key].index(red_team_2)] = 1
		playersListBlue[teams_in_events[event_key].index(blue_team_1)] = 1
		playersListBlue[teams_in_events[event_key].index(blue_team_2)] = 1

		teamsArray = np.vstack([teamsArray, playersListRed])
		teamsArray = np.vstack([teamsArray, playersListBlue])

		scoresArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "red_score"]])
		scoresArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "blue_score"]])

		marginsArray = np.vstack([marginsArray, ml_all_matches_df.loc[i, "score_diff"]])
		marginsArray = np.vstack([marginsArray, ml_all_matches_df.loc[i, "blue_score"] - ml_all_matches_df.loc[i, "red_score"]])
		
	if previous_oprs[red_team_1] == [] and ml_all_matches_df.loc[i, "red_team_1_games_played_per_comp"] > 0:
		try:
			ml_all_matches_df.loc[i, "red_team_1_avg_previous_oprs"] = oprArray[teams_in_events[event_key].index(red_team_1)]
			ml_all_matches_df.loc[i, "red_team_1_highest_opr"] = oprArray[teams_in_events[event_key].index(red_team_1)]
		except:
			pass
	if previous_oprs[red_team_2] == [] and ml_all_matches_df.loc[i, "red_team_2_games_played_per_comp"] > 0:
		try:
			ml_all_matches_df.loc[i, "red_team_2_avg_previous_oprs"] = oprArray[teams_in_events[event_key].index(red_team_2)]
			ml_all_matches_df.loc[i, "red_team_2_highest_opr"] = oprArray[teams_in_events[event_key].index(red_team_2)]
		except:
			pass
	if previous_oprs[blue_team_1] == [] and ml_all_matches_df.loc[i, "blue_team_1_games_played_per_comp"] > 0:
		try:
			ml_all_matches_df.loc[i, "blue_team_1_avg_previous_oprs"] = oprArray[teams_in_events[event_key].index(blue_team_1)]
			ml_all_matches_df.loc[i, "blue_team_1_highest_opr"] = oprArray[teams_in_events[event_key].index(blue_team_1)]
		except:
			pass
	if previous_oprs[blue_team_2] == [] and ml_all_matches_df.loc[i, "blue_team_2_games_played_per_comp"] > 0:
		try:
			ml_all_matches_df.loc[i, "blue_team_2_avg_previous_oprs"] = oprArray[teams_in_events[event_key].index(blue_team_2)]
			ml_all_matches_df.loc[i, "blue_team_2_highest_opr"] = oprArray[teams_in_events[event_key].index(blue_team_2)]
		except:
			pass

	if previous_ccwms[red_team_1] == [] and ml_all_matches_df.loc[i, "red_team_1_games_played_per_comp"] > 0:
		try:
			ml_all_matches_df.loc[i, "red_team_1_avg_previous_ccwms"] = ccwmArray[teams_in_events[event_key].index(red_team_1)]
			ml_all_matches_df.loc[i, "red_team_1_highest_ccwm"] = ccwmArray[teams_in_events[event_key].index(red_team_1)]
		except:
			pass
	if previous_ccwms[red_team_2] == [] and ml_all_matches_df.loc[i, "red_team_2_games_played_per_comp"] > 0:
		try:
			ml_all_matches_df.loc[i, "red_team_2_avg_previous_ccwms"] = ccwmArray[teams_in_events[event_key].index(red_team_2)]
			ml_all_matches_df.loc[i, "red_team_2_highest_ccwm"] = ccwmArray[teams_in_events[event_key].index(red_team_2)]
		except:
			pass
	if previous_ccwms[blue_team_1] == [] and ml_all_matches_df.loc[i, "blue_team_1_games_played_per_comp"] > 0:
		try:
			ml_all_matches_df.loc[i, "blue_team_1_avg_previous_ccwms"] = ccwmArray[teams_in_events[event_key].index(blue_team_1)]
			ml_all_matches_df.loc[i, "blue_team_1_highest_ccwm"] = ccwmArray[teams_in_events[event_key].index(blue_team_1)]
		except:
			pass
	if previous_ccwms[blue_team_2] == [] and ml_all_matches_df.loc[i, "blue_team_2_games_played_per_comp"] > 0:
		try:
			ml_all_matches_df.loc[i, "blue_team_2_avg_previous_ccwms"] = ccwmArray[teams_in_events[event_key].index(blue_team_2)]
			ml_all_matches_df.loc[i, "blue_team_2_highest_ccwm"] = ccwmArray[teams_in_events[event_key].index(blue_team_2)]
		except:
			pass

	if i not in index_first_matches_list:
		oprArray = np.linalg.lstsq(teamsArray, scoresArray, rcond=None)[0]
		ccwmArray = np.linalg.lstsq(teamsArray, marginsArray, rcond=None)[0]

		ml_all_matches_df.loc[i, "red_team_1_opr"] = oprArray[teams_in_events[event_key].index(red_team_1)]
		ml_all_matches_df.loc[i, "red_team_2_opr"] = oprArray[teams_in_events[event_key].index(red_team_2)]
		ml_all_matches_df.loc[i, "blue_team_1_opr"] = oprArray[teams_in_events[event_key].index(blue_team_1)]
		ml_all_matches_df.loc[i, "blue_team_2_opr"] = oprArray[teams_in_events[event_key].index(blue_team_2)]

		ml_all_matches_df.loc[i, "red_team_1_ccwm"] = ccwmArray[teams_in_events[event_key].index(red_team_1)]
		ml_all_matches_df.loc[i, "red_team_2_ccwm"] = ccwmArray[teams_in_events[event_key].index(red_team_2)]
		ml_all_matches_df.loc[i, "blue_team_1_ccwm"] = ccwmArray[teams_in_events[event_key].index(blue_team_1)]
		ml_all_matches_df.loc[i, "blue_team_2_ccwm"] = ccwmArray[teams_in_events[event_key].index(blue_team_2)]

	
	ml_all_matches_df.loc[i, "red_team_1_previous_oprs"] = str(previous_oprs[red_team_1])
	ml_all_matches_df.loc[i, "red_team_2_previous_oprs"] = str(previous_oprs[red_team_2])
	ml_all_matches_df.loc[i, "blue_team_1_previous_oprs"] = str(previous_oprs[blue_team_1])
	ml_all_matches_df.loc[i, "blue_team_2_previous_oprs"] = str(previous_oprs[blue_team_2])

	ml_all_matches_df.loc[i, "red_team_1_previous_ccwms"] = str(previous_ccwms[red_team_1])
	ml_all_matches_df.loc[i, "red_team_2_previous_ccwms"] = str(previous_ccwms[red_team_2])
	ml_all_matches_df.loc[i, "blue_team_1_previous_ccwms"] = str(previous_ccwms[blue_team_1])
	ml_all_matches_df.loc[i, "blue_team_2_previous_ccwms"] = str(previous_ccwms[blue_team_2])

	if previous_oprs[red_team_1] != []:
		ml_all_matches_df.loc[i, "red_team_1_avg_previous_oprs"] = statistics.mean(previous_oprs[red_team_1])
		ml_all_matches_df.loc[i, "red_team_1_highest_opr"] = max(previous_oprs[red_team_1])
	if previous_oprs[red_team_2] != []:
		ml_all_matches_df.loc[i, "red_team_2_avg_previous_oprs"] = statistics.mean(previous_oprs[red_team_2])
		ml_all_matches_df.loc[i, "red_team_2_highest_opr"] = max(previous_oprs[red_team_2])
	if previous_oprs[blue_team_1] != []:
		ml_all_matches_df.loc[i, "blue_team_1_avg_previous_oprs"] = statistics.mean(previous_oprs[blue_team_1])
		ml_all_matches_df.loc[i, "blue_team_1_highest_opr"] = max(previous_oprs[blue_team_1])
	if previous_oprs[blue_team_2] != []:
		ml_all_matches_df.loc[i, "blue_team_2_avg_previous_oprs"] = statistics.mean(previous_oprs[blue_team_2])
		ml_all_matches_df.loc[i, "blue_team_2_highest_opr"] = max(previous_oprs[blue_team_2])

	if previous_ccwms[red_team_1] != []:
		ml_all_matches_df.loc[i, "red_team_1_avg_previous_ccwms"] = statistics.mean(previous_ccwms[red_team_1])
		ml_all_matches_df.loc[i, "red_team_1_highest_ccwm"] = max(previous_ccwms[red_team_1])
	if previous_ccwms[red_team_2] != []:
		ml_all_matches_df.loc[i, "red_team_2_avg_previous_ccwms"] = statistics.mean(previous_ccwms[red_team_2])
		ml_all_matches_df.loc[i, "red_team_2_highest_ccwm"] = max(previous_ccwms[red_team_2])
	if previous_ccwms[blue_team_1] != []:
		ml_all_matches_df.loc[i, "blue_team_1_avg_previous_ccwms"] = statistics.mean(previous_ccwms[blue_team_1])
		ml_all_matches_df.loc[i, "blue_team_1_highest_ccwm"] = max(previous_ccwms[blue_team_1])
	if previous_ccwms[blue_team_2] != []:
		ml_all_matches_df.loc[i, "blue_team_2_avg_previous_ccwms"] = statistics.mean(previous_ccwms[blue_team_2])
		ml_all_matches_df.loc[i, "blue_team_2_highest_ccwm"] = max(previous_ccwms[blue_team_2])
	
	if (i != (len(ml_all_matches_df.index) - 1)):
		if ml_all_matches_df.loc[i + 1, "event_key"] != event_key or i == len(ml_all_matches_df) - 1:
			for k in teams_in_events[event_key]:
				previous_oprs[k].append(oprArray[teams_in_events[event_key].index(k)][0])
				previous_ccwms[k].append(ccwmArray[teams_in_events[event_key].index(k)][0])
				last_opr[k] = oprArray[teams_in_events[event_key].index(k)][0]
				last_ccwm[k] = ccwmArray[teams_in_events[event_key].index(k)][0]

	previous_comp = event_key

	if i % 1000 == 0:
		print(i)