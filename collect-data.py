#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collect historical coin prices for machine learning model training. Maintain
the historical data in the 'coinML/data' directory.

Example call: python3 collect-data.py BAT-USDC

    Parameters:
        Coin (string): The code for a coin (e.g. BAT-USDC)

@author: Dale Kube (dkube@uwalumni.com)
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime
from pprint import pprint

print("[INFO] Establishing the Coinbase API connection")
import cbpro
public_client = cbpro.PublicClient()

COIN_IDS = ['BAT-USDC']
START_DT_UTC = '2019-01-01 00:00:00'
NOW_DT_UTC = datetime.utcnow().strftime('%Y-%m-%d')
DATA_DIR = './data/'

# Connect to the Coinbase API
# API Docs: https://docs.pro.coinbase.com/
# Manage API Keys and Secrets: https://pro.coinbase.com/profile/api
products = public_client.get_products()

# Function to save the data to file during the iterations
def save_file(df, COIN_CSV):
    print('[INFO] Saving the data to', os.path.abspath(COIN_CSV))
    df.drop_duplicates(subset=['time'], inplace=True)
    df.to_csv(COIN_CSV, index=False)

# Iterate over coins
# Manage the coin-specific data in the 'coinML/data' directory
for coin in COIN_IDS:
    
    # Print the product details in the JSON format
    print("[INFO] Starting the iteration for " + coin)
    COIN_DETAILS = [x for x in products if x['id']==coin][0]
    pprint(COIN_DETAILS)
    
    # Create the primary data directory if it does not exist
    if not os.path.exists(DATA_DIR):
        print("[INFO] Creating the data directory from scratch")
        os.mkdir(DATA_DIR)
    
    COIN_CSV = coin + '.csv'
    os.chdir(DATA_DIR)
    if os.path.isfile(COIN_CSV):
        print('[INFO] Reading the existing data set for', coin)
        df = pd.read_csv(COIN_CSV, low_memory=False)
    else:
        print('[INFO] Creating the data set from scratch for', coin)
        df = pd.DataFrame(columns=['time','low','high','open','close','volume'])
        df.to_csv(COIN_CSV, index=False)
        
    # Create a list of possible dates between the specific range
    datelist = pd.date_range(START_DT_UTC, NOW_DT_UTC).tolist()
    datelist = [x.strftime('%Y-%m-%d') for x in datelist]
    if len(df) > 0:
        
        # Purge data for dates with incomplete records
        df['UTC_DAY'] = df.apply(lambda row: datetime.utcfromtimestamp(row['time']).strftime('%Y-%m-%d'), axis=1)
        day_counts = df['UTC_DAY'].value_counts()
        day_counts = day_counts[day_counts<200]
        N_PURGE = len(day_counts)
        print("[INFO] Purging data for " + str(N_PURGE) + " incomplete days previously saved")
        df = df[~df['UTC_DAY'].isin(day_counts.index.values)]
        
        # Identify UTC dates without data
        # Recalculate prices for the current date to avoid intra-day gaps
        df = df.loc[df['UTC_DAY'] < datetime.utcnow().strftime('%Y-%m-%d')]
        exist_dates = set(df['UTC_DAY'])
        del df['UTC_DAY']
        datelist = [x for x in datelist if x not in exist_dates]
    
    # Iterate over the dates to collect new candles using the Coinbase API
    # Iteratively save the data after 10 dates have passed
    FILE_COUNT = 0
    N_DATES = len(datelist)
    try:
        
        for d in datelist:
            
            print('[INFO] Collecting', coin, 'prices for date:', d)
            d_start = d + ' 00:00:00'
            d_end = d + ' 24:00:00'
        
            # Collect the historical prices in five minute intervals
            # https://docs.pro.coinbase.com/#get-historic-rates
            hist = public_client.get_product_historic_rates(coin, start=d_start, end=d_end, granularity=300)
            for h in hist:
                new_row = pd.Series(h, index=df.columns)
                df = df.append(new_row, ignore_index=True)
            N_HIST = len(hist)
            print("[INFO] Appended", N_HIST, "new price candles")
            
            # Iteratively save the data
            FILE_COUNT += 1
            if FILE_COUNT % 10 == 0 or FILE_COUNT == N_DATES:
                save_file(df, COIN_CSV)
            
            # Sleep for one second to respect the API limits and avoid errors
            time.sleep(1)
    
    except KeyboardInterrupt:
        
        print("[INFO] Acknowledged the KeyboardInterrupt")
        save_file(df, COIN_CSV)
        print("[INFO] Shutting down the process.....")
        sys.exit(0)


