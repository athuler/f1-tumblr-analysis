import sqlite3
import requests
import json
import datetime
from urllib.parse import urlparse
from urllib.parse import parse_qs
from time import sleep
import matplotlib.pyplot as plt
import matplotlib.dates as md
import numpy as np
from scipy.signal import find_peaks_cwt

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


def getPostsToTimestamp(race, tag = None, timestamp = "", replace = False, debug = False):
    '''
    Gets the 20 most recent posts as of the given timestamp
    and saves them to the database
    --
    Input: race (mandatory), tag, timestamp
    Output: The earliest timestamp gathered
    '''
    
    # Set tag if none is provided
    if tag == None:
        tag = race
    
        
    # Set Request URL
    url = "https://api.tumblr.com/v2/tagged?filter=raw&api_key="+API_KEY+"&tag="+tag
    
    # Ignore timestamp is none is provided
    if timestamp != "":
        url += "&before="+str(timestamp)
    
    
    # Get Posts
    APIResponse = requests.get(url)
    APIResponse = APIResponse.json()
    
    
    # Compute and print statistics about current batch of posts
    num_posts = len(APIResponse["response"])
    first_timestamp = APIResponse["response"][0]["timestamp"]
    last_timestamp = APIResponse["response"][-1]["timestamp"]
    if debug:
        print(
            first_timestamp,"->", last_timestamp,
            "(",round((first_timestamp-last_timestamp)/60,1), "min |",
            round(num_posts/(first_timestamp-last_timestamp)*60,1), "posts/min)\n"
        )
    
    
    # Iterate through each post
    for post in APIResponse["response"]:
        
        # Save Post Data
        post_content_raw = post['trail'][0]["content_raw"]
        post_url = post["post_url"]
        post_author = post["blog_name"]
        post_timestamp = post["timestamp"]
        post_id = post["id"]
        post_tags = post["tags"]
        
        if debug:
            print(post_timestamp,"\t", post_author,"\t", )
        
        # Check If Post Already in DB
        c.execute('select * from "' + race + '" where id=?', (post_id,))
        
        if c.fetchone() != None:
            # Post already in DB
            
            # Delete records if replacing them
            if not replace:
                continue
            c.execute('delete from "' + race + '" where id=?', (post_id,))
        
        
        # Add post to DB
        c.execute(
            'insert into "' + race + '" values (?,?,?,?,?,?)',
            (post_id, post_timestamp, post_url, post_author, post_content_raw, str(post_tags))
        )
    
        conn.commit()
    
    return(last_timestamp)

def fetchPostsForGP(race, delay = 500):
    '''
    Fetches all posts for a GP
    --
    Input: GP name
    Output: None
    '''
    
    # Get GP Start & End Time
    endTime = GP_DATA[race]["start"]
    startTime = GP_DATA[race]["end"]
    
    
    # Build Tag List
    tags = ["formula 1", "f1", "formula1"]
    for additionalTag in GP_DATA[race]["gp_tags"]:
        tags += additionalTag
    
    for tag in tags:
        nextTimeStamp = endTime
        print("Current tag:", tag)
        
        while (nextTimeStamp >= startTime):

            nextTimeStamp = getPostsToTimestamp(
                                    race,
                                    tag,
                                    nextTimeStamp,
                                    replace = True
                            )
            c.execute('select COUNT(*) as post_count from "' + race + '"')
            print(
                round((endTime-nextTimeStamp)/(endTime-startTime)*100,2), "% (",
                c.fetchone()[0],"posts )",
                end="\r"
            )
            sleep(delay / 1000)

def raceSummary(race, endTime = 1701010800, startTime = 1701003600, resolution = 5):
    
    # Get Data
    c.execute('select * from "' + race + '" WHERE "timestamp" >= ? AND "timestamp" <= ?',(startTime, endTime))
    data = c.fetchall()
    timestamps = []
    for row in data:
        timestamps.append(row[1])
   
    
    
    # Plot Time Chart
    dates=[datetime.datetime.fromtimestamp(ts) for ts in timestamps]
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