import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier, NearestNeighbors
from scipy.spatial import distance
from sklearn.metrics import accuracy_score, confusion_matrix
import sqlite3
from sqlite3 import Error

def pred(teams):
	conn = sqlite3.connect('data.db') #Connecting to database
	c = conn.cursor()

	inputList = teams.split("-")

	red_1 = int(inputList[0].replace("-", ""))
	red_2 = int(inputList[1].replace("-", ""))
	blue_1 = int(inputList[2].replace("-", ""))
	blue_2 = int(inputList[1].replace("-", ""))


	match_df = pd.read_sql_query("SELECT * FROM matches_ml_1920", conn)
	teams_info_df = pd.read_sql_query("SELECT * FROM teams_info_1920", conn)

	all_short_df = match_df.drop(columns=["red_score", "blue_score"])


	try:
		match_df = match_df.drop(columns=["level_0"])
	except:
		pass

	try:
		match_df = match_df.drop(columns=["index"])
	except:
		pass

	try:
		teams_info_df = teams_info_df.drop(columns=["level_0"])
	except:
		pass

	X = match_df.drop(columns=["match_winner", "red_score", "blue_score"])
	y = match_df["match_winner"]

	X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=1)

	knn = KNeighborsClassifier(n_neighbors=100, algorithm='auto')
	knn.fit(X_train, y_train)

	knn_pred = knn.predict(X_test)
	knn_accuracy = accuracy_score(y_test, knn_pred)

	neigh = NearestNeighbors(n_neighbors=100)
	neigh.fit(X, y)

	print(knn_accuracy)

	red_1_index = teams_info_df.index[teams_info_df["team_num"] == red_1][0]
	red_2_index = teams_info_df.index[teams_info_df["team_num"] == red_2][0]
	blue_1_index = teams_info_df.index[teams_info_df["team_num"] == blue_1][0]
	blue_2_index = teams_info_df.index[teams_info_df["team_num"] == blue_2][0]
	row_to_add = len(X)


	X.loc[row_to_add, "red_team_avg_sum"] = teams_info_df.loc[red_1_index, "avg_score"] + teams_info_df.loc[red_2_index, "avg_score"]
	X.loc[row_to_add, "blue_team_avg_sum"] = teams_info_df.loc[blue_1_index, "avg_score"] + teams_info_df.loc[blue_2_index, "avg_score"]

	X.loc[row_to_add, "red_team_high_score_sum"] = teams_info_df.loc[red_1_index, "high_score"] + teams_info_df.loc[red_2_index, "high_score"]
	X.loc[row_to_add, "blue_team_high_score_sum"] = teams_info_df.loc[blue_1_index, "high_score"] + teams_info_df.loc[blue_2_index, "high_score"]

	X.loc[row_to_add, "red_team_opr_sum"] = teams_info_df.loc[red_1_index, "latest_opr"] + teams_info_df.loc[red_2_index, "latest_opr"]
	X.loc[row_to_add, "blue_team_opr_sum"] = teams_info_df.loc[blue_1_index, "latest_opr"] + teams_info_df.loc[blue_2_index, "latest_opr"]

	X.loc[row_to_add, "red_team_ccwm_sum"] = teams_info_df.loc[red_1_index, "latest_ccwm"] + teams_info_df.loc[red_2_index, "latest_ccwm"]
	X.loc[row_to_add, "blue_team_ccwm_sum"] = teams_info_df.loc[blue_1_index, "latest_ccwm"] + teams_info_df.loc[blue_2_index, "latest_ccwm"]

	X.loc[row_to_add, "red_team_avg_opr_sum"] = teams_info_df.loc[red_1_index, "avg_opr"] + teams_info_df.loc[red_2_index, "avg_opr"]
	X.loc[row_to_add, "blue_team_avg_opr_sum"] = teams_info_df.loc[blue_1_index, "avg_opr"] + teams_info_df.loc[blue_2_index, "avg_opr"]

	X.loc[row_to_add, "red_team_highest_opr_sum"] = teams_info_df.loc[red_1_index, "high_opr"] + teams_info_df.loc[red_2_index, "high_opr"]
	X.loc[row_to_add, "blue_team_highest_opr_sum"] = teams_info_df.loc[blue_1_index, "high_opr"] + teams_info_df.loc[blue_2_index, "high_opr"]

	X.loc[row_to_add, "red_team_avg_ccwm_sum"] = teams_info_df.loc[red_1_index, "avg_ccwm"] + teams_info_df.loc[red_2_index, "avg_ccwm"]
	X.loc[row_to_add, "blue_team_avg_ccwm_sum"] = teams_info_df.loc[blue_1_index, "avg_ccwm"] + teams_info_df.loc[blue_2_index, "avg_ccwm"]

	X.loc[row_to_add, "red_team_high_ccwm_sum"] = teams_info_df.loc[red_1_index, "high_ccwm"] + teams_info_df.loc[red_2_index, "high_ccwm"]
	X.loc[row_to_add, "blue_team_high_ccwm_sum"] = teams_info_df.loc[blue_1_index, "high_ccwm"] + teams_info_df.loc[blue_2_index, "high_ccwm"]

	X.loc[row_to_add, "avg_sum_diff"] = X.loc[row_to_add, "red_team_avg_sum"] - X.loc[row_to_add, "blue_team_avg_sum"]

	X.loc[row_to_add, "high_score_sum_diff"] = X.loc[row_to_add, "red_team_high_score_sum"] - X.loc[row_to_add, "blue_team_high_score_sum"]

	# X.loc[row_to_add, "opr_sum_diff"] = X.loc[row_to_add, "red_team_opr_sum"] - X.loc[row_to_add, "blue_team_opr_sum"] #here

	# X.loc[row_to_add, "ccwm_sum_diff"] = X.loc[row_to_add, "red_team_ccwm_sum"] - X.loc[row_to_add, "blue_team_ccwm_sum"] #here

	X.loc[row_to_add, "avg_opr_sum_diff"] = X.loc[row_to_add, "red_team_avg_opr_sum"] - X.loc[row_to_add, "blue_team_avg_opr_sum"]

	X.loc[row_to_add, "highest_opr_sum_diff"] = X.loc[row_to_add, "red_team_highest_opr_sum"] - X.loc[row_to_add, "blue_team_highest_opr_sum"]

	X.loc[row_to_add, "avg_ccwm_sum_diff"] = X.loc[row_to_add, "red_team_avg_ccwm_sum"] - X.loc[row_to_add, "blue_team_avg_ccwm_sum"]

	X.loc[row_to_add, "high_ccwm_sum_diff"] = X.loc[row_to_add, "red_team_high_ccwm_sum"] - X.loc[row_to_add, "blue_team_high_ccwm_sum"]

	X = X.reset_index()
	X = X.drop(columns=["index"])

	row_to_test = row_to_add
	test_neighbor = X.iloc[row_to_test].to_numpy().reshape(1, len(X.columns))

	neighbors_list = neigh.kneighbors(test_neighbor)[1].tolist()[0]


	match_outcomes = []
	match_outcomes.append(0)
	match_outcomes.append(0)
	for i in neighbors_list:
		if all_short_df.loc[i, "match_winner"] == 0:
			match_outcomes[0] = match_outcomes[0] + 1
		else:
			match_outcomes[1] = match_outcomes[1] + 1


	return((match_outcomes[0]/(match_outcomes[0]+match_outcomes[1]))*100)


print(pred("4174-4174-4174-4174"))