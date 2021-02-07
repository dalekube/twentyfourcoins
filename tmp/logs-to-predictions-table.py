#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert logs to tables, TEMPORARY

@author: Dale Kube (dkube@uwalumni.com)
"""


import os
os.chdir('/home/dale/Downloads/GitHub/TwentyFourCoins/functions')

from db_connect import db_connect
con = db_connect('../data/db.sqlite')
cursor = con.cursor()

# Create the 'predictions' table
statement = '\
CREATE TABLE IF NOT EXISTS predictions (\
COIN TEXT NOT NULL,\
ACTUAL_TIME INT NOT NULL,\
ACTUAL_CLOSE FLOAT NOT NULL,\
PREDICTION_TIME INT NOT NULL,\
PREDICTION FLOAT NOT NULL\
)\
'
cursor.execute(statement)
cursor.execute('pragma table_info("predictions")')
cursor.fetchall()

# Move the logs into the predictions table
statement = "\
INSERT INTO predictions \
SELECT META1, VALUE3, VALUE1, UTC_TIME, VALUE2 \
FROM logs \
WHERE ACTIVITY = 'P01'\
"
cursor.execute(statement)
cursor.execute('SELECT * FROM predictions LIMIT 5')
cursor.fetchall()

# Delete the logs
# Confirm the empty set
statement = "\
DELETE FROM logs \
WHERE ACTIVITY = 'P01'\
"
cursor.execute(statement)
cursor.execute('SELECT * FROM logs WHERE ACTIVITY = "P01"')
cursor.fetchall()
cursor.close()
con.close()

# cursor.execute('DROP TABLE predictions')