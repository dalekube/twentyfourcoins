#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Used to initialize the SQLite3 database from scratch.

@author: dale
"""

## DEVELOPMENT ONLY
## import os
## os.chdir('/home/dale/Downloads/GitHub/TwentyFourCoins/functions')

# Create a database object if it doesn't already exist
from db_connect import db_connect
con = db_connect('../data/db.sqlite')
cursor = con.cursor()

# Create the master 'logs' table
statement = '\
CREATE TABLE IF NOT EXISTS logs (\
UTC_TIME INT NOT NULL,\
ACTIVITY VARCHAR(3) NOT NULL,\
VALUE1 FLOAT,\
VALUE2 FLOAT,\
VALUE3 FLOAT,\
META1 TEXT\
)\
'
cursor.execute(statement)

# Create the 'prices' table
statement = '\
CREATE TABLE IF NOT EXISTS prices (\
coin TEXT NOT NULL,\
time INT NOT NULL,\
low FLOAT NOT NULL,\
high FLOAT NOT NULL,\
open FLOAT NOT NULL,\
close FLOAT NOT NULL,\
volume INT NOT NULL\
)\
'
cursor.execute(statement)

# Random queries to validate changes
statement = 'SELECT * FROM logs'
statement = 'SELECT * FROM logs ORDER BY UTC_TIME DESC LIMIT 10'
statement = 'SELECT * FROM prices LIMIT 10'
statement = 'pragma table_info("logs")'
cursor.execute(statement)
cursor.fetchall()

# Close the cursor and connection
cursor.close()
con.close()
