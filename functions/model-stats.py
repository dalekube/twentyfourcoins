#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Show the performance statistics for the best model for a specified coin

@author: dale
"""

import os
import sys
import json
import glob
import pandas as pd
from datetime import datetime

## DEVELOPMENT ONLY
## os.chdir('/home/dale/Downloads/GitHub/coinML/functions')

# Create a database connection
from db_connect import db_connect
con = db_connect('../data/db.sqlite')

# Load the configurations
with open('../config.json') as f:
    config = json.load(f)

# Evaluate the command line parameters
# argv[1] = coin name (e.g. BAT-USDC)
assert len(sys.argv) == 2, '[ERROR] Invalid command line arguments'

## DEVELOPMENT ONLY
## COIN = 'BAT-USDC'

# Identify the specific coin
COIN = sys.argv[1]
assert COIN in config['SUPPORTED_COINS'], "[ERROR] " + COIN + " is not supported"

# If a specific model version is not defined,
# automatically identify the best model with the lowest error
MODEL_DIR = '../models/' + COIN + '/'
model_files = glob.glob(MODEL_DIR + 'RF*.pkl')
model_errors = [i.split('-')[2] for i in model_files]
model_errors = [float(os.path.splitext(i)[0]) for i in model_errors]
model_min_error = min(model_errors)

# Query the database for the logged performance statistics
statement = 'SELECT * FROM logs WHERE ACTIVITY="M01" AND VALUE1=%s' % model_min_error
model_stats = pd.read_sql(statement, con)
con.close()
assert len(model_stats) > 0, '[ERROR] Did not identify any statistics in the logs'
model_stats = model_stats.sort_values(by=['UTC_TIME'], ascending=False)
model_stats = model_stats.iloc[0,:]
training_time = str(datetime.utcfromtimestamp(model_stats['UTC_TIME']))

# Print the performance statistics
print('[INFO] Model statistics for', COIN)
print('[INFO] Model trained at', training_time)
print('[INFO] Mean Absolute Error (MAE) =', '${:,.4f}'.format(model_min_error))
print('[INFO] Mean Absolute Percentage Error (MAPE) =', '{:.2%}'.format(model_stats['VALUE2']))
print('[FINISHED] Successfully returned the model performance statistics')


