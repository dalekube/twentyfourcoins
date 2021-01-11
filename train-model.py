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
import sys
import json

import pandas as pd
import numpy as np

#from matplotlib import pyplot as plt
#import tensorflow as tf
#from tensorflow import keras
#from tensorflow.keras import layers

from skranger.ensemble import RangerForestRegressor
import pickle

## Check if the GPU is available
#print("[INFO] GPU Configuration =", tf.config.list_physical_devices('GPU'))
#print("[INFO] TensorFlow version =", tf.__version__)

## DEVELOPMENT ONLY
## os.chdir('/home/dale/Downloads/GitHub/coinML')

# Load the configurations
with open('config.json') as f:
    config = json.load(f)

# Evaluate the command line parameters
# argv[1] = coin name (e.g. BAT-USDC)
if len(sys.argv) > 1:

    COIN = sys.argv[1]
    
    ## DEVELOPMENT ONLY
    ## COIN = 'BAT-USDC'
    
    # Create the coin directory if necessary
    DATA_DIR = './data/'
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)
    
    # Load the data for the coin
    # Print the row count when finished
    COIN_CSV = DATA_DIR + COIN + '.csv'
    assert COIN in config['SUPPORTED_COINS'], "[ERROR] " + COIN + " is not supported"
    assert os.path.exists(COIN_CSV), "[ERROR] Unavailable data (.csv) for " + COIN
    df = pd.read_csv(COIN_CSV, low_memory=False)
    N_DF = len(df)
    assert N_DF > 0, "[ERROR] Zero rows in the data file (.csv) for " + COIN
    print("[INFO] Successfully read", '{:,}'.format(N_DF), "records from file")
    
    # Calculate rolling average features
    df.sort_values(by=['time'], inplace=True)
    for i in range(10, 2000, 10):
        df['MA'+str(i)] = df['close'].rolling(window=i).mean()
    
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
    # Use the latest 1,000 observations for the test split
    price_24 = df.pop('PRICE_24')
    N_TEST = 1000
    N_DF = len(df)
    
    x_train = df[0:N_DF-N_TEST]
    y_train = price_24[0:N_DF-N_TEST]
    
    x_test = df[-N_TEST:]
    y_test = price_24[-N_TEST:]
    
    # Train the random forest model
    print("[INFO] Training the RangerForestRegressor")
    rfr = RangerForestRegressor(n_estimators=100)
    rfr.fit(x_train, y_train)
    
    # Estimate the performance upon the test data
    predictions = rfr.predict(x_test)
    errors = np.square(predictions - y_test)
    MSE = np.mean(errors)
    MSE = '{:.4f}'.format(MSE)
    print("[INFO] RangerForestRegressor MSE =", MSE)
    
    # Save the random forest model
    print("[INFO] Saving the RangerForestRegressor model to a pickle file")
    RF_FILE = './models/' + COIN + '/RF-' + MSE + '.pkl'
    with open(RF_FILE, 'wb') as f:
        pickle.dump(rfr, f)
    
#    # Model architecture and layers
#    model = keras.Sequential()
#    model.add(keras.Input(shape=(df.shape[1],)))
#    model.add(layers.Dense(300, kernel_initializer='normal', activation='relu'))
#    model.add(layers.Dense(300, kernel_initializer='normal', activation='relu'))
#    model.add(layers.Dense(1, kernel_initializer='normal'))
#    
#    # Compile and summarize the model
#    model.compile(optimizer=keras.optimizers.Adam(lr=10e-3), loss='mean_squared_error')
#    model.summary()
#    
#    # Model checkpoint
#    # Iteratively save the model weights after improvement
#    MODEL_DIR = './models/' + COIN + '/'
#    MODEL_FILE = MODEL_DIR + 'weights-' + COIN + '-{val_loss:.4f}.hdf5'
#    ModelCheck = keras.callbacks.ModelCheckpoint(MODEL_FILE, monitor='val_loss',\
#    verbose=1, save_weights_only=False, mode='min', save_best_only=True)
#    
#    # Early stopping to avoid unnecessary computation and save time
#    EarlyStop = keras.callbacks.EarlyStopping(monitor='val_loss', patience=5,\
#    verbose=1, restore_best_weights=True)
#    
#    # Compile the callbacks into a single list
#    callbacks = [ModelCheck, EarlyStop]
#    
#    history = model.fit(x_train, y_train, epochs=2, verbose=1,
#              callbacks=callbacks, validation_data=(x_test, y_test), shuffle=True)
#    
#    # Visualize the model performance over the epochs
#    # Exclude the first five epochs
#    hist = history.history
#    hist = {k: hist[k][5:] for k in hist}
#    plt.plot(hist['loss'])
#    plt.plot(hist['val_loss'])
#    plt.title('model loss (MSE)')
#    plt.ylabel('MSE')
#    plt.xlabel('epoch')
#    plt.legend(['train', 'val'], loc='upper left')
#    plt.show()
#    
#    # Save the training history
#    HISTORY_FILE = './models/' + COIN + '/history-' + COIN + '.json'
#    json.dump(hist, open(HISTORY_FILE, 'w'))
    
    # Finished
    print("[FINISHED] Successfully trained the model for", COIN)

else:
    
    # Error: missing command line arguments
    print("[ERROR] Missing command line arguments. Must specify coin name (e.g. BAT-USDC)")

