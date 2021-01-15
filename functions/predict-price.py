#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train the model for BAT-USDC

Example call: python3 predict-price.py BAT-USDC weights-BAT-USDC-0.0005.hdf5

    Parameters:
        Coin (string): The code for a coin (e.g. BAT-USDC)
        Model Object (string): Filename for the model object to use for the inference

@author: dale
"""

import sys
import json
import re

import numpy as np
import pandas as pd
from datetime import datetime
import pickle

## DEVELOPMENT ONLY
## import os
## os.chdir('/home/dale/Downloads/GitHub/coinML/functions')

# Create a database connection
from db_connect import db_connect
con = db_connect('../data/db.sqlite')

# Load the configurations
with open('../config.json') as f:
    config = json.load(f)

# Evaluate the command line parameters
# argv[1] = coin name (e.g. BAT-USDC)
# argv[2] = model object name (e.g. weights-BAT-USDC-0.0022.hdf5)
assert len(sys.argv) == 3, '[ERROR] Invalid command line arguments.'

## DEVELOPMENT ONLY
## COIN = 'BAT-USDC'

# Identify the specific coin
COIN = sys.argv[1]
assert COIN in config['SUPPORTED_COINS'], "[ERROR] " + COIN + " is not supported"

# Load the data for the coin
# Print the row count when finished
statement = 'SELECT * FROM prices WHERE coin = "%s"' % (COIN)
df = pd.read_sql(statement, con)
del df['coin']

N_DF = len(df)
assert N_DF > 0, "[ERROR] Zero rows in the collected data for " + COIN
print("[INFO] Successfully read", '{:,}'.format(N_DF), "rows from the database")

# Calculate rolling average features
df.sort_values(by=['time'], inplace=True)
NUM_MOV_AVG = int(config['NUM_MOV_AVG'])
for i in range(10, NUM_MOV_AVG, 10):
    df['MA_close_'+str(i)] = df['close'].rolling(window=i, min_periods=1, center=False).mean()
    df['MA_volume_'+str(i)] = df['volume'].rolling(window=i, min_periods=1, center=False).mean()

# Drop rows with na values and convert to float32
df.fillna(0, inplace=True)
df = df.astype(np.float32)

## DEVELOPMENT ONLY
## MODEL_PATH = './models/' + COIN + '/RF-0.00471387.pkl'

# Load the neural network model
assert sys.argv[2] is not None, "[ERROR] Null model file path"
MODEL_PATH = '../models/' + COIN + '/' + sys.argv[2]
if re.match(".*\/RF.*pkl$", MODEL_PATH):
    print("[INFO] Loading the RangerForestRegressor model", MODEL_PATH)
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
else:
    print("[ERROR] Model path does not align to a valid model")
    sys.exit(0)

# Make prediction with the latest observation closest to NOW()
df['time'] = df['time'].astype(int)
df['UTC_TIME'] = df.apply(lambda row: datetime.utcfromtimestamp(row['time']), axis=1)
df.sort_values(by=['time'], inplace=True)
df_predict = df.tail(1)

p_unixtime = int(df_predict['time'])
p_time = df_predict.pop('UTC_TIME')
p_time = str(p_time.tolist()[0])
p_close = float(df_predict['close'])
p_now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

prediction = float(model.predict(df_predict))
EXPECTED_CHANGE = prediction-p_close

# Log the current price and prediction (P01)
# VALUE1 = Latest Price
# VALUE2 = Predicted Price
# VALUE3 = Unix time for the candle used for the prediction
p_close = round(p_close,8)
prediction = round(prediction,8)
EXPECTED_CHANGE = round(EXPECTED_CHANGE,8)

cursor = con.cursor()
statement = 'INSERT INTO logs VALUES (strftime("%%s","now"), "P01", %s, %s, %s, NULL)' % (p_close, prediction, p_unixtime)
cursor.execute(statement)    
cursor.close()
con.commit()
con.close()

print('[INFO] Making forward-looking prediction from', p_time)
print('[INFO] Current time =', p_now)  
print('[INFO] Current price =', str(p_close))
print('[INFO] Predicted price =', str(prediction))
print('[RESULT] The price is expected to change by', str(EXPECTED_CHANGE), 'dollars in the next 24 hours')
