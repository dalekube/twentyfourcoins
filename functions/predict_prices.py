#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Predict new prices for all supported coins

@author: Dale Kube (dkube@uwalumni.com)
"""

import os
import re
import json
import glob
import numpy as np
import pandas as pd
from datetime import datetime
import bz2
import _pickle as cPickle

## DEVELOPMENT ONLY
## os.chdir('/home/dale/Downloads/GitHub/TwentyFourCoins/functions')

from db_connect import db_connect
con = db_connect('../data/db.sqlite')

# Load the configurations
with open('../config.json') as f:
    config = json.load(f)

# Iterate over every supported coin
for COIN in config['SUPPORTED_COINS'].values():
    
    print('[INFO] Starting the iteration for', COIN)
    ## DEVELOPMENT ONLY
    ## COIN = 'BAT-USDC'
    
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
    
    # Load the best model
    MODEL_DIR = '../models/' + COIN + '/'
    
    # If a specific model version is not defined,
    # automatically identify the best model with the lowest error
    model_files = glob.glob(MODEL_DIR + 'RF*.pkl')
    assert len(model_files) > 0, '[ERROR] No models are available for predictions'
    model_errors = [i.split('-')[2] for i in model_files]
    model_errors = [float(os.path.splitext(i)[0]) for i in model_errors]
    model_min_error = min(model_errors)
    best_model = [i for i in model_files if re.search(str(model_min_error), i)]
    assert len(best_model) == 1, '[ERROR] Unable to identify a model with the lowest error for ' + COIN
    MODEL_PATH = best_model[0] 
    
    print("[INFO] Loading the RangerForestRegressor model", MODEL_PATH)
    with bz2.BZ2File(MODEL_PATH, 'rb') as f:
        model = cPickle.load(f)
    
    # Make prediction with the latest observation closest to NOW()
    df['time'] = df['time'].astype(int)
    df['UTC_TIME'] = df.apply(lambda row: datetime.utcfromtimestamp(row['time']), axis=1)
    df.sort_values(by=['time'], inplace=True)
    df_predict = df.tail(1)
    
    p_unixtime = int(df_predict['time'])
    p_time = df_predict.pop('UTC_TIME')
    predict_time = str(p_time.tolist()[0])
    p_close = float(df_predict['close'])
    predict_now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    prediction = float(model.predict(df_predict))
    expected_change = prediction-p_close
    
    # Log the current price and prediction (P01)
    # VALUE1 = Latest Price
    # VALUE2 = Predicted Price
    # VALUE3 = Unix time for the candle used for the prediction
    predict_close = round(p_close,8)
    prediction = round(prediction,8)
    expected_change = round(expected_change,8)
    change_direction = 'up' if expected_change > 0 else 'down'
    
    cursor = con.cursor()
    statement = 'INSERT INTO logs VALUES (strftime("%%s","now"), "P01", %s, %s, %s, NULL)' % (predict_close, prediction, p_unixtime)
    cursor.execute(statement)    
    cursor.close()
    con.commit()
    
    print('[INFO] Making forward-looking prediction from', predict_time)
    print('[INFO] Current time =', predict_now)  
    print('[INFO] Current price =', str(predict_close))
    print('[INFO] Predicted price =', str(prediction))
    print('[FINISHED] The price is expected to change by', str(expected_change), 'dollars in the next 24 hours')
    
    # Query the database for the logged performance statistics
    statement = 'SELECT * FROM logs WHERE ACTIVITY="M01" AND VALUE1=%s AND META1="%s"' % (model_min_error, COIN)
    model_stats = pd.read_sql(statement, con)
    
    assert len(model_stats) > 0, '[ERROR] Did not identify any statistics in the logs'
    model_stats = model_stats.sort_values(by=['UTC_TIME'], ascending=False)
    model_stats = model_stats.iloc[0,:]
    training_time = str(datetime.utcfromtimestamp(model_stats['UTC_TIME']))
    
    # Print the performance statistics
    print('[INFO] Model statistics for', COIN)
    print('[INFO] Model trained at', training_time)
    print('[INFO] Mean Absolute Error (MAE) =', '${:,.4f}'.format(model_min_error))
    print('[INFO] Mean Absolute Percentage Error (MAPE) =', '{:.2%}'.format(model_stats['VALUE2']))
    print('[FINISHED] Finished with the forecast for', COIN)
    
    # Overwrite the JSON file with the latest details
    JSON_DUMP = MODEL_DIR + 'latest.json'
    with open(JSON_DUMP, 'w') as f:
        json.dump({
            'predict_time':predict_time,
            'predict_now':predict_now,
            'predict_close':'$ {:,.4f}'.format(predict_close),
            'prediction':'$ {:,.4f}'.format(prediction),
            'expected_change':'$ {:,.4f}'.format(expected_change),
            'change_direction': change_direction,
            'stats_training_time': training_time,
            'stats_mae': '$ {:,.4f}'.format(model_min_error),
            'stats_mape': '{:.2%}'.format(model_stats['VALUE2'])
            }, f)

# Close the database connection when finished
con.close()
