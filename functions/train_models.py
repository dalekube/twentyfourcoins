#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train the models for supported coins.

@author: Dale Kube (dkube@uwalumni.com)
"""

import os
import json
import pandas as pd
import numpy as np
import glob
import random

from skranger.ensemble import RangerForestRegressor
import bz2
import _pickle as cPickle

## DEVELOPMENT ONLY
## os.chdir('/home/dale/Downloads/GitHub/TwentyFourCoins/functions')

# Create a database connection
from db_connect import db_connect
con = db_connect('../data/db.sqlite')

# Load the configurations
with open('../config.json') as f:
    config = json.load(f)

# Iterate over the supported coins
for COIN in config['SUPPORTED_COINS'].values():
    
    ## DEVELOPMENT ONLY
    ## COIN = 'BAT-USDC'
    
    print('[INFO] Staring the iteration for', COIN)
    
    # Load the data for the coin
    # Print the row count when finished
    statement = 'SELECT * FROM prices WHERE coin = "%s"' % (COIN)
    df = pd.read_sql(statement, con)
    del df['coin']
    
    N_DF = len(df)
    assert N_DF > 0, '[ERROR] Zero rows in the collected data for ' + COIN
    print("[INFO] Successfully read", '{:,}'.format(N_DF), "rows from the database")
    
    # Calculate rolling average features
    df.sort_values(by=['time'], inplace=True)
    NUM_MOV_AVG = int(config['NUM_MOV_AVG'])
    for i in range(10, NUM_MOV_AVG, 10):
        df['MA_close_'+str(i)] = df['close'].rolling(window=i, min_periods=1, center=False).mean()
    
    # Drop rows with na values and convert to float32
    df.fillna(0, inplace=True)
    df = df.astype(np.float32)
    
    # Sort and calculate the 24 hours forward closing price (288 time periods of five minutes)
    # 86400/300 = 288
    # Remove observations without a 24-hour price target
    df.sort_values(by=['time'], inplace=True, ascending=False)
    df['PRICE_24'] = df['close'].shift(288)
    df = df[~pd.isnull(df['PRICE_24'])]
    
    # Split the training and testing data
    # Use a combinatorial approach, with samples from recent days and random days across history
    price_24 = df.pop('PRICE_24')
    N_TEST_RECENT = 3000
    N_TEST_RANDOM = 3000
    N_DF = len(df)
    print("[INFO] Defining the train/test split")
    
    # Sample recent days
    x_train = df[N_TEST_RECENT:].reset_index(drop=True)
    y_train = price_24[N_TEST_RECENT:].reset_index(drop=True)
    
    x_test_recent = df[:N_TEST_RECENT]
    y_test_recent = price_24[:N_TEST_RECENT] 
    
    # Random sample from the rest of the training data
    idx = random.sample(range(0,len(x_train)), N_TEST_RANDOM)
    x_test_random = x_train.iloc[idx,:]
    y_test_random = y_train.iloc[idx]
    
    x_test = pd.concat([x_test_recent, x_test_random])
    y_test = pd.concat([y_test_recent, y_test_random])
    
    x_train.drop(idx, inplace=True)
    y_train.drop(idx, inplace=True)
    
    # Train the random forest model
    print("[INFO] Training the RangerForestRegressor model")
    rfr = RangerForestRegressor(n_estimators=131, oob_error=False, sample_fraction=[0.25], min_node_size=1)
    rfr.fit(x_train, y_train)
    
    # Estimate the performance upon the test data
    rf_preds = rfr.predict(x_test)
    
    # Use the simple moving average as an option
    # Evaluate multiple moving averages to find the best performing range
    avgs_range = range(10, NUM_MOV_AVG, 10)
    avgs_mae = [np.mean(abs(x_test['MA_close_'+str(g)] - y_test)) for g in avgs_range]
    best_mov_avg = avgs_range[avgs_mae.index(min(avgs_mae))]
    mov_avg_col = 'MA_close_'+str(best_mov_avg)
    print('[INFO] Using', mov_avg_col, 'as the best moving average')
    mov_avg = x_test[mov_avg_col]
    
    # Evaluate all models and ensembles to achieve optimal performance
    # Ensemble the predictions from both models
    ensemble_preds_all = (rf_preds+mov_avg)/2.0
    ensemble_preds_rf_avg = (rf_preds+mov_avg)/2.0
    prediction_sets = {
            'RangerForestRegressor': rf_preds,
            'MovingAverage':mov_avg,
            'Ensemble_RF_AVG': ensemble_preds_rf_avg,
            }
    results = {}
    for model, preds in prediction_sets.items():
        
        # Mean Absolute Error
        MAE = np.mean(abs(preds - y_test))
        print('[INFO]', COIN, model, 'MAE =', '${:,.6f}'.format(MAE))
        results[model] = MAE
    
    best_model = min(results, key=results.get)
    print('[INFO] Best model with the lowest MAE =', best_model)
    best_preds = prediction_sets[best_model]
    
    # Calculate the MAE and MAPE with the best set of predictions
    MAE = np.mean(abs(best_preds - y_test))
    MAE = '{:.8f}'.format(MAE)
    MAPE = np.mean(abs((best_preds - y_test)/y_test))
    MAPE = '{:.8f}'.format(MAPE)
    
    # Log the model performance (M01)
    print('[INFO] Logging the model performance to the database')
    cursor = con.cursor()
    statement = 'INSERT INTO logs VALUES (strftime("%%s","now"), "M01", %s, %s, NULL, "%s", NULL)' % (MAE, MAPE, COIN)
    cursor.execute(statement)    
    cursor.close()
    con.commit()
    
    # Create the model directory if it doesn't already exist
    MODEL_DIR = '../models/' + COIN
    if not os.path.exists(MODEL_DIR):
        os.mkdir(MODEL_DIR)
    
    # Delete existing models
    print('[INFO] Deleting existing models')
    for f in glob.glob(MODEL_DIR + '/models*.pkl'):
        os.remove(f)
    
    # Save the model objects
    MODELS_FILE = MODEL_DIR + '/models-' + MAE + '.pkl'
    print("[INFO] Saving the models to file:", MODELS_FILE)
    with bz2.BZ2File(MODELS_FILE, 'wb') as f:
        cPickle.dump([rfr, best_model, mov_avg_col], f)
    
    # Finished
    print("[INFO] Successfully trained the models for", COIN)

# Close the database connection
con.close()
print('[INFO] Finished training all models')