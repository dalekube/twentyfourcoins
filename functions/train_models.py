#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train the models for supported coins.

@author: Dale Kube (dkube@uwalumni.com)
"""

import os
import gc
import json
import pandas as pd
import numpy as np
import glob
import random

from skranger.ensemble import RangerForestRegressor
from sklearn.linear_model import LinearRegression
import bz2
import _pickle as cPickle

os.chdir(os.path.dirname(os.path.realpath(__file__)))
gc.enable()
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

# Iterate over the supported coins
for COIN in config['SUPPORTED_COINS'].values():
    
    for w in config['SUPPORTED_WINDOWS']:
        
        WINDOW = int(w)
        print('[INFO] Starting the iteration for', COIN)
        print('[INFO] Time window (5 minute bundles) =', WINDOW)
        df = training_data(con, config, COIN, WINDOW, prices_spy, prices_btc)
        
        # Split the training and testing data
        # Use a combinatorial approach, with samples from recent days and random days across history
        y_price = df.pop('Y_PRICE')
        N_TEST_RECENT = 3000
        N_TEST_RANDOM = 3000
        N_DF = len(df)
        
        # Sample recent days
        x_train = df[N_TEST_RECENT:].reset_index(drop=True)
        y_train = y_price[N_TEST_RECENT:].reset_index(drop=True)
        
        x_test_recent = df[:N_TEST_RECENT]
        y_test_recent = y_price[:N_TEST_RECENT]
        gc.enable()
        del df
        
        # Random sample from the rest of the training data
        random.seed(1000)
        idx = random.sample(range(0,len(x_train)), N_TEST_RANDOM)
        x_test_random = x_train.iloc[idx,:]
        y_test_random = y_train.iloc[idx]
        
        x_test = pd.concat([x_test_recent, x_test_random])
        y_test = pd.concat([y_test_recent, y_test_random])
        
        x_train.drop(idx, inplace=True)
        y_train.drop(idx, inplace=True)
        
        # Train  and evaluate the random forest model
        rfr = RangerForestRegressor(n_estimators=31, oob_error=False, sample_fraction=[0.25])
        rfr.fit(x_train, y_train)
        rf_preds = rfr.predict(x_test)
        
        # Use the simple moving average as an option
        # Evaluate multiple moving averages to find the best performing range
        avgs_range = range(int(config['MIN_MOV_AVG']), int(config['MAX_MOV_AVG']), int(config['INTERVAL_MOV_AVG']))
        avgs_mae = [np.mean(abs(x_test['MovingAverage_price_'+str(g)] - y_test)) for g in avgs_range]
        best_mov_avg = avgs_range[avgs_mae.index(min(avgs_mae))]
        mov_avg_col = 'MovingAverage_price_'+str(best_mov_avg)
        print('[INFO] Using', mov_avg_col, 'as the best moving average')
        mov_avg = x_test[mov_avg_col]
        
        # Linear regression fit
        lr = LinearRegression(normalize=True).fit(x_train, y_train)
        lr_preds = lr.predict(x_test)
        
        # Evaluate all models and ensembles to achieve optimal performance
        # Ensemble the predictions from both models
        ensemble_preds_all = (rf_preds+mov_avg+lr_preds)/3.0
        ensemble_preds_rf_avg = (rf_preds+mov_avg)/2.0
        ensemble_preds_rf_lr = (rf_preds+lr_preds)/2.0
        ensemble_preds_avg_lr = (mov_avg+lr_preds)/2.0
        prediction_sets = {
                'RangerForestRegressor': rf_preds,
                'MovingAverage':mov_avg,
                'LinearRegression':lr_preds,
                'Ensemble_ALL':ensemble_preds_all,
                'Ensemble_RF_AVG': ensemble_preds_rf_avg,
                'Ensemble_RF_LR': ensemble_preds_rf_lr,
                'Ensemble_AVG_LR': ensemble_preds_avg_lr,
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
        statement = 'INSERT INTO model_performance \
        VALUES (strftime("%%Y-%%m-%%d %%H:%%M:%%S", datetime("now")), \
        %s, %s, "%s", %s)' % (MAE, MAPE, COIN, WINDOW)
        cursor.execute(statement)    
        cursor.close()
        con.commit()
        
        # Create the model directory if it doesn't already exist
        MODEL_DIR_COIN = '../models/' + COIN
        MODEL_DIR =  MODEL_DIR_COIN + '/' + str(WINDOW)
        if not os.path.exists(MODEL_DIR_COIN):
            os.mkdir(MODEL_DIR_COIN)
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
            cPickle.dump([rfr, lr, best_model, mov_avg_col], f)


# Close the database connection
con.close()
print('[INFO] Finished training all models')