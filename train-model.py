#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train the model for the specified coin.

Example call: python3 train-model.py BAT-USDC

    Parameters:
        Coin (string): The code for a coin (e.g. BAT-USDC)

@author: Dale Kube (dkube@uwalumni.com)
"""

import sys
import json
import pandas as pd
import numpy as np
from skranger.ensemble import RangerForestRegressor
import pickle

## DEVELOPMENT ONLY
## import os
## os.chdir('/home/dale/Downloads/GitHub/coinML')

# Create a database connection
from data.db_connect import db_connect
con = db_connect('./data/db.sqlite')

# Load the configurations
with open('config.json') as f:
    config = json.load(f)

# Evaluate the command line parameters
# argv[1] = coin name (e.g. BAT-USDC)
if len(sys.argv) > 1:
    
    assert sys.argv[1] is not None, '[ERROR] Missing coin parameter (e.g. BAT-USDC)'
    COIN = sys.argv[1]
    
    ## DEVELOPMENT ONLY
    ## COIN = 'BAT-USDC'
    
    # Load the data for the coin
    # Print the row count when finished
    assert COIN in config['SUPPORTED_COINS'], "[ERROR] " + COIN + " is not supported"

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
    for i in range(10, 2000, 10):
        df['MA'+str(i)] = df['close'].rolling(window=i, min_periods=1, center=False).mean()
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
    N_DF = len(df)
    
    print("[INFO] Training the model and evaluating the performance using the latest", '{:,}'.format(N_TEST), "days")
    x_train = df[0:N_DF-N_TEST]
    y_train = price_24[0:N_DF-N_TEST]
    
    x_test = df[-N_TEST:]
    y_test = price_24[-N_TEST:]
    
    # Train the random forest model
    print("[INFO] Training the RangerForestRegressor")
    rfr = RangerForestRegressor(n_estimators=150, oob_error=False)
    rfr.fit(x_train, y_train)
    
    # Estimate the performance upon the test data
    predictions = rfr.predict(x_test)
    errors = abs(predictions - y_test)
    MAE = np.mean(errors)
    MAE = '{:.8f}'.format(MAE)
    print("[INFO] RangerForestRegressor MAE =", MAE)
    
    # Log the model performance (M01)
    print('[INFO] Logging the model performance to the database')
    cursor = con.cursor()
    statement = 'INSERT INTO logs VALUES (strftime("%%s","now"), "M01", %s, NULL, NULL)' % (MAE)
    cursor.execute(statement)    
    cursor.close()
    con.commit()
    con.close()
    
    # Save the random forest model
    RF_FILE = './models/' + COIN + '/RF-' + MAE + '.pkl'
    print("[INFO] Saving the RangerForestRegressor model to file:", RF_FILE)
    with open(RF_FILE, 'wb') as f:
        pickle.dump(rfr, f)
    
    # Finished
    print("[FINISHED] Successfully trained the model for", COIN)

else:
    
    # Error: missing command line arguments
    print("[ERROR] Missing command line arguments. Must specify coin name (e.g. BAT-USDC)")

