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
import numpy as np
from matplotlib import pyplot as plt
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split

# Check if the GPU is available
print("[INFO] GPU Configuration =", tf.config.list_physical_devices('GPU'))
print("[INFO] TensorFlow version =", tf.__version__)

# Load the configurations
with open('config.json') as f:
    config = json.load(f)

# Evaluate the command line parameters
# argv[1] = coin name (e.g. BAT-USDC)
if len(sys.argv) > 1:

    COIN = sys.argv[1]
    
    # Create the coin directory if necessary
    DATA_DIR = './data/' + COIN
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)
    
    # Load the data for the coin
    # Print the row count when finished
    COIN_CSV = DATA_DIR + '/' + COIN + '.csv'
    assert COIN in config['SUPPORTED_COINS'], "[ERROR] " + COIN + " is not supported"
    assert os.path.exists(COIN_CSV), "[ERROR] Unavailable data (.csv) for " + COIN
    df = pd.read_csv(COIN_CSV, low_memory=False)
    N_DF = len(df)
    assert N_DF > 0, "[ERROR] Zero rows in the data file (.csv) for " + COIN
    print("[INFO] Successfully read", N_DF, "records from file")
    
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
    
    # Separate the outcome variable (PRICE_24)
    price_24 = df.pop('PRICE_24')
    x_train, x_test, y_train, y_test = train_test_split(df, price_24, test_size=0.10)
    x_train = tf.convert_to_tensor(x_train)
    
    # Model architecture and layers
    model = keras.Sequential()
    model.add(keras.Input(shape=(df.shape[1],)))
    model.add(layers.Dense(300, kernel_initializer='normal', activation='relu'))
    model.add(layers.Dense(300, kernel_initializer='normal', activation='relu'))
    model.add(layers.Dense(1, kernel_initializer='normal'))
    
    # Compile and summarize the model
    model.compile(optimizer=keras.optimizers.Adam(lr=10e-6), loss='mean_squared_error')
    model.summary()
    
    # Learning rate scheduler to use varying learning rates
    # over the training cycle
    def scheduler(epoch, lr):
        if epoch < 5:
            return 10e-3
        elif epoch < 10:
            return 10e-5
        else:
            return 10e-7
    
    LRSchedule = keras.callbacks.LearningRateScheduler(scheduler)
    
    # Model checkpoint
    # Iteratively save the model weights after improvement
    model_file = './models/weights-' + COIN + '-{val_loss:.4f}.hdf5'
    ModelCheck = keras.callbacks.ModelCheckpoint(model_file, monitor='val_loss',\
    verbose=1, save_weights_only=False, mode='min', save_best_only=True)
    
    # Early stopping to avoid unnecessary computation and save time
    EarlyStop = keras.callbacks.EarlyStopping(monitor='val_loss', patience=3,\
    verbose=1, restore_best_weights=True)
    
    # Compile the callbacks into a single list
    callbacks = [LRSchedule, ModelCheck, EarlyStop]
    
    history = model.fit(x_train, y_train, epochs=100, verbose=1,
              callbacks=callbacks, validation_data=(x_test, y_test), shuffle=True)
    
    # Visualize the model performance over the epochs
    # Exclude the first five epochs
    hist = history.history
    hist = {k: hist[k][5:] for k in hist}
    plt.plot(hist['loss'])
    plt.plot(hist['val_loss'])
    plt.title('model loss (MSE)')
    plt.ylabel('MSE')
    plt.xlabel('epoch')
    plt.legend(['train', 'val'], loc='upper left')
    plt.show()
    
    # Finished
    print("[FINISHED] Successfully trained the model for", COIN)

else:
    
    # Error: missing command line arguments
    print("[ERROR] Missing command line arguments. Must specify coin name (e.g. BAT-USDC)")

