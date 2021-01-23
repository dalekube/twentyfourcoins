#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train the model for the specified coin.

Example call: python3 train-model.py BAT-USDC

    Parameters:
        Coin (string): The code for a coin (e.g. BAT-USDC)

@author: Dale Kube (dkube@uwalumni.com)
"""

import os
import json
import pandas as pd
import numpy as np

import xgboost as xgb
from skranger.ensemble import RangerForestRegressor
import bz2
import _pickle as cPickle

## DEVELOPMENT ONLY
## import os
## os.chdir('/home/dale/Downloads/GitHub/TwentyFourCoins/functions')

# Create a database connection
from db_connect import db_connect
con = db_connect('../data/db.sqlite')

# Load the configurations
with open('../config.json') as f:
    config = json.load(f)

# Iterate over the supported coins
for COIN in config['SUPPORTED_COINS'].values():

    # Load the data for the coin
    # Print the row count when finished
    statement = 'SELECT * FROM prices WHERE coin = "%s"' % (COIN)
    df = pd.read_sql(statement, con)
    del df['coin']
    
    N_DF = len(df)
    assert N_DF > 0, '[ERROR] Zero rows in the collected data for ' + COIN
    print("[INFO] Successfully read", '{:,}'.format(N_DF), "rows from the database")
    
    #    # Append closing prices and volumes for correlative coins
    #    # Correlative data helps the model to understand confounding market trends
    #    correlations = config['MODEL_CORRELATIONS']['BAT-USDC']
    #    close_cols = []
    #    for i in correlations:
    #            # Load the data for the coin
    #            # Print the row count when finished
    #            print('[INFO] Reading historical data for correlative coin', i)
    #            statement = 'SELECT time, close, volume FROM prices WHERE coin = "%s"' % i
    #            df_cor = pd.read_sql(statement, con)
    #            N_DF_COR = len(df_cor)
    #            assert N_DF_COR > 0, '[ERROR] Missing prices for correlative coin'
    #            print('[INFO] Successfully read', '{:,}'.format(N_DF_COR), 'rows from the database')
    #            
    #            print('[INFO] Merging the correlative prices and volumes')
    #            cols_cor = [j + '-' + i for j in df_cor.columns if j != 'time']
    #            close_cols = close_cols + [cols_cor[0]]
    #            df_cor.columns = ['time'] + cols_cor
    #            df = df.merge(df_cor,on='time',how='left')
    #            assert N_DF == len(df), '[ERROR] Unintended row expansion from correlative data merger'
    
    # Calculate rolling average features
    df.sort_values(by=['time'], inplace=True)
    NUM_MOV_AVG = int(config['NUM_MOV_AVG'])
    for i in range(10, NUM_MOV_AVG, 10):
        df['MA_close_'+str(i)] = df['close'].rolling(window=i, min_periods=1, center=False).mean()
        #df['MA_volume_'+str(i)] = df['volume'].rolling(window=i, min_periods=1, center=False).mean()
    #        for y in close_cols:
    #            df['MA'+str(i)+'_'+y] = df[y].rolling(window=i, min_periods=1, center=False).mean()
    
    # Drop rows with na values and convert to float32
    df.fillna(0, inplace=True)
    df = df.astype(np.float32)
    
    # Sort and calculate the 24 hours forward closing price (288 time periods of five minutes)
    # 86400/300 = 288
    # Remove observations without a 24-hour price target
    df.sort_values(by=['time'], inplace=True)
    df['PRICE_24'] = df['close'].shift(288)
    df = df[~pd.isnull(df['PRICE_24'])]
    
    # Split the training and testing data
    # Use the latest 3,000 observations for the test split
    price_24 = df.pop('PRICE_24')
    N_TEST = 3000
    N_ESTIMATORS = 101
    SAMPLE_FRACTION = 0.25
    N_DF = len(df)
    
    print("[INFO] Defining the train/test split")
    print("[INFO] Training the models and evaluating the performance using the latest", '{:,}'.format(N_TEST), "candles")
    x_train = df[0:N_DF-N_TEST]
    y_train = price_24[0:N_DF-N_TEST]
    
    x_test = df[-N_TEST:]
    y_test = price_24[-N_TEST:]
    
    # Train the random forest model
    rfr = RangerForestRegressor(n_estimators=N_ESTIMATORS, oob_error=False, 
                                sample_fraction=[SAMPLE_FRACTION])
    rfr.fit(x_train, y_train)
    
    # Estimate the performance upon the test data
    rf_preds = rfr.predict(x_test)
    
    # Train the xgboost model
    dtrain = xgb.DMatrix(x_train, y_train)
    dtest = xgb.DMatrix(x_test, y_test)
    
    evallist = [(dtrain, 'train'), (dtest, 'val')]
    param = {'max_depth': 6, 'eta': 0.1, 'objective': 'reg:squarederror', 
             'eval_metric': 'mape', 'subsample':0.3}
    
    xgb_model = xgb.train(param, dtrain, num_boost_round=500, evals=evallist, 
                          early_stopping_rounds=3, maximize=False)
    
    xgb_preds = xgb_model.predict(dtest)
    
    # Ensemble the predictions from both models
    predictions = (rf_preds+xgb_preds)/2.0
    
    # Mean Absolute Error
    MAE = np.mean(abs(predictions - y_test))
    print('[INFO] Ensemble MAE =', '${:,.4f}'.format(MAE))
    MAE = '{:.8f}'.format(MAE)
    
    # Mean Absolute Percentage Error
    MAPE_RF = np.mean(abs((rf_preds - y_test)/y_test))
    MAPE_XGB = np.mean(abs((xgb_preds - y_test)/y_test))
    MAPE = np.mean(abs((predictions - y_test)/y_test))
    print('[INFO] Ensemble MAPE =', '{:.2%}'.format(MAPE))
    BASELINE = (MAPE/min(MAPE_RF,MAPE_XGB))-1
    print('[INFO] Percentage improvement due to ensemble =', '{:.2%}'.format(-1 * BASELINE))
    MAPE = '{:.8f}'.format(MAPE)
    
    # Log the model performance (M01)
    print('[INFO] Logging the model performance to the database')
    cursor = con.cursor()
    statement = 'INSERT INTO logs VALUES (strftime("%%s","now"), "M01", %s, %s, NULL, "%s")' % (MAE, MAPE, COIN)
    cursor.execute(statement)    
    cursor.close()
    con.commit()
    
    # Create the model directory if it doesn't already exist
    MODEL_DIR = '../models/' + COIN
    if not os.path.exists(MODEL_DIR):
        os.mkdir(MODEL_DIR)
    
    # Save both models
    MODELS_FILE = MODEL_DIR + '/models-' + MAE + '.pkl'
    print("[INFO] Saving the models to file:", MODELS_FILE)
    with bz2.BZ2File(MODELS_FILE, 'wb') as f:
        cPickle.dump([rfr,xgb_model], f)
    
    # Finished
    print("[FINISHED] Successfully trained the models for", COIN)

# Close the database connection
con.close()
print('[INFO] Finished training all models')