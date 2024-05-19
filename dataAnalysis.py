from scipy.stats import ttest_ind
import matplotlib.pyplot as plt 
import numpy
import json
from dbMethods import *


def ttestLengthAndEmotion(BUFFER_BEFORE_CRASH, BUFFER_AFTER_CRASH, returning = "emotion", debug = False):
	
	numSignificant = 0

	# Load Race Data
	with open('race_data.json', encoding='utf-8') as f:
		raceData = json.load(f)

	# All Red Flags For The 2023 Season
	redFlags2023 = {
		"2023-australian-grand-prix": [15, 60+40, 60+60+1],
		"2023-dutch-grand-prix": [60+33],
		"2023-mexican-grand-prix": [50],
		"2023-brazilian-grand-prix": [5]
	}
	
	overallPostLengths = {
		"crash": [],
		"no crash": []
	}
	overallEmotionScore = {
		"crash": [],
		"no crash": []
	}

	for raceWithIncident, timestamps in redFlags2023.items():
		
		if debug:
			print(raceWithIncident)

		# Convert to UTC Timestamp
		# And Add A Buffer Beforehand
		timestamps = list(map(lambda x: (x*60)+raceData[raceWithIncident]["timestamps"]["gp_start"]-BUFFER_BEFORE_CRASH, timestamps))

		# Prepare Dictionaries And Lists
		postLengths = {
			"crash": [],
			"no crash": []
		}
		emotionScore = {
			"crash": [],
			"no crash": []
		}

		# Get Data
		c.execute(
			'SELECT * FROM "' + raceData[raceWithIncident]["table_name"] + '" WHERE timestamp > ? AND timestamp < ?',
			(raceData[raceWithIncident]["timestamps"]["gp_start"], raceData[raceWithIncident]["timestamps"]["gp_end"])
		)
		data = c.fetchall()
		if debug:
			print(f"{len(data)} posts during race")

		for postNum, row in enumerate(data):
			
			# Check if Timestamp Near A Crash
			postTime = row[1]
			postAfterCrash = False

			for crashTime in timestamps:
				if(postTime > crashTime & postTime-crashTime < BUFFER_AFTER_CRASH):
					postAfterCrash = True

			if(postAfterCrash):
				category = "crash"
			else:
				category = "no crash"

			postLengths[category].append(row[6])
			emotionScore[category].append(row[7])
			
			overallEmotionScore[category].append(row[7])
			overallPostLengths[category].append(row[6])

		if debug:
			print("Post Length: " + str(len(postLengths["crash"])) + " crash, " + str(len(postLengths["no crash"])) + " no crash")
			print("Emotion Score: " + str(len(emotionScore["crash"])) + " crash, " + str(len(emotionScore["no crash"])) + " no crash")
			print("Mean Post Lengths:")
			print(f"\t- Crash: {round(numpy.array(postLengths['crash']).mean(),2)}")
			print(f"\t- No Crash: {round(numpy.array(postLengths['no crash']).mean(),2)}")
			print("Mean Emotion Score:")
			print(f"\t- Crash: {round(numpy.array(emotionScore['crash']).mean(),2)}")
			print(f"\t- No Crash: {round(numpy.array(emotionScore['no crash']).mean(),2)}")
		
		"""
		# Perform two-sample t-test
		if debug:
			print("Testing for Post Length")
		t_statistic, p_value = ttest_ind(postLengths["crash"], postLengths["no crash"])
		if(p_value <= 0.05):
			numSignificant+=1

		# Output the results
		if debug:
			print(f"\tt-statistic: {round(t_statistic,2)}")
			print(f"\tP-value: {round(p_value,3)}")

		# Perform two-sample t-test
		if debug:
			print("Testing for Emotion Score")
		t_statistic, p_value = ttest_ind(emotionScore["crash"], emotionScore["no crash"])
		if(p_value <= 0.05):
			numSignificant+=1

		# Output the results
		if debug:
			print(f"\tt-statistic: {round(t_statistic,2)}")
			print(f"\tP-value: {round(p_value,3)}")
		"""

		# Perform two-sample t-test
		"""if debug:
			print("Testing for Absolute Emotion Score")
		t_statistic, p_value = ttest_ind(
							[abs(ele) for ele in emotionScore["crash"]],
							[abs(ele) for ele in emotionScore["no crash"]]
		)
		if(p_value <= 0.05):
			numSignificant+=1

		# Output the results
		if debug:
			print(f"\tt-statistic: {round(t_statistic,2)}")
			print(f"\tP-value: {round(p_value,3)}")
			print("")"""
	
	if debug:
		print("=============")
		print("OVERALL STATS")
		print("=============")
		
		print("Mean Post Lengths:")
		print(f"\t- Crash: {round(numpy.array(overallPostLengths['crash']).mean(),2)}")
		print(f"\t- No Crash: {round(numpy.array(overallPostLengths['no crash']).mean(),2)}")
		print("Mean Emotion Score:")
		print(f"\t- Crash: {round(numpy.array(overallEmotionScore['crash']).mean(),2)}")
		print(f"\t- No Crash: {round(numpy.array(overallEmotionScore['no crash']).mean(),2)}")
		print("Mean Absolute Emotion Score:")
		print(f"\t- Crash: {round(numpy.array([abs(ele) for ele in overallEmotionScore['crash']]).mean(),2)}")
		print(f"\t- No Crash: {round(numpy.array([abs(ele) for ele in overallEmotionScore['no crash']]).mean(),2)}")
	
	# Perform two-sample t-test
	if debug:
		print("Testing for Post Length")
	t_statistic, p_value = ttest_ind(overallPostLengths["crash"], overallPostLengths["no crash"])
	postLengthSignificance = p_value
	if(p_value <= 0.05):
		numSignificant+=1

	# Output the results
	if debug:
		print(f"\tt-statistic: {round(t_statistic,2)}")
		print(f"\tP-value: {round(p_value,3)}")

		
	# Perform two-sample t-test
	if debug:
		print("Testing for Emotion Score")
	t_statistic, p_value = ttest_ind(overallEmotionScore["crash"], overallEmotionScore["no crash"])
	#emotionSignificance = p_value
	if(p_value <= 0.05):
		numSignificant+=1

	# Output the results
	if debug:
		print(f"\tt-statistic: {round(t_statistic,2)}")
		print(f"\tP-value: {round(p_value,3)}")
		
	# Perform two-sample t-test
	if debug:
		print("Testing for AbsoluteEmotion Score")
	t_statistic, p_value = ttest_ind(
								[abs(ele) for ele in overallEmotionScore["crash"]],
								[abs(ele) for ele in overallEmotionScore["no crash"]]
	)
	emotionSignificance = p_value
	
	if(p_value <= 0.05):
		numSignificant+=1

	# Output the results
	if debug:
		print(f"\tt-statistic: {round(t_statistic,2)}")
		print(f"\tP-value: {round(p_value,3)}")
	
	if(returning == "emotion"):
		return emotionSignificance
	elif(returning == "length"):
		return postLengthSignificance
	else:
		print("VALUE ERROR")
		raise ValueError
	
	#return numSignificant
	#return emotionSignificance
	#return postLengthSignificance

# Chart P-Value Over Time Post-Crash
def graphPValuePostCrash(
	timeBeforeCrash = 0,
	timeAfterCrash = 60 * 7,
	returning = "emotion",
	step = 1,
	caption = ""
):
	buffer_list = list(range(0,timeAfterCrash,step))
	significant_list = []

	for currentBuffer in buffer_list:
		significant_list.append(ttestLengthAndEmotion(0, currentBuffer, returning = returning))
		print(f"{currentBuffer}/{max(buffer_list)}",end="\r")
	
	plt.figure(figsize=(12,8))
	plt.plot(buffer_list, significant_list)
	plt.title(caption)
	plt.xlabel("Time After Crash (seconds)")
	plt.show()