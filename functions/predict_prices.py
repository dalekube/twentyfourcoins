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
import pandas as pd
import bz2
import _pickle as cPickle

os.chdir(os.path.dirname(os.path.realpath(__file__)))
from training_data import training_data
from db_connect import db_connect
con = db_connect('../data/db.sqlite')

# Load the historical prices for important features
from features.stock_spy import features_stock_spy
from features.bitcoin import features_bitcoin
prices_spy = features_stock_spy(con)
prices_btc = features_bitcoin(con)

# Load the configurations
with open('../config.json') as f:
    config = json.load(f)

# Iterate over every supported coin
for COIN in config['SUPPORTED_COINS'].values():
    
    for w in config['SUPPORTED_WINDOWS']:
    
        # Load the data for the coin
        # Print the row count when finished
        WINDOW = int(w)
        TIME_INTERVAL = 288
        
        print('[INFO] Starting the iteration for', COIN)
        print('[INFO] Time window (5 minute bundles) =', WINDOW)
        df = training_data(con, config, COIN, WINDOW, prices_spy, prices_btc, inference=True)
        
        # Load the best model
        MODEL_DIR = '../models/' + COIN + '/' + str(WINDOW) + '/'
        
        # If a specific model version is not defined,
        # automatically identify the best model with the lowest error
        model_files = glob.glob(MODEL_DIR + 'models*.pkl')
        assert len(model_files) > 0, '[ERROR] No models available'
        model_errors = [i.split('-')[2] for i in model_files]
        model_errors = [float(os.path.splitext(i)[0]) for i in model_errors]
        model_min_error = min(model_errors)
        best_model = [i for i in model_files if re.search(str(model_min_error), i)]
        assert len(best_model) == 1, '[ERROR] Unable to identify a pickle file with the lowest error'
        
        MODELS_FILE = best_model[0] 
        print("[INFO] Loading the model objects:", MODELS_FILE)
        with bz2.BZ2File(MODELS_FILE, 'rb') as f:
            rfr, lr, best_model, mov_avg_col = cPickle.load(f)
        
        # Make prediction with the latest observation closest to NOW()
        df_predict = df.tail(1)
        actual_time = str(df_predict['time'].iloc[0])
        actual_price = float(df_predict['price'].iloc[0])
        predict_time = str(df_predict['time'].iloc[0] + pd.DateOffset(WINDOW/TIME_INTERVAL))
        del df_predict['time']
        
        # Random forest prediction
        rf_pred = rfr.predict(df_predict)
        
        # Linear regression prediction
        lr_pred = lr.predict(df_predict)
        
        # Moving average prediction
        avg_pred = df_predict[mov_avg_col]
        
        # Use the predictions associated with the best model
        assert best_model in ['RangerForestRegressor', 'MovingAverage', 'LinearRegression',
                              'Ensemble_ALL', 'Ensemble_RF_AVG', 'Ensemble_RF_LR', 'Ensemble_AVG_LR']
        print('[INFO] Making predictions with the best model:', best_model)
        if best_model == 'RangerForestRegressor':
            
            prediction = rf_pred[0]
        
        elif best_model == 'MovingAverage':
            
            prediction = float(avg_pred)
            
        elif best_model == 'LinearRegression':
            
            prediction = float(lr_pred)
            
        elif best_model == 'Ensemble_ALL':
            
            prediction = float((rf_pred+avg_pred+lr_pred)/3.0)
            
        elif best_model == 'Ensemble_RF_AVG':
            
            prediction = float((rf_pred+avg_pred)/2.0)
        
        elif best_model == 'Ensemble_RF_LR':
            
            prediction = float((rf_pred+lr_pred)/2.0)
            
        elif best_model == 'Ensemble_AVG_LR':
            
            prediction = float((avg_pred+lr_pred)/2.0)
        
        # Log the latest actual price and corresponding prediction details
        actual_price = round(actual_price,8)
        prediction = round(prediction,8)
        expected_change_pct = round((prediction/actual_price)-1,8)
        expected_change = prediction-actual_price
        expected_change = round(expected_change,8)
        change_direction = 'up' if expected_change > 0 else 'down'
        
        cursor = con.cursor()
        statement = 'INSERT INTO predictions \
        VALUES ("%s", "%s", %s, "%s", %s, %s)' % (COIN, actual_time, actual_price, predict_time, prediction, WINDOW)
        cursor.execute(statement)    
        cursor.close()
        con.commit()
        
        print('[INFO] Making forward-looking prediction from', actual_time)
        print('[INFO] Latest actual price =', '{:,}'.format(actual_price))
        print('[INFO] Prediction time =', predict_time)  
        print('[INFO] Predicted price =', '{:,}'.format(prediction))
        print('[INFO] The price is expected to change by', str(expected_change), 'dollars in the next 24 hours')
        
        # Query the database for the logged performance statistics
        statement = 'SELECT * FROM model_performance \
        WHERE MAE=%s AND COIN="%s" AND WINDOW=%s' % (model_min_error, COIN, WINDOW)
        model_stats = pd.read_sql(statement, con)
        
        assert len(model_stats) > 0, '[ERROR] Did not identify any statistics in the logs'
        model_stats['UTC_TIME'] = pd.to_datetime(model_stats['UTC_TIME'])
        model_stats = model_stats.sort_values(by=['UTC_TIME'], ascending=False)
        model_stats = model_stats.head(1) 
        training_time = str(model_stats['UTC_TIME'].iloc[0])
        MAPE = model_stats['MAPE'].iloc[0]
        
        # Print the performance statistics
        print('[INFO] Model trained at', training_time)
        print('[INFO] Mean Absolute Error (MAE) =', '${:,.4f}'.format(model_min_error))
        print('[INFO] Mean Absolute Percentage Error (MAPE) =', '{:.2%}'.format(MAPE))
        
        # Overwrite the JSON file with the latest details
        JSON_DUMP = MODEL_DIR + 'latest.json'
        with open(JSON_DUMP, 'w') as f:
            json.dump({
                'actual_time':actual_time,
                'actual_price':'$ {:,.4f}'.format(actual_price),
                'prediction':'$ {:,.4f}'.format(prediction),
                'expected_change':'$ {:,.4f}'.format(expected_change),
                'expected_change_pct':'{:.2%}'.format(expected_change_pct),
                'change_direction': change_direction,
                'stats_training_time': training_time,
                'stats_mae': '$ {:,.4f}'.format(model_min_error),
                'stats_mape': '{:.2%}'.format(MAPE)
                }, f)
        
        # Collect predictions for the predictive performance chart
        # Limit to the past N months
        YEAR_DT = pd.to_datetime('now') - pd.DateOffset(months=3)
        
        statement = 'SELECT PREDICTION_TIME, PREDICTION FROM predictions \
        WHERE COIN = "%s" AND WINDOW = %s' % (COIN, WINDOW)
        df_preds = pd.read_sql(statement, con)
        df_preds.columns = ['time','pred']
        df_preds['time'] = pd.to_datetime(df_preds['time'])
        df_preds = df_preds[df_preds['time'] > YEAR_DT]
        df_preds = df_preds.sort_values(by=['time'])
        assert len(df_preds) > 0, '[ERROR] Collected zero predicted prices'
        print('[INFO] Collected', '{:,}'.format(len(df_preds)), 'predicted prices for the charts')
        
        statement = 'SELECT time, price FROM prices_coinbase WHERE coin="%s"' % COIN
        df_actuals = pd.read_sql(statement, con)
        df_actuals['time'] = pd.to_datetime(df_actuals['time'])
        df_actuals = df_actuals[df_actuals['time'] > YEAR_DT]
        df_actuals = df_actuals.sort_values(by=['time'])
        assert len(df_actuals) > 0, '[ERROR] Collected zero actual prices'
        print('[INFO] Collected', '{:,}'.format(len(df_actuals)), 'actual prices for the charts')
        
        # Timestamps are not JSON serializable
        df_preds['time'] = df_preds['time'].astype(str)
        df_preds = df_preds.reset_index(drop=True)
        df_actuals['time'] = df_actuals['time'].astype(str)
        df_actuals = df_actuals.reset_index(drop=True)
        
        # Overwrite the JSON file with the latest details
        JSON_DUMP = MODEL_DIR + 'charts.json'
        with open(JSON_DUMP, 'w') as f:
            json.dump({
                'actuals':df_actuals.to_json(),
                'predictions':df_preds.to_json(),
                }, f)

# Close the database connection when finished
con.close()

