#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train the model for BAT-USDC

@author: dale
"""

import os
import sys
import json

import pandas as pd
from datetime import datetime
import tensorflow as tf
from tensorflow import keras

# Check if the GPU is available
print("[INFO] GPU Configuration =", tf.config.list_physical_devices('GPU'))
print("[INFO] TensorFlow version =", tf.__version__)

# Load the configurations
with open('config.json') as f:
    config = json.load(f)

# Evaluate the command line parameters
# argv[1] = coin name (e.g. BAT-USDC)
# argv[2] = model object name (e.g. weights-BAT-USDC-0.0022.hdf5)
if len(sys.argv) != 3:
    
    # Error: missing command line arguments
    print("[ERROR] Missing command line arguments.")
    
else:
    
    COIN = sys.argv[1]
    assert COIN in config['SUPPORTED_COINS'], "[ERROR] " + COIN + " is not supported"
    DATA_DIR = './data/' + COIN
    
    # Load the data for the coin
    # Print the row count when finished
    COIN_CSV = DATA_DIR + '/' + COIN + '.csv'
    assert COIN in config['SUPPORTED_COINS'], "[ERROR] " + COIN + " is not supported"
    assert os.path.exists(COIN_CSV), "[ERROR] Unavailable data (.csv) for " + COIN
    df = pd.read_csv(COIN_CSV, low_memory=False)
    N_DF = len(df)
    assert N_DF > 0, "[ERROR] Zero rows in the data file (.csv) for " + COIN
    print("[INFO] Successfully read", N_DF, "records from file")
    
    # Load the pre-trained model object
    model = keras.models.load_model(sys.argv[2])
    
    # Make prediction with the latest observation closest to NOW()
    df['UTC_TIME'] = df.apply(lambda row: datetime.utcfromtimestamp(row['time']), axis=1)
    df.sort_values(by=['time'], inplace=True)
    df_predict = df.tail(1)
    p_time = df_predict.pop('UTC_TIME')
    p_time = str(p_time.tolist()[0])
    p_close = float(df_predict['close'])
    p_now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    print("[INFO] Current time = " + p_now)
    print("[INFO] Making forward-looking prediction from " + p_time)
    prediction = float(model.predict(df_predict))
    
    print("[INFO] Predicted price = " + str(prediction))
    EXPECTED_CHANGE = prediction-p_close
    print("[RESULT] The price is expected to change by " + str(round(EXPECTED_CHANGE,3)) + " dollars in the next 24 hours")
