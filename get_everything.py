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

# events_list_by_date = used_events_df["event_key"].tolist()
# event_matches_df["event_order"] = event_matches_df["event_key"].apply(order_num)
# event_matches_df = event_matches_df.sort_values("event_order")
# event_matches_df = event_matches_df.drop(event_matches_df.loc[event_matches_df["event_order"] == -1], axis=1)
# event_matches_df = event_matches_df.dropna()
# event_matches_df = event_matches_df.drop(columns=["event_order"])

# event_matches_df.to_sql("matches_1920", con=conn, if_exists="replace")

#MOVING ON TO MATH PART
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
	is_first_match = False
	is_new_comp = False
	red_team_1 = ml_all_matches_df.loc[i, "red_team_1"]
	red_team_2 = ml_all_matches_df.loc[i, "red_team_2"]
	blue_team_1 = ml_all_matches_df.loc[i, "blue_team_1"]
	blue_team_2 = ml_all_matches_df.loc[i, "blue_team_2"]
	eventKey = ml_all_matches_df.loc[i, "event_key"]
	red_score = ml_all_matches_df.loc[i, "red_score"]
	# red_auto_score = ml_all_matches_df.loc[i, "red_auto_score"]
	# red_tele_score = ml_all_matches_df.loc[i, "red_tele_score"]
	# red_end_score = ml_all_matches_df.loc[i, "red_end_score"]
	blue_score = ml_all_matches_df.loc[i, "blue_score"]
	# blue_auto_score = ml_all_matches_df.loc[i, "blue_auto_score"]
	# blue_tele_score = ml_all_matches_df.loc[i, "blue_tele_score"]
	# blue_end_score = ml_all_matches_df.loc[i, "blue_end_score"]

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

	if team_games_played[red_team_1] == 0:
		is_first_match = True
	elif team_games_played[red_team_2] == 0:
		is_first_match = True
	elif team_games_played[blue_team_1] == 0:
		is_first_match = True
	elif team_games_played[blue_team_2] == 0:
		is_first_match = True

	if eventKey != previous_comp:
		is_new_comp = True

	if is_new_comp == True:
		if previous_comp != "":
			oprArray = np.linalg.lstsq(teamsArray, scoresArray, rcond=None)[0]
			# autoOprArray = np.linalg.lstsq(teamsArray, autoScoresArray, rcond=None)[0]
			# teleOprArray = np.linalg.lstsq(teamsArray, teleScoresArray, rcond=None)[0]
			# endOprArray = np.linalg.lstsq(teamsArray, endScoresArray, rcond=None)[0]

			ccwmArray = np.linalg.lstsq(teamsArray, marginsArray, rcond=None)[0]
			# autoCcwmArray = np.linalg.lstsq(teamsArray, autoMarginsArray, rcond=None)[0]
			# teleCcwmArray = np.linalg.lstsq(teamsArray, teleMarginsArray, rcond=None)[0]
			# endCcwmArray = np.linalg.lstsq(teamsArray, endMarginsArray, rcond=None)[0]

			for k in teams_in_events[previous_comp]:
				team_games_played_per_comp[k] = 0
				team_comps_played[k] = team_comps_played[k] + 1
				previous_oprs[k].append(oprArray[teams_in_events[previous_comp].index(k)][0])
				# previous_auto_oprs[k].append(autoOprArray[teams_in_events[previous_comp].index(k)][0])
				# previous_tele_oprs[k].append(teleOprArray[teams_in_events[previous_comp].index(k)][0])
				# previous_end_oprs[k].append(endOprArray[teams_in_events[previous_comp].index(k)][0])
				previous_ccwms[k].append(ccwmArray[teams_in_events[previous_comp].index(k)][0])
				# previous_auto_ccwms[k].append(autoCcwmArray[teams_in_events[previous_comp].index(k)][0])
				# previous_tele_ccwms[k].append(teleCcwmArray[teams_in_events[previous_comp].index(k)][0])
				# previous_end_ccwms[k].append(endCcwmArray[teams_in_events[previous_comp].index(k)][0])

		playersListRedTEMPLATE = []
		playersListBlueTEMPLATE = []

		for j in teams_in_events[eventKey]:
			playersListRedTEMPLATE.append(0)
			playersListBlueTEMPLATE.append(0)


		playersListRed = playersListRedTEMPLATE.copy()
		playersListBlue = playersListBlueTEMPLATE.copy()
		playersListRed[teams_in_events[eventKey].index(red_team_1)] = 1
		playersListRed[teams_in_events[eventKey].index(red_team_2)] = 1
		playersListBlue[teams_in_events[eventKey].index(blue_team_1)] = 1
		playersListBlue[teams_in_events[eventKey].index(blue_team_2)] = 1

		if team_comps_played[red_team_1] != 0:
			ml_all_matches_df.loc[i, "red_team_1_opr"] = previous_oprs[red_team_1][len(previous_oprs[red_team_1]) - 1]
			# ml_all_matches_df.loc[i, "red_team_1_auto_opr"] = previous_auto_oprs[red_team_1][len(previous_auto_oprs[red_team_1]) - 1]
			# ml_all_matches_df.loc[i, "red_team_1_tele_opr"] = previous_tele_oprs[red_team_1][len(previous_tele_oprs[red_team_1]) - 1]
			# ml_all_matches_df.loc[i, "red_team_1_end_opr"] = previous_end_oprs[red_team_1][len(previous_end_oprs[red_team_1]) - 1]

			ml_all_matches_df.loc[i, "red_team_1_ccwm"] = previous_ccwms[red_team_1][len(previous_ccwms[red_team_1]) - 1]
			# ml_all_matches_df.loc[i, "red_team_1_auto_ccwm"] = previous_auto_ccwms[red_team_1][len(previous_auto_ccwms[red_team_1]) - 1]
			# ml_all_matches_df.loc[i, "red_team_1_tele_ccwm"] = previous_tele_ccwms[red_team_1][len(previous_tele_ccwms[red_team_1]) - 1]
			# ml_all_matches_df.loc[i, "red_team_1_end_ccwm"] = previous_end_ccwms[red_team_1][len(previous_end_ccwms[red_team_1]) - 1]

			ml_all_matches_df.loc[i, "red_team_1_avg_opr"] = statistics.mean(previous_oprs[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_avg_auto_opr"] = statistics.mean(previous_auto_oprs[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_avg_tele_opr"] = statistics.mean(previous_tele_oprs[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_avg_end_opr"] = statistics.mean(previous_end_oprs[red_team_1])

			ml_all_matches_df.loc[i, "red_team_1_avg_ccwm"] = statistics.mean(previous_ccwms[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_avg_auto_ccwm"] = statistics.mean(previous_auto_ccwms[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_avg_tele_ccwm"] = statistics.mean(previous_tele_ccwms[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_avg_end_ccwm"] = statistics.mean(previous_end_ccwms[red_team_1])

			ml_all_matches_df.loc[i, "red_team_1_high_opr"] = max(previous_oprs[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_high_auto_opr"] = max(previous_auto_oprs[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_high_tele_opr"] = max(previous_tele_oprs[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_high_end_opr"] = max(previous_end_oprs[red_team_1])

			ml_all_matches_df.loc[i, "red_team_1_high_ccwm"] = max(previous_ccwms[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_high_auto_ccwm"] = max(previous_auto_ccwms[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_high_tele_ccwm"] = max(previous_tele_ccwms[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_1_high_end_ccwm"] = max(previous_end_ccwms[red_team_1])

		if team_comps_played[red_team_2] != 0:
			ml_all_matches_df.loc[i, "red_team_2_opr"] = previous_oprs[red_team_2][len(previous_oprs[red_team_2]) - 1]
			# ml_all_matches_df.loc[i, "red_team_2_auto_opr"] = previous_auto_oprs[red_team_2][len(previous_auto_oprs[red_team_2]) - 1]
			# ml_all_matches_df.loc[i, "red_team_2_tele_opr"] = previous_tele_oprs[red_team_2][len(previous_tele_oprs[red_team_2]) - 1]
			# ml_all_matches_df.loc[i, "red_team_2_end_opr"] = previous_end_oprs[red_team_2][len(previous_end_oprs[red_team_2]) - 1]

			ml_all_matches_df.loc[i, "red_team_2_ccwm"] = previous_ccwms[red_team_2][len(previous_ccwms[red_team_2]) - 1]
			# ml_all_matches_df.loc[i, "red_team_2_auto_ccwm"] = previous_auto_ccwms[red_team_2][len(previous_auto_ccwms[red_team_2]) - 1]
			# ml_all_matches_df.loc[i, "red_team_2_tele_ccwm"] = previous_tele_ccwms[red_team_2][len(previous_tele_ccwms[red_team_2]) - 1]
			# ml_all_matches_df.loc[i, "red_team_2_end_ccwm"] = previous_end_ccwms[red_team_2][len(previous_end_ccwms[red_team_2]) - 1]

			ml_all_matches_df.loc[i, "red_team_2_avg_opr"] = statistics.mean(previous_oprs[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_avg_auto_opr"] = statistics.mean(previous_auto_oprs[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_avg_tele_opr"] = statistics.mean(previous_tele_oprs[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_avg_end_opr"] = statistics.mean(previous_end_oprs[red_team_2])

			ml_all_matches_df.loc[i, "red_team_2_avg_ccwm"] = statistics.mean(previous_ccwms[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_avg_auto_ccwm"] = statistics.mean(previous_auto_ccwms[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_avg_tele_ccwm"] = statistics.mean(previous_tele_ccwms[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_avg_end_ccwm"] = statistics.mean(previous_end_ccwms[red_team_2])

			ml_all_matches_df.loc[i, "red_team_2_high_opr"] = max(previous_oprs[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_high_auto_opr"] = max(previous_auto_oprs[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_high_tele_opr"] = max(previous_tele_oprs[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_high_end_opr"] = max(previous_end_oprs[red_team_2])

			ml_all_matches_df.loc[i, "red_team_2_high_ccwm"] = max(previous_ccwms[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_high_auto_ccwm"] = max(previous_auto_ccwms[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_high_tele_ccwm"] = max(previous_tele_ccwms[red_team_2])
			# ml_all_matches_df.loc[i, "red_team_2_high_end_ccwm"] = max(previous_end_ccwms[red_team_2])

		if team_comps_played[blue_team_1] != 0:
			ml_all_matches_df.loc[i, "blue_team_1_opr"] = previous_oprs[blue_team_1][len(previous_oprs[blue_team_1]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_1_auto_opr"] = previous_auto_oprs[blue_team_1][len(previous_auto_oprs[blue_team_1]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_1_tele_opr"] = previous_tele_oprs[blue_team_1][len(previous_tele_oprs[blue_team_1]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_1_end_opr"] = previous_end_oprs[blue_team_1][len(previous_end_oprs[blue_team_1]) - 1]

			ml_all_matches_df.loc[i, "blue_team_1_ccwm"] = previous_ccwms[blue_team_1][len(previous_ccwms[blue_team_1]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_1_auto_ccwm"] = previous_auto_ccwms[blue_team_1][len(previous_auto_ccwms[blue_team_1]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_1_tele_ccwm"] = previous_tele_ccwms[blue_team_1][len(previous_tele_ccwms[blue_team_1]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_1_end_ccwm"] = previous_end_ccwms[blue_team_1][len(previous_end_ccwms[blue_team_1]) - 1]

			ml_all_matches_df.loc[i, "blue_team_1_avg_opr"] = statistics.mean(previous_oprs[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_auto_opr"] = statistics.mean(previous_auto_oprs[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_tele_opr"] = statistics.mean(previous_tele_oprs[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_end_opr"] = statistics.mean(previous_end_oprs[blue_team_1])

			ml_all_matches_df.loc[i, "blue_team_1_avg_ccwm"] = statistics.mean(previous_ccwms[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_auto_ccwm"] = statistics.mean(previous_auto_ccwms[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_tele_ccwm"] = statistics.mean(previous_tele_ccwms[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_end_ccwm"] = statistics.mean(previous_end_ccwms[blue_team_1])

			ml_all_matches_df.loc[i, "blue_team_1_high_opr"] = max(previous_oprs[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_high_auto_opr"] = max(previous_auto_oprs[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_high_tele_opr"] = max(previous_tele_oprs[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_high_end_opr"] = max(previous_end_oprs[blue_team_1])

			ml_all_matches_df.loc[i, "blue_team_1_high_ccwm"] = max(previous_ccwms[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_high_auto_ccwm"] = max(previous_auto_ccwms[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_high_tele_ccwm"] = max(previous_tele_ccwms[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_1_high_end_ccwm"] = max(previous_end_ccwms[blue_team_1])

		if team_comps_played[blue_team_2] != 0:
			ml_all_matches_df.loc[i, "blue_team_2_opr"] = previous_oprs[blue_team_2][len(previous_oprs[blue_team_2]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_2_auto_opr"] = previous_auto_oprs[blue_team_2][len(previous_auto_oprs[blue_team_2]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_2_tele_opr"] = previous_tele_oprs[blue_team_2][len(previous_tele_oprs[blue_team_2]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_2_end_opr"] = previous_end_oprs[blue_team_2][len(previous_end_oprs[blue_team_2]) - 1]

			ml_all_matches_df.loc[i, "blue_team_2_ccwm"] = previous_ccwms[blue_team_2][len(previous_ccwms[blue_team_2]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_2_auto_ccwm"] = previous_auto_ccwms[blue_team_2][len(previous_auto_ccwms[blue_team_2]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_2_tele_ccwm"] = previous_tele_ccwms[blue_team_2][len(previous_tele_ccwms[blue_team_2]) - 1]
			# ml_all_matches_df.loc[i, "blue_team_2_end_ccwm"] = previous_end_ccwms[blue_team_2][len(previous_end_ccwms[blue_team_2]) - 1]

			ml_all_matches_df.loc[i, "blue_team_2_avg_opr"] = statistics.mean(previous_oprs[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_auto_opr"] = statistics.mean(previous_auto_oprs[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_tele_opr"] = statistics.mean(previous_tele_oprs[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_end_opr"] = statistics.mean(previous_end_oprs[blue_team_2])

			ml_all_matches_df.loc[i, "blue_team_2_avg_ccwm"] = statistics.mean(previous_ccwms[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_auto_ccwm"] = statistics.mean(previous_auto_ccwms[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_tele_ccwm"] = statistics.mean(previous_tele_ccwms[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_end_ccwm"] = statistics.mean(previous_end_ccwms[blue_team_2])

			ml_all_matches_df.loc[i, "blue_team_2_high_opr"] = max(previous_oprs[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_high_auto_opr"] = max(previous_auto_oprs[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_high_tele_opr"] = max(previous_tele_oprs[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_high_end_opr"] = max(previous_end_oprs[blue_team_2])

			ml_all_matches_df.loc[i, "blue_team_2_high_ccwm"] = max(previous_ccwms[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_high_auto_ccwm"] = max(previous_auto_ccwms[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_high_tele_ccwm"] = max(previous_tele_ccwms[blue_team_2])
			# ml_all_matches_df.loc[i, "blue_team_2_high_end_ccwm"] = max(previous_end_ccwms[blue_team_2])




	if not is_new_comp:
		if not is_first_match:
			ml_all_matches_df.loc[i, "red_team_1_avg_score"] = statistics.mean(previous_scores[red_team_1])
			ml_all_matches_df.loc[i, "red_team_2_avg_score"] = statistics.mean(previous_scores[red_team_2])
			ml_all_matches_df.loc[i, "blue_team_1_avg_score"] = statistics.mean(previous_scores[blue_team_1])
			ml_all_matches_df.loc[i, "blue_team_2_avg_score"] = statistics.mean(previous_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_avg_auto_score"] = statistics.mean(previous_auto_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_avg_auto_score"] = statistics.mean(previous_auto_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_auto_score"] = statistics.mean(previous_auto_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_auto_score"] = statistics.mean(previous_auto_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_avg_tele_score"] = statistics.mean(previous_tele_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_avg_tele_score"] = statistics.mean(previous_tele_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_tele_score"] = statistics.mean(previous_tele_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_tele_score"] = statistics.mean(previous_tele_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_avg_end_score"] = statistics.mean(previous_end_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_avg_end_score"] = statistics.mean(previous_end_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_end_score"] = statistics.mean(previous_end_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_end_score"] = statistics.mean(previous_end_scores[blue_team_2])


			ml_all_matches_df.loc[i, "red_team_1_high_score"] = max(previous_scores[red_team_1])
			ml_all_matches_df.loc[i, "red_team_2_high_score"] = max(previous_scores[red_team_2])
			ml_all_matches_df.loc[i, "blue_team_1_high_score"] = max(previous_scores[blue_team_1])
			ml_all_matches_df.loc[i, "blue_team_2_high_score"] = max(previous_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_high_auto_score"] = max(previous_auto_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_high_auto_score"] = max(previous_auto_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_high_auto_score"] = max(previous_auto_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_high_auto_score"] = max(previous_auto_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_high_tele_score"] = max(previous_tele_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_high_tele_score"] = max(previous_tele_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_high_tele_score"] = max(previous_tele_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_high_tele_score"] = max(previous_tele_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_high_end_score"] = max(previous_end_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_high_end_score"] = max(previous_end_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_high_end_score"] = max(previous_end_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_high_end_score"] = max(previous_end_scores[blue_team_2])


			ml_all_matches_df.loc[i, "red_team_1_avg_score"] = statistics.mean(previous_scores[red_team_1])
			ml_all_matches_df.loc[i, "red_team_2_avg_score"] = statistics.mean(previous_scores[red_team_2])
			ml_all_matches_df.loc[i, "blue_team_1_avg_score"] = statistics.mean(previous_scores[blue_team_1])
			ml_all_matches_df.loc[i, "blue_team_2_avg_score"] = statistics.mean(previous_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_avg_auto_score"] = statistics.mean(previous_auto_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_avg_auto_score"] = statistics.mean(previous_auto_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_auto_score"] = statistics.mean(previous_auto_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_auto_score"] = statistics.mean(previous_auto_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_avg_tele_score"] = statistics.mean(previous_tele_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_avg_tele_score"] = statistics.mean(previous_tele_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_tele_score"] = statistics.mean(previous_tele_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_tele_score"] = statistics.mean(previous_tele_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_avg_end_score"] = statistics.mean(previous_end_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_avg_end_score"] = statistics.mean(previous_end_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_avg_end_score"] = statistics.mean(previous_end_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_avg_end_score"] = statistics.mean(previous_end_scores[blue_team_2])


			ml_all_matches_df.loc[i, "red_team_1_high_score"] = max(previous_scores[red_team_1])
			ml_all_matches_df.loc[i, "red_team_2_high_score"] = max(previous_scores[red_team_2])
			ml_all_matches_df.loc[i, "blue_team_1_high_score"] = max(previous_scores[blue_team_1])
			ml_all_matches_df.loc[i, "blue_team_2_high_score"] = max(previous_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_high_auto_score"] = max(previous_auto_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_high_auto_score"] = max(previous_auto_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_high_auto_score"] = max(previous_auto_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_high_auto_score"] = max(previous_auto_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_high_tele_score"] = max(previous_tele_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_high_tele_score"] = max(previous_tele_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_high_tele_score"] = max(previous_tele_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_high_tele_score"] = max(previous_tele_scores[blue_team_2])

			# ml_all_matches_df.loc[i, "red_team_1_high_end_score"] = max(previous_end_scores[red_team_1])
			# ml_all_matches_df.loc[i, "red_team_2_high_end_score"] = max(previous_end_scores[red_team_2])
			# ml_all_matches_df.loc[i, "blue_team_1_high_end_score"] = max(previous_end_scores[blue_team_1])
			# ml_all_matches_df.loc[i, "blue_team_2_high_end_score"] = max(previous_end_scores[blue_team_2])

			# scoresArray = scoresArray.reshape((scoresArray.shape[0],))

			oprArray = np.linalg.lstsq(teamsArray, scoresArray, rcond=None)[0]
			# autoOprArray = np.linalg.lstsq(teamsArray, autoScoresArray, rcond=None)[0]
			# teleOprArray = np.linalg.lstsq(teamsArray, teleScoresArray, rcond=None)[0]
			# endOprArray = np.linalg.lstsq(teamsArray, endScoresArray, rcond=None)[0]

			ccwmArray = np.linalg.lstsq(teamsArray, marginsArray, rcond=None)[0]
			# autoCcwmArray = np.linalg.lstsq(teamsArray, autoMarginsArray, rcond=None)[0]
			# teleCcwmArray = np.linalg.lstsq(teamsArray, teleMarginsArray, rcond=None)[0]
			# endCcwmArray = np.linalg.lstsq(teamsArray, endMarginsArray, rcond=None)[0]

			if team_comps_played[red_team_1] != 0:
				ml_all_matches_df.loc[i, "red_team_1_opr"] = oprArray[teams_in_events[eventKey].index(red_team_1)]
				# ml_all_matches_df.loc[i, "red_team_1_auto_opr"] = autoOprArray[teams_in_events[eventKey].index[red_team_1]]
				# ml_all_matches_df.loc[i, "red_team_1_tele_opr"] = teleOprArray[teams_in_events[eventKey].index[red_team_1]]
				# ml_all_matches_df.loc[i, "red_team_1_end_opr"] = endOprArray[teams_in_events[eventKey].index[red_team_1]]

				ml_all_matches_df.loc[i, "red_team_1_ccwm"] = ccwmArray[teams_in_events[eventKey].index(red_team_1)]
				# ml_all_matches_df.loc[i, "red_team_1_auto_ccwm"] = autoCcwmArray[teams_in_events[eventKey].index[red_team_1]]
				# ml_all_matches_df.loc[i, "red_team_1_tele_ccwm"] = teleCcwmArray[teams_in_events[eventKey].index[red_team_1]]
				# ml_all_matches_df.loc[i, "red_team_1_end_ccwm"] = endCcwmArray[teams_in_events[eventKey].index[red_team_1]]

				ml_all_matches_df.loc[i, "red_team_1_avg_opr"] = statistics.mean(previous_oprs[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_avg_auto_opr"] = statistics.mean(previous_auto_oprs[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_avg_tele_opr"] = statistics.mean(previous_tele_oprs[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_avg_end_opr"] = statistics.mean(previous_end_oprs[red_team_1])

				ml_all_matches_df.loc[i, "red_team_1_avg_ccwm"] = statistics.mean(previous_ccwms[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_avg_auto_ccwm"] = statistics.mean(previous_auto_ccwms[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_avg_tele_ccwm"] = statistics.mean(previous_tele_ccwms[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_avg_end_ccwm"] = statistics.mean(previous_end_ccwms[red_team_1])

				ml_all_matches_df.loc[i, "red_team_1_high_opr"] = max(previous_oprs[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_high_auto_opr"] = max(previous_auto_oprs[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_high_tele_opr"] = max(previous_tele_oprs[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_high_end_opr"] = max(previous_end_oprs[red_team_1])

				ml_all_matches_df.loc[i, "red_team_1_high_ccwm"] = max(previous_ccwms[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_high_auto_ccwm"] = max(previous_auto_ccwms[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_high_tele_ccwm"] = max(previous_tele_ccwms[red_team_1])
				# ml_all_matches_df.loc[i, "red_team_1_high_end_ccwm"] = max(previous_end_ccwms[red_team_1])

			if team_comps_played[red_team_2] != 0:
				ml_all_matches_df.loc[i, "red_team_2_opr"] = oprArray[teams_in_events[eventKey].index(red_team_2)]
				# ml_all_matches_df.loc[i, "red_team_2_auto_opr"] = autoOprArray[teams_in_events[eventKey].index[red_team_2]]
				# ml_all_matches_df.loc[i, "red_team_2_tele_opr"] = teleOprArray[teams_in_events[eventKey].index[red_team_2]]
				# ml_all_matches_df.loc[i, "red_team_2_end_opr"] = endOprArray[teams_in_events[eventKey].index[red_team_2]]

				ml_all_matches_df.loc[i, "red_team_2_ccwm"] = ccwmArray[teams_in_events[eventKey].index(red_team_2)]
				# ml_all_matches_df.loc[i, "red_team_2_auto_ccwm"] = autoCcwmArray[teams_in_events[eventKey].index[red_team_2]]
				# ml_all_matches_df.loc[i, "red_team_2_tele_ccwm"] = teleCcwmArray[teams_in_events[eventKey].index[red_team_2]]
				# ml_all_matches_df.loc[i, "red_team_2_end_ccwm"] = endCcwmArray[teams_in_events[eventKey].index[red_team_2]]

				ml_all_matches_df.loc[i, "red_team_2_avg_opr"] = statistics.mean(previous_oprs[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_avg_auto_opr"] = statistics.mean(previous_auto_oprs[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_avg_tele_opr"] = statistics.mean(previous_tele_oprs[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_avg_end_opr"] = statistics.mean(previous_end_oprs[red_team_2])

				ml_all_matches_df.loc[i, "red_team_2_avg_ccwm"] = statistics.mean(previous_ccwms[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_avg_auto_ccwm"] = statistics.mean(previous_auto_ccwms[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_avg_tele_ccwm"] = statistics.mean(previous_tele_ccwms[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_avg_end_ccwm"] = statistics.mean(previous_end_ccwms[red_team_2])

				ml_all_matches_df.loc[i, "red_team_2_high_opr"] = max(previous_oprs[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_high_auto_opr"] = max(previous_auto_oprs[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_high_tele_opr"] = max(previous_tele_oprs[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_high_end_opr"] = max(previous_end_oprs[red_team_2])

				ml_all_matches_df.loc[i, "red_team_2_high_ccwm"] = max(previous_ccwms[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_high_auto_ccwm"] = max(previous_auto_ccwms[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_high_tele_ccwm"] = max(previous_tele_ccwms[red_team_2])
				# ml_all_matches_df.loc[i, "red_team_2_high_end_ccwm"] = max(previous_end_ccwms[red_team_2])

			if team_comps_played[blue_team_1] != 0:
				ml_all_matches_df.loc[i, "blue_team_1_opr"] = oprArray[teams_in_events[eventKey].index(blue_team_1)]
				# ml_all_matches_df.loc[i, "blue_team_1_auto_opr"] = autoOprArray[teams_in_events[eventKey].index[blue_team_1]]
				# ml_all_matches_df.loc[i, "blue_team_1_tele_opr"] = teleOprArray[teams_in_events[eventKey].index[blue_team_1]]
				# ml_all_matches_df.loc[i, "blue_team_1_end_opr"] = endOprArray[teams_in_events[eventKey].index[blue_team_1]]

				ml_all_matches_df.loc[i, "blue_team_1_ccwm"] = ccwmArray[teams_in_events[eventKey].index(blue_team_1)]
				# ml_all_matches_df.loc[i, "blue_team_1_auto_ccwm"] = autoCcwmArray[teams_in_events[eventKey].index[blue_team_1]]
				# ml_all_matches_df.loc[i, "blue_team_1_tele_ccwm"] = teleCcwmArray[teams_in_events[eventKey].index[blue_team_1]]
				# ml_all_matches_df.loc[i, "blue_team_1_end_ccwm"] = endCcwmArray[teams_in_events[eventKey].index[blue_team_1]]

				ml_all_matches_df.loc[i, "blue_team_1_avg_opr"] = statistics.mean(previous_oprs[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_avg_auto_opr"] = statistics.mean(previous_auto_oprs[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_avg_tele_opr"] = statistics.mean(previous_tele_oprs[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_avg_end_opr"] = statistics.mean(previous_end_oprs[blue_team_1])

				ml_all_matches_df.loc[i, "blue_team_1_avg_ccwm"] = statistics.mean(previous_ccwms[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_avg_auto_ccwm"] = statistics.mean(previous_auto_ccwms[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_avg_tele_ccwm"] = statistics.mean(previous_tele_ccwms[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_avg_end_ccwm"] = statistics.mean(previous_end_ccwms[blue_team_1])

				ml_all_matches_df.loc[i, "blue_team_1_high_opr"] = max(previous_oprs[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_high_auto_opr"] = max(previous_auto_oprs[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_high_tele_opr"] = max(previous_tele_oprs[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_high_end_opr"] = max(previous_end_oprs[blue_team_1])

				ml_all_matches_df.loc[i, "blue_team_1_high_ccwm"] = max(previous_ccwms[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_high_auto_ccwm"] = max(previous_auto_ccwms[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_high_tele_ccwm"] = max(previous_tele_ccwms[blue_team_1])
				# ml_all_matches_df.loc[i, "blue_team_1_high_end_ccwm"] = max(previous_end_ccwms[blue_team_1])

			if team_comps_played[blue_team_2] != 0:
				ml_all_matches_df.loc[i, "blue_team_2_opr"] = oprArray[teams_in_events[eventKey].index(blue_team_2)]
				# ml_all_matches_df.loc[i, "blue_team_2_auto_opr"] = autoOprArray[teams_in_events[eventKey].index[blue_team_2]]
				# ml_all_matches_df.loc[i, "blue_team_2_tele_opr"] = teleOprArray[teams_in_events[eventKey].index[blue_team_2]]
				# ml_all_matches_df.loc[i, "blue_team_2_end_opr"] = endOprArray[teams_in_events[eventKey].index[blue_team_2]]

				ml_all_matches_df.loc[i, "blue_team_2_ccwm"] = ccwmArray[teams_in_events[eventKey].index(blue_team_2)]
				# ml_all_matches_df.loc[i, "blue_team_2_auto_ccwm"] = autoCcwmArray[teams_in_events[eventKey].index[blue_team_2]]
				# ml_all_matches_df.loc[i, "blue_team_2_tele_ccwm"] = teleCcwmArray[teams_in_events[eventKey].index[blue_team_2]]
				# ml_all_matches_df.loc[i, "blue_team_2_end_ccwm"] = endCcwmArray[teams_in_events[eventKey].index[blue_team_2]]

				ml_all_matches_df.loc[i, "blue_team_2_avg_opr"] = statistics.mean(previous_oprs[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_avg_auto_opr"] = statistics.mean(previous_auto_oprs[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_avg_tele_opr"] = statistics.mean(previous_tele_oprs[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_avg_end_opr"] = statistics.mean(previous_end_oprs[blue_team_2])

				ml_all_matches_df.loc[i, "blue_team_2_avg_ccwm"] = statistics.mean(previous_ccwms[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_avg_auto_ccwm"] = statistics.mean(previous_auto_ccwms[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_avg_tele_ccwm"] = statistics.mean(previous_tele_ccwms[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_avg_end_ccwm"] = statistics.mean(previous_end_ccwms[blue_team_2])

				ml_all_matches_df.loc[i, "blue_team_2_high_opr"] = max(previous_oprs[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_high_auto_opr"] = max(previous_auto_oprs[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_high_tele_opr"] = max(previous_tele_oprs[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_high_end_opr"] = max(previous_end_oprs[blue_team_2])

				ml_all_matches_df.loc[i, "blue_team_2_high_ccwm"] = max(previous_ccwms[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_high_auto_ccwm"] = max(previous_auto_ccwms[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_high_tele_ccwm"] = max(previous_tele_ccwms[blue_team_2])
				# ml_all_matches_df.loc[i, "blue_team_2_high_end_ccwm"] = max(previous_end_ccwms[blue_team_2])

		playersListRed = playersListRedTEMPLATE.copy()
		playersListBlue = playersListBlueTEMPLATE.copy()
		playersListRed[teams_in_events[eventKey].index(red_team_1)] = 1
		playersListRed[teams_in_events[eventKey].index(red_team_2)] = 1
		playersListBlue[teams_in_events[eventKey].index(blue_team_1)] = 1
		playersListBlue[teams_in_events[eventKey].index(blue_team_2)] = 1

	if is_new_comp:
		teamsArray = np.array(playersListRed)
		teamsArray = np.vstack([teamsArray, playersListBlue])

		scoresArray = np.array(red_score)
		scoresArray = np.vstack([scoresArray, blue_score])

		# autoScoresArray = np.array(ml_all_matches_df.loc[i, "red_auto_score"])
		# autoScoresArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "blue_auto_score"]])

		# teleScoresArray = np.array(red_tele_score)
		# teleScoresArray = np.vstack([scoresArray, blue_tele_score])

		# endScoresArray = np.array(red_end_score)
		# endScoresArray = np.vstack([scoresArray, blue_end_score])

		marginsArray = np.array(ml_all_matches_df.loc[i, "score_diff_red"])
		marginsArray = np.vstack([marginsArray, ml_all_matches_df.loc[i, "score_diff_blue"]])

		# autoMarginsArray = np.array(ml_all_matches_df.loc[i, "score_diff_red_auto"])
		# autoMarginsArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "score_diff_blue_auto"]])

		# teleMarginsArray = np.array(ml_all_matches_df.loc[i, "score_diff_red_tele"])
		# teleMarginsArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "score_diff_blue_tele"]])

		# endMarginsArray = np.array(ml_all_matches_df.loc[i, "score_diff_red_end"])
		# endMarginsArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "score_diff_blue_end"]])

	if not is_new_comp:
		teamsArray = np.vstack([teamsArray, playersListRed])
		teamsArray = np.vstack([teamsArray, playersListBlue])

		scoresArray = np.vstack([scoresArray, red_score])
		scoresArray = np.vstack([scoresArray, blue_score])

		# autoScoresArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "red_auto_score"]])
		# autoScoresArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "blue_auto_score"]])

		# teleScoresArray = np.vstack([scoresArray, red_tele_score])
		# teleScoresArray = np.vstack([scoresArray, blue_tele_score])

		# endScoresArray = np.vstack([scoresArray, red_end_score])
		# endScoresArray = np.vstack([scoresArray, blue_end_score])

		marginsArray = np.vstack([marginsArray, ml_all_matches_df.loc[i, "score_diff_red"]])
		marginsArray = np.vstack([marginsArray, ml_all_matches_df.loc[i, "score_diff_blue"]])

		# autoMarginsArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "score_diff_red_auto"]])
		# autoMarginsArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "score_diff_blue_auto"]])

		# teleMarginsArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "score_diff_red_tele"]])
		# teleMarginsArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "score_diff_blue_tele"]])

		# endMarginsArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "score_diff_red_end"]])
		# endMarginsArray = np.vstack([scoresArray, ml_all_matches_df.loc[i, "score_diff_blue_end"]])

	

	previous_scores[red_team_1].append(red_score)
	previous_scores[red_team_2].append(red_score)
	previous_scores[blue_team_1].append(blue_score)
	previous_scores[blue_team_2].append(blue_score)

	# previous_auto_scores[red_team_1].append(red_auto_score)
	# previous_auto_scores[red_team_2].append(red_auto_score)
	# previous_auto_scores[blue_team_1].append(blue_auto_score)
	# previous_auto_scores[blue_team_2].append(blue_auto_score)

	# previous_tele_scores[red_team_1].append(red_tele_score)
	# previous_tele_scores[red_team_2].append(red_tele_score)
	# previous_tele_scores[blue_team_1].append(blue_tele_score)
	# previous_tele_scores[blue_team_2].append(blue_tele_score)

	# previous_end_scores[red_team_1].append(red_end_score)
	# previous_end_scores[red_team_2].append(red_end_score)
	# previous_end_scores[blue_team_1].append(blue_end_score)
	# previous_end_scores[blue_team_2].append(blue_end_score)

	team_games_played[red_team_1] = team_games_played[red_team_1] + 1
	team_games_played[red_team_2] = team_games_played[red_team_2] + 1
	team_games_played[blue_team_1] = team_games_played[blue_team_1] + 1
	team_games_played[blue_team_2] = team_games_played[blue_team_2] + 1

	team_games_played_per_comp[red_team_1] = team_games_played_per_comp[red_team_1] + 1
	team_games_played_per_comp[red_team_2] = team_games_played_per_comp[red_team_2] + 1
	team_games_played_per_comp[blue_team_1] = team_games_played_per_comp[blue_team_1] + 1
	team_games_played_per_comp[blue_team_2] = team_games_played_per_comp[blue_team_2] + 1

	previous_comp = eventKey

	if i % 1000 == 0:
		print(i)


teams_info_df = pd.DataFrame()

for i in range(len(teamsList)):
	teamNum = teamsList[i]
	teams_info_df.loc[i, "team_num"] = teamNum
	teams_info_df.loc[i, "latest_opr"] = previous_oprs[teamNum][len(previous_oprs[teamNum]) - 1]
	teams_info_df.loc[i, "avg_opr"] = statistics.mean(previous_oprs[teamNum])
	teams_info_df.loc[i, "high_opr"] = max(previous_oprs[teamNum])
	teams_info_df.loc[i, "latest_ccwm"] = previous_ccwms[teamNum][len(previous_ccwms[teamNum]) - 1]
	teams_info_df.loc[i, "avg_ccwm"] = statistics.mean(previous_ccwms[teamNum])
	teams_info_df.loc[i, "high_ccwm"] = max(previous_ccwms[teamNum])
	teams_info_df.loc[i, "avg_score"] = statistics.mean(previous_scores[teamNum])
	teams_info_df.loc[i, "high_score"] = max(previous_scores[teamNum])

try:
	ml_all_matches_df = ml_all_matches_df.drop(columns=["level_0"])
except:
	pass


teams_info_df.to_sql("teams_info_1920", con=conn, if_exists="replace")


#MOVING ON TO MACHINE LEARNING MATH PART
print("MOVING ON TO MACHINE LEARNING MATH")

for i in range(len(ml_all_matches_df)):
	ml_all_matches_df.loc[i, "red_team_avg_sum"] = ml_all_matches_df.loc[i, "red_team_1_avg_score"] + ml_all_matches_df.loc[i, "red_team_2_avg_score"]
	ml_all_matches_df.loc[i, "blue_team_avg_sum"] = ml_all_matches_df.loc[i, "blue_team_1_avg_score"] + ml_all_matches_df.loc[i, "blue_team_2_avg_score"]

	ml_all_matches_df.loc[i, "red_team_high_score_sum"] = ml_all_matches_df.loc[i, "red_team_1_high_score"] + ml_all_matches_df.loc[i, "red_team_2_high_score"]
	ml_all_matches_df.loc[i, "blue_team_high_score_sum"] = ml_all_matches_df.loc[i, "blue_team_1_high_score"] + ml_all_matches_df.loc[i, "blue_team_2_high_score"]

	ml_all_matches_df.loc[i, "red_team_opr_sum"] = ml_all_matches_df.loc[i, "red_team_1_opr"] + ml_all_matches_df.loc[i, "red_team_2_opr"]
	ml_all_matches_df.loc[i, "blue_team_opr_sum"] = ml_all_matches_df.loc[i, "blue_team_1_opr"] + ml_all_matches_df.loc[i, "blue_team_2_opr"]

	ml_all_matches_df.loc[i, "red_team_ccwm_sum"] = ml_all_matches_df.loc[i, "red_team_1_ccwm"] + ml_all_matches_df.loc[i, "red_team_2_ccwm"]
	ml_all_matches_df.loc[i, "blue_team_ccwm_sum"] = ml_all_matches_df.loc[i, "blue_team_1_ccwm"] + ml_all_matches_df.loc[i, "blue_team_2_ccwm"]

	ml_all_matches_df.loc[i, "red_team_avg_opr_sum"] = ml_all_matches_df.loc[i, "red_team_1_avg_opr"] + ml_all_matches_df.loc[i, "red_team_2_avg_opr"]
	ml_all_matches_df.loc[i, "blue_team_avg_opr_sum"] = ml_all_matches_df.loc[i, "blue_team_1_avg_opr"] + ml_all_matches_df.loc[i, "blue_team_2_avg_opr"]

	ml_all_matches_df.loc[i, "red_team_highest_opr_sum"] = ml_all_matches_df.loc[i, "red_team_1_high_opr"] + ml_all_matches_df.loc[i, "red_team_2_high_opr"]
	ml_all_matches_df.loc[i, "blue_team_highest_opr_sum"] = ml_all_matches_df.loc[i, "blue_team_1_high_opr"] + ml_all_matches_df.loc[i, "blue_team_2_high_opr"]

	ml_all_matches_df.loc[i, "red_team_avg_ccwm_sum"] = ml_all_matches_df.loc[i, "red_team_1_avg_ccwm"] + ml_all_matches_df.loc[i, "red_team_2_avg_ccwm"]
	ml_all_matches_df.loc[i, "blue_team_avg_ccwm_sum"] = ml_all_matches_df.loc[i, "blue_team_1_avg_ccwm"] + ml_all_matches_df.loc[i, "blue_team_2_avg_ccwm"]

	ml_all_matches_df.loc[i, "red_team_high_ccwm_sum"] = ml_all_matches_df.loc[i, "red_team_1_high_ccwm"] + ml_all_matches_df.loc[i, "red_team_2_high_ccwm"]
	ml_all_matches_df.loc[i, "blue_team_high_ccwm_sum"] = ml_all_matches_df.loc[i, "blue_team_1_high_ccwm"] + ml_all_matches_df.loc[i, "blue_team_2_high_ccwm"]

	ml_all_matches_df.loc[i, "avg_sum_diff"] = ml_all_matches_df.loc[i, "red_team_avg_sum"] - ml_all_matches_df.loc[i, "blue_team_avg_sum"]

	ml_all_matches_df.loc[i, "high_score_sum_diff"] = ml_all_matches_df.loc[i, "red_team_high_score_sum"] - ml_all_matches_df.loc[i, "blue_team_high_score_sum"]

	ml_all_matches_df.loc[i, "opr_sum_diff"] = ml_all_matches_df.loc[i, "red_team_opr_sum"] - ml_all_matches_df.loc[i, "blue_team_opr_sum"]

	ml_all_matches_df.loc[i, "ccwm_sum_diff"] = ml_all_matches_df.loc[i, "red_team_ccwm_sum"] - ml_all_matches_df.loc[i, "blue_team_ccwm_sum"]

	ml_all_matches_df.loc[i, "avg_opr_sum_diff"] = ml_all_matches_df.loc[i, "red_team_avg_opr_sum"] - ml_all_matches_df.loc[i, "blue_team_avg_opr_sum"]

	ml_all_matches_df.loc[i, "highest_opr_sum_diff"] = ml_all_matches_df.loc[i, "red_team_highest_opr_sum"] - ml_all_matches_df.loc[i, "blue_team_highest_opr_sum"]

	ml_all_matches_df.loc[i, "avg_ccwm_sum_diff"] = ml_all_matches_df.loc[i, "red_team_avg_ccwm_sum"] - ml_all_matches_df.loc[i, "blue_team_avg_ccwm_sum"]

	ml_all_matches_df.loc[i, "high_ccwm_sum_diff"] = ml_all_matches_df.loc[i, "red_team_high_ccwm_sum"] - ml_all_matches_df.loc[i, "blue_team_high_ccwm_sum"]

	if i % 1000 == 0:
		print(i)

ml_all_matches_df = ml_all_matches_df.drop(columns=["match_start_time"])
ml_all_matches_df.to_sql("matches_math_1920", con=conn, if_exists="replace")

print(ml_all_matches_df.isnull().sum())

ml_all_matches_df = ml_all_matches_df.dropna()
ml_all_matches_df = ml_all_matches_df.reset_index()
ml_all_matches_df = ml_all_matches_df.drop(columns=["index"])

ml_all_matches_df = ml_all_matches_df[["match_winner", "red_score", "blue_score", "red_team_avg_sum", "blue_team_avg_sum", "red_team_high_score_sum", "blue_team_high_score_sum", "red_team_opr_sum", "blue_team_opr_sum", "red_team_ccwm_sum", "blue_team_ccwm_sum", "red_team_avg_opr_sum", "blue_team_avg_opr_sum", "red_team_avg_ccwm_sum", "blue_team_avg_ccwm_sum", "red_team_highest_opr_sum", "blue_team_highest_opr_sum", "red_team_high_ccwm_sum", "blue_team_high_ccwm_sum", "avg_sum_diff", "high_score_sum_diff", "avg_opr_sum_diff", "avg_ccwm_sum_diff", "highest_opr_sum_diff", "high_ccwm_sum_diff"]]

ml_all_matches_df.to_sql("matches_ml_1920", con=conn, if_exists="replace")

