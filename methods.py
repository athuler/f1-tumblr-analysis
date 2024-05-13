import sqlite3
import re
import requests
import json
import sys
from datetime import datetime, timedelta
from urllib.parse import urlparse
from urllib.parse import parse_qs
from time import sleep
import matplotlib.pyplot as plt
import matplotlib.dates as md
import numpy as np
from scipy.signal import find_peaks_cwt
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer

# Download necessary NLTK resources
nltk.download([
	"names",
	"stopwords",
	"state_union",
	"twitter_samples",
	"movie_reviews",
	"averaged_perceptron_tagger",
	"vader_lexicon",
	"punkt",
])

# Load API Key
global API_KEY
API_KEY = json.loads(open("secret.json").read())["api_key"]

# Load Race Data
global GP_DATA
GP_DATA = json.loads(open("race_data.json").read())

# Connect to DB
global conn
global c
conn = sqlite3.connect('f1_tumblr_analysis.db')
c = conn.cursor()


# Define Additional Tags
additionalTags = [
	"formula 1",
	"f1",
	"formula1",
	"f1blr"
]



def getPostsToTimestamp(
	tableName,
	tag = None,
	timestamp = "",
	replace = False,
	debug = False
):
	'''
	Gets the 20 most recent posts as of the given timestamp
	and saves them to the database
	--
	Input: race (mandatory), tag, timestamp
	Output: The earliest timestamp gathered
	'''
	
	# Set tag if none is provided
	if tag == None:
		tag = tableName
	
	
		
	# Set Request URL
	url = "https://api.tumblr.com/v2/tagged?filter=raw&api_key="+API_KEY+"&tag="+tag
	
	# Ignore timestamp is none is provided
	if timestamp != "":
		url += "&before="+str(timestamp)
	
	
	# Get Posts
	fetching = True
	while(fetching):
		try:
			APIResponse = requests.get(url)
			fetching = False
		except Exception as e:
			if debug:
				print(e)
			print("Connection Reset. Reconnecting...")
			fetching = True
	
	# Handle Response
	APIResponse = APIResponse.json()
	
	# Check Status
	if(APIResponse["meta"]["status"] != 200):
		print("ERROR IN REQUEST")
		print(json.dumps(APIResponse, indent=4))
		sys.exit("Status code of response was not 200")
	
	
	# Compute and print statistics about current batch of posts
	num_posts = len(APIResponse["response"])
	
	if num_posts == 0:
		return None
	
	first_timestamp = APIResponse["response"][0]["timestamp"]
	last_timestamp = APIResponse["response"][-1]["timestamp"]
	
	if(first_timestamp == last_timestamp):
		last_timestamp -= 1
	
	if debug:
		print(
			"\n", last_timestamp,"->",first_timestamp,
			"(",round((first_timestamp-last_timestamp)/60,1), "min |",
			round(num_posts/(first_timestamp-last_timestamp)*60,1), "posts/min)"
		)
	
	
	# Iterate through each post
	for post in APIResponse["response"]:
		
		if "trail" not in post:
			print("Skipping post without trail")
			continue
		
		# Ignore Empty Posts
		if post['trail'] == []:
			print("Skipping empty post")
			continue
		
		if debug:
			#print(json.dumps(post, indent=4))
			...
		
		# Save Post Data
		post_content_raw = post['trail'][0]["content_raw"]
		#post_content_raw = post['body']
		post_url = post["short_url"]
		post_author = post["blog_name"]
		post_timestamp = post["timestamp"]
		post_id = post["id"]
		post_tags = post["tags"]
		
		if debug:
			print(post_timestamp,"\t", post_author,"\t", post_url)
		
		
		
		# Check If Post Already in DB
		c.execute('select * from "' + tableName + '" where id=?', (post_id,))
		
		if c.fetchone() != None:
			# Post already in DB
			
			# Delete records if replacing them
			if not replace:
				continue
			c.execute('delete from "' + tableName + '" where id=?', (post_id,))
		
		
		# Add post to DB
		c.execute(
			'insert into "' + tableName + '" values (?,?,?,?,?,?,0,0)',
			(post_id, post_timestamp, post_url, post_author, post_content_raw, str(post_tags))
		)
	
		conn.commit()
	
	if debug:
		#print(json.dumps(APIResponse, indent=4))
		...
	
	
	return(last_timestamp)




def getPostsForGP(
	race,
	delay = 300,
	replace = True,
	startAtTag = None,
	debug = False
):
	'''
	Fetches all posts for a GP
	--
	Input: GP name
	Output: Number of Posts
	'''
	
	# Get GP Start & End Time
	startTime = GP_DATA[race]["timestamps"]["fp1_start"] - 60 * 60 * 2
	endTime = GP_DATA[race]["timestamps"]["gp_end"] + 60 * 60 * 2
	tableName = GP_DATA[race]["table_name"]
	
	
	postCount = 0
	
	
	
	# Build Tag List
	tags = additionalTags.copy()
	for additionalTag in GP_DATA[race]["gp_tags"]:
		tags.append(additionalTag)
		
	# Start At Designated Tag
	if(startAtTag != None):
		while(len(tags) > 0 and tags[0] != startAtTag):
			print("Skipping tag", tags[0])
			del tags[0]
	
	
	for tag in tags:
		nextTimeStamp = endTime
		print("Current tag:", tag)
		
		c.execute('select COUNT(*) as post_count from "' + tableName + '"')
		postsBeforeCurrentTag = c.fetchone()[0]
		
		while (nextTimeStamp >= startTime):

			nextTimeStamp = getPostsToTimestamp(
									tableName = tableName,
									tag = tag,
									timestamp = nextTimeStamp,
									replace = replace,
									debug = debug
							)
			if(nextTimeStamp == None):
				print("No Posts")
				postCount = 0
				break
			
			c.execute('select COUNT(*) as post_count from "' + tableName + '"')
			postCount = c.fetchone()[0]
			print(
				str(round((endTime-nextTimeStamp)/(endTime-startTime)*100,2)) + \
				"% (" + str(postCount) +\
				" total posts for gp)",
				end="\r"
			)
			sleep(delay / 1000)
		
		#print(str(postCount - postsBeforeCurrentTag) + " posts")
		
		print("____________________________________________", end="\r")
		
	return(postCount)




def raceSummary(
	race,
	endTime = 1701010800,
	startTime = 1701003600,
	resolution = 5
):
	
	# Get Data
	c.execute('select * from "' + race + '" WHERE "timestamp" >= ? AND "timestamp" <= ?',(startTime, endTime))
	data = c.fetchall()
	timestamps = []
	for row in data:
		timestamps.append(row[1])
   
	
	
	# Plot Time Chart
	dates=[datetime.fromtimestamp(ts) for ts in timestamps]
	datenums=md.date2num(dates)
	xfmt = md.DateFormatter('%H:%M')
	plt.figure(figsize=(10,6))
	plt.title(race.title() + " (" + str(resolution) +" min resolution)")
	plt.ylabel("# of Tumblr Posts")
	ax=plt.gca()
	ax.xaxis.set_major_formatter(xfmt)
	plt.hist(datenums, bins=int(120/resolution))
	plt.show()
	
	
	# Per-minute Frequency
	wordFreqMinute = np.histogram(
		timestamps,
		bins=range(
			min(timestamps)-min(timestamps)%60, # Get start of the minute
			max(timestamps) + 60,
			60
		)
	)
	print(wordFreqMinute)



def loadSeasonFromWeb(
	season = 2023,
	debug = False
):
	"""
	Given a season, gets the data for the races and loads them in the JSON file
	"""
	
	# Only Accept Seasons Between 2018 and 2024
	if(season < 2018 or season > 2024):
		return None
	
	# Get Race Data For Season
	url = "https://github.com/sportstimes/f1/raw/main/_db/f1/"+str(season)+".json"
	response = requests.get(url)
	roughRaceData = response.json()["races"]
	
	
	
	
	newRaceData = {}
	
	# Load Each Race
	for race in roughRaceData:
		
		slugWithYear = str(season) + "-" + race["slug"]
		
		# Save Current Race
		newRaceData[slugWithYear] = {
			"year" : season,
			"round" : race["round"],
			"name" : race["name"],
			"location" : race["location"],
			"emoji" : "",
			"table_name" : slugWithYear,
			"timestamps" : {},
			"gp_tags" : [
				race["name"].lower() + " gp " + str(season),
				race["name"].lower() + " gp",
				race["location"].lower() + " " + str(season),
				race["location"].lower() + " gp " + str(season)
			]
		}
		
		# Add US GP Tag Where Appropriate
		if(race["name"].lower() == "united states"):
			newRaceData[slugWithYear]["gp_tags"].append("us gp " + str(season))
			newRaceData[slugWithYear]["gp_tags"].append("us gp")
		
		if debug:
			print("Race #" + str(race["round"]))
			print(race["name"] + " / " + race["location"])
			print(race["slug"])
		
		# Load Each Session
		for session, startTimeOg in race["sessions"].items():
			
			# Determine Session Length
			if("gp" in session):
				sessionLength = 120
			else:
				sessionLength = 60
			
			
			# Convert to DateTime
			startTime = datetime.fromisoformat(startTimeOg.replace("Z","+00:00"))
			endTime = startTime + timedelta(minutes=sessionLength)
			
			if debug:
				print(session, int(startTime.timestamp()))
			
			# Add Session To Race
			newRaceData[slugWithYear]["timestamps"][session + "_start"] = int(startTime.timestamp())
			newRaceData[slugWithYear]["timestamps"][session + "_end"] = int(endTime.timestamp())
		
		
		# Check if Table Exists
		c.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='"+slugWithYear+"';")
		
		# Create Table If It Doesn't Exist
		if c.fetchone() == None:
			c.execute("CREATE TABLE '"+slugWithYear+"' ('id'	INTEGER UNIQUE,	\"timestamp\"	INTEGER,\"url\"	TEXT,\"author\"	TEXT,\"content\"	TEXT,\"tags\"	TEXT,\"postLength\"	INTEGER,\"emotionScore\"	REAL,PRIMARY KEY(\"id\"))")
		
		if debug:
			#print(json.dumps(race, indent=4))
			print("")
		
	
	# Load Current Race Data
	with open('race_data.json', encoding='utf-8') as f:
		raceData = json.load(f)
	
	# Preserve Existing Tags
	for currentRace in newRaceData.keys():
		if(currentRace not in raceData):
			continue
		
		for tag in raceData[currentRace]["gp_tags"]:
			if tag in newRaceData[currentRace]["gp_tags"]:
				continue
			newRaceData[currentRace]["gp_tags"].append(tag)
		
	# Remove Duplicate Tags
	for currentRace in newRaceData.keys():
		newRaceData[currentRace]["gp_tags"] = list(set(newRaceData[currentRace]["gp_tags"]))
	
	# Save JSON to file
	with open('race_data.json', 'w', encoding='utf-8') as f:
		json.dump(newRaceData, f, ensure_ascii=False, indent=4)
	
	return True
	
	
def getPostsForSeason(
	season = 2023,
	debug = False,
	startAtRace = 1,
	raceLimit = None,
	delay = 1000,
	replace = False
):
	
	# Load Race Data
	with open('race_data.json', encoding='utf-8') as f:
		raceData = json.load(f)
		
	i = 0
	currentRaceNum = 0
	started = False
	
	# Fetch Posts For Each Race
	for currentRace, currentRaceData in raceData.items():
		i += 1
		currentRaceNum += 1
		
		if(currentRaceNum < startAtRace and started == False):
			continue
		elif(started == False):
			currentRaceNum = 1
			started = True
		
		if(raceLimit != None and currentRaceNum > raceLimit):
			break
		
		# Only Consider Current Season
		if(currentRaceData["year"] != season):
			continue
		
		print("Fetching " + currentRace + " #" + str(i) + " Round " + str(currentRaceData["round"]) + " (" + str(currentRaceData["timestamps"]["fp1_start"]) + "-" + str(currentRaceData["timestamps"]["gp_end"]) + ")")
		
		# Fetch Post For Current Race
		numPosts = getPostsForGP(
			currentRace,
			debug = debug,
			replace = replace,
			delay = delay
		)
		
		print(numPosts,"posts\n")


CLEANR = re.compile('<.*?>') 

def cleanhtml(raw_html):
	cleantext = re.sub(CLEANR, '', raw_html)
	return cleantext.strip()
		
def get_emotion(text):
	# Tokenize the text
	tokens = word_tokenize(text.lower())

	# Remove stopwords
	stop_words = set(stopwords.words('english'))
	filtered_tokens = [word for word in tokens if word.isalnum() and word not in stop_words]

	# Join tokens back into a single string
	clean_text = ' '.join(filtered_tokens)

	# Analyze sentiment
	sid = SentimentIntensityAnalyzer()
	scores = sid.polarity_scores(clean_text)

	return scores
		
		
def computePostLengthAndEmotionForRace(
	race,
	debug = False
):
	print("Computing Post Length & Sentiment for " + str(race))
	
	# Load Current Race Data
	with open('race_data.json', encoding='utf-8') as f:
		raceData = json.load(f)
	tableName = raceData[race]["table_name"]
	
	# Check Table Formatting
	c.execute('PRAGMA table_info("' + tableName + '")')
	data = c.fetchall()
	columnList = []
	for row in data:
		columnList.append(row[1])
	
	if("postLength" not in columnList):
		c.execute('ALTER TABLE "' + tableName + '" ADD COLUMN postLength INTEGER;')
		conn.commit()
	
	if("emotionScore" not in columnList):
		c.execute('ALTER TABLE "' + tableName + '" ADD COLUMN emotionScore REAL;')
		conn.commit()
		
	
	# Get Data
	c.execute('SELECT * FROM "' + tableName + '"')
	data = c.fetchall()
	
	for postNum, row in enumerate(data):
		
		# Remove HTML Formatting
		cleanPostContent = cleanhtml(row[4])
		
		# Get Post Length
		postLength = len(cleanPostContent)
		
		# Get Post Emotion Score
		postEmotionScore = get_emotion(cleanPostContent)["compound"]
		
		# Add These To The Database
		c.execute(
			'UPDATE "' + tableName + '" SET postLength = ?, emotionScore = ? WHERE id = ?',
			(postLength, postEmotionScore, row[0])
		)
		
		print(str(round(100*postNum/len(data),2)) + "%", end="\r")
		
		conn.commit()
			
def computePostLengthAndEmotionForSeason(
	season = 2023,
	debug = False
):
	# Load Race Data
	with open('race_data.json', encoding='utf-8') as f:
		raceData = json.load(f)
	
	# Compute For Each Race
	for currentRace, currentRaceData in raceData.items():
		computePostLengthAndEmotionForRace(currentRace, debug = debug)