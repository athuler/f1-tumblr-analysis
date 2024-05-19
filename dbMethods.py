import sqlite3

# Connect to DB
global conn
global c
conn = sqlite3.connect('f1_tumblr_analysis.db')
c = conn.cursor()