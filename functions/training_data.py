#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retrieve the full training data set for the specified coin with
the secondary features.

@author: Dale Kube (dkube@uwalumni.com)
"""

import pandas as pd
from features.stock_spy import features_stock_spy

## DEVELOPMENT ONLY
## os.chdir('/home/dale/Downloads/GitHub/TwentyFourCoins/functions')

def training_data(con, config, COIN, inference=False):
    
    # Load the data for the coin
    # Print the row count when finished
    statement = 'SELECT * FROM prices WHERE coin = "%s"' % (COIN)
    df = pd.read_sql(statement, con)
    df['time'] = pd.to_datetime(df['time'])
    del df['coin']
    
    N_DF = len(df)
    assert N_DF > 0, '[ERROR] Zero rows in the collected data for ' + COIN
    print("[INFO] Successfully read", '{:,}'.format(N_DF), "rows from the database")
    
    # Add stock market features
    prices_spy = features_stock_spy(con)
    prices_spy.rename(columns={'time':'time_merge'}, inplace=True)
    df['time_merge'] = df['time'].dt.strftime('%Y-%m-%d')
    df['time_merge'] = pd.to_datetime(df['time_merge'])
    df = df.merge(prices_spy, on=['time_merge'], how='left')
    del df['time_merge'], df['stock_spy_time']
    
    # Calculate rolling average features
    df.sort_values(by=['time'], inplace=True)
    for i in range(int(config['MIN_MOV_AVG']), int(config['MAX_MOV_AVG']), int(config['INTERVAL_MOV_AVG'])):
        df['MA_close_'+str(i)] = df['close'].rolling(window=i, min_periods=1, center=False).mean()
    
    # Drop rows with na values and convert to float32
    df.fillna(0, inplace=True)
    
    # Sort and calculate the 24 hours forward closing price (288 time periods of five minutes)
    # 86400/300 = 288
    # Remove observations without a 24-hour price target
    if inference:
        df.sort_values(by=['time'], inplace=True)
    else:
        df.sort_values(by=['time'], inplace=True, ascending=False)
        df['PRICE_24'] = df['close'].shift(288)
        df = df[~pd.isnull(df['PRICE_24'])]
        del df['time']
    
    return df