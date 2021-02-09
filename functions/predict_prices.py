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
    
    ## DEVELOPMENT ONLY
    ## COIN = 'BAT-USDC'
    
    # Load the data for the coin
    # Print the row count when finished
    print('[INFO] Starting the iteration for', COIN)
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
    
    # Drop rows with na values and convert to float32
    df.fillna(0, inplace=True)
    df = df.astype(np.float32)
    
    # Load the best model
    MODEL_DIR = '../models/' + COIN + '/'
    
    # If a specific model version is not defined,
    # automatically identify the best model with the lowest error
    model_files = glob.glob(MODEL_DIR + 'models*.pkl')
    assert len(model_files) > 0, '[ERROR] No models are available for predictions for ' + COIN
    model_errors = [i.split('-')[2] for i in model_files]
    model_errors = [float(os.path.splitext(i)[0]) for i in model_errors]
    model_min_error = min(model_errors)
    best_model = [i for i in model_files if re.search(str(model_min_error), i)]
    assert len(best_model) == 1, '[ERROR] Unable to identify a pickle file with the lowest error for ' + COIN
    
    MODELS_FILE = best_model[0] 
    print("[INFO] Loading the model objects:", MODELS_FILE)
    with bz2.BZ2File(MODELS_FILE, 'rb') as f:
        rfr, best_model, mov_avg_col = cPickle.load(f)
    
    # Make prediction with the latest observation closest to NOW()
    df['time'] = df['time'].astype(int)
    df.sort_values(by=['time'], inplace=True)
    df_predict = df.tail(1)
    
    actual_time = int(df_predict['time'])
    actual_time_str = datetime.utcfromtimestamp(actual_time).strftime("%Y-%m-%d %H:%M:%S")
    actual_close = float(df_predict['close'])
    
    predict_time = int(df_predict['time']) + 86400    
    predict_time_str = datetime.utcfromtimestamp(predict_time).strftime("%Y-%m-%d %H:%M:%S")
    
    # Random forest prediction
    rf_pred = rfr.predict(df_predict)
    
    # Moving average prediction
    avg_pred = df_predict[mov_avg_col]
    
    # Use the predictions associated with the best model
    assert best_model in ['RangerForestRegressor', 'MovingAverage', 'Ensemble_RF_AVG']
    print('[INFO] Making predictions with the best model:', best_model)
    if best_model == 'RangerForestRegressor':
        
        prediction = rf_pred[0]
    
    elif best_model == 'MovingAverage':
        
        prediction = float(avg_pred)
        
    elif best_model == 'Ensemble_RF_AVG':
        
        prediction = float((rf_pred+avg_pred)/2.0)
    
    # Log the latest actual price and corresponding prediction details
    actual_close = round(actual_close,8)
    prediction = round(prediction,8)
    expected_change_pct = round((prediction/actual_close)-1,8)
    expected_change = prediction-actual_close
    expected_change = round(expected_change,8)
    change_direction = 'up' if expected_change > 0 else 'down'
    
    cursor = con.cursor()
    statement = 'INSERT INTO predictions VALUES ("%s", "%s", %s, "%s", %s)' % (COIN, actual_time, actual_close, predict_time, prediction)
    cursor.execute(statement)    
    cursor.close()
    con.commit()
    
    print('[INFO] Making forward-looking prediction from', actual_time_str)
    print('[INFO] Latest actual price =', '{:,}'.format(actual_close))
    print('[INFO] Prediction time =', predict_time_str)  
    print('[INFO] Predicted price =', '{:,}'.format(prediction))
    print('[INFO] The price is expected to change by', str(expected_change), 'dollars in the next 24 hours')
    
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
    print('[INFO] Finished with the forecast for', COIN)
    
    # Overwrite the JSON file with the latest details
    JSON_DUMP = MODEL_DIR + 'latest.json'
    with open(JSON_DUMP, 'w') as f:
        json.dump({
            'actual_time':actual_time_str,
            'actual_close':'$ {:,.4f}'.format(actual_close),
            'prediction':'$ {:,.4f}'.format(prediction),
            'expected_change':'$ {:,.4f}'.format(expected_change),
            'expected_change_pct':'{:.2%}'.format(expected_change_pct),
            'change_direction': change_direction,
            'stats_training_time': training_time,
            'stats_mae': '$ {:,.4f}'.format(model_min_error),
            'stats_mape': '{:.2%}'.format(model_stats['VALUE2'])
            }, f)
    
    # Collect predictions for the predictive performance chart
    # Limit to the past 12 months
    YEAR_DT = pd.to_datetime('now') - pd.DateOffset(months=12)
    
    statement = 'SELECT PREDICTION_TIME, PREDICTION FROM predictions WHERE COIN = "%s"' % COIN
    df_preds = pd.read_sql(statement, con)
    df_preds.columns = ['time','pred']
    df_preds['time'] = df_preds.apply(lambda row: datetime.utcfromtimestamp(row['time']), axis=1)
    df_preds['time'] = pd.to_datetime(df_preds['time'])
    df_preds['time'] = df_preds['time']
    df_preds = df_preds[df_preds['time'] > YEAR_DT]
    df_preds = df_preds.sort_values(by=['time'])
    print('[INFO] Collected', '{:,}'.format(len(df_preds)), 'predicted prices for the charts')
    
    statement = 'SELECT time, close FROM prices WHERE coin="%s"' % COIN
    df_actuals = pd.read_sql(statement, con)
    df_actuals['time'] = df_actuals.apply(lambda row: datetime.utcfromtimestamp(row['time']), axis=1)
    df_actuals['time'] = pd.to_datetime(df_actuals['time'])
    df_actuals = df_actuals[df_actuals['time'] > YEAR_DT]
    df_actuals = df_actuals[df_actuals['time'] >= min(df_preds['time'])]
    df_actuals = df_actuals.sort_values(by=['time'])
    print('[INFO] Collected', '{:,}'.format(len(df_actuals)), 'actual prices for the charts')
    
    # Overwrite the JSON file with the latest details
    JSON_DUMP = MODEL_DIR + 'charts.json'
    with open(JSON_DUMP, 'w') as f:
        json.dump({
            'actuals':df_actuals.to_json(),
            'predictions':df_preds.to_json(),
            }, f)

# Close the database connection when finished
con.close()

