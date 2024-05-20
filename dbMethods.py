import sqlite3

# Connect to DB
global conn
global c
conn = sqlite3.connect('postDb.db')
c = conn.cursor()