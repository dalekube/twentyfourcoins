#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collect historical COIN prices for machine learning model training. Maintain
the historical data in the 'COINML/data' directory.

Example call: python3 collect-data.py BAT-USDC

    Parameters:
        COIN (string): The code for a COIN (e.g. BAT-USDC)

@author: Dale Kube (dkube@uwalumni.com)
"""

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

# Connect to the COINbase API
# API Docs: https://docs.pro.COINbase.com/
# Manage API Keys and Secrets: https://pro.COINbase.com/profile/api
products = public_client.get_products()

## DEVELOPMENT ONLY
## import os
## os.chdir('/home/dale/Downloads/GitHub/coinML')

# Create a database connection
from data.db_connect import db_connect
con = db_connect('./data/db.sqlite')

# Iterate over COINs
# Manage the COIN-specific data in the 'COINML/data' directory
for COIN in COIN_IDS:
    
    ## DEVELOPMENT ONLY
    ## COIN = 'BAT-USDC'
    
    # Print the product details in the JSON format
    print("[INFO] Starting the iteration for " + COIN)
    COIN_DETAILS = [x for x in products if x['id']==COIN][0]
    pprint(COIN_DETAILS)
    
    # Retreive the existing data for the coin
    statement = 'SELECT * FROM prices WHERE coin = "%s"' % (COIN)
    df = pd.read_sql(statement, con)
    
    # Create a list of possible dates between the specific range
    datelist = pd.date_range(START_DT_UTC, NOW_DT_UTC).tolist()
    datelist = [x.strftime('%Y-%m-%d') for x in datelist]
    if len(df) > 0:
        
        # Data cleansing and validation
        # Purge data for dates with incomplete, excessive, or duplicate records
        df['UTC_DAY'] = df.apply(lambda row: datetime.utcfromtimestamp(row['time']).strftime('%Y-%m-%d'), axis=1)
        day_counts = df['UTC_DAY'].value_counts()
        day_counts = day_counts[(day_counts<200) | (day_counts > 300)]
        day_list = day_counts.index.values.tolist()
        
        dups = df[df['time'].duplicated()]['UTC_DAY'].unique().tolist()
        [day_list.append(d) for d in dups]
        day_list = set(day_list)
        
        N_PURGE = len(day_list)
        print('[INFO] Purging existing prices for', str(N_PURGE), 'days')
        
        # Delete the bad price records in the database
        time_purge = df.loc[df['UTC_DAY'].isin(day_list),'time'].to_list()
        time_purge = tuple(time_purge)
        statement = 'DELETE FROM prices WHERE coin = "%s" AND time IN %s' % (COIN, time_purge)
        cursor = con.cursor()
        cursor.execute(statement)
        cursor.close()
        con.commit()
        
        # Identify existing UTC dates with good data
        # Recalculate prices for the current date to avoid intra-day gaps
        df = df[~df['UTC_DAY'].isin(day_list)]
        df = df.loc[df['UTC_DAY'] < datetime.utcnow().strftime('%Y-%m-%d')]
        exist_dates = set(df['UTC_DAY'])
        del df['UTC_DAY']
        datelist = [x for x in datelist if x not in exist_dates]
    
    # Iterate over the dates to collect new candles using the Coinbase API
    # Iteratively save the data after 10 dates have passed
    try:
        
        print('[INFO] Starting the API iterations with', len(datelist), 'total dates')
        for d in datelist:
            
            d_start = d + ' 00:05:00'
            d_end = d + ' 23:55:00'
            
            # Collect the historical prices in five minute intervals
            # https://docs.pro.COINbase.com/#get-historic-rates
            hist = public_client.get_product_historic_rates(COIN, start=d_start, end=d_end, granularity=300)
            hist = pd.DataFrame(hist, columns=df.columns[1:])
            hist.insert(loc=0, column='coin', value='BAT-USDC')
            N_HIST = len(hist)
            print('[INFO] Gathered', N_HIST, 'new price candles from the API for', d)
            
            #hist['UTC_DAY'] = hist.apply(lambda row: datetime.utcfromtimestamp(row['time']).strftime('%Y-%m-%d'), axis=1)
            #hist['UTC_DAY_FULL'] = hist.apply(lambda row: datetime.utcfromtimestamp(row['time']), axis=1)
            
            # Save the new candles to the database
            hist.to_sql('prices', con, if_exists='append', index=False)
            con.commit()
            
            # Sleep for one second to respect the API limits and avoid errors
            time.sleep(1)
    
    except KeyboardInterrupt:
        
        print("[INFO] Acknowledged the KeyboardInterrupt")
        print("[INFO] Shutting down the process.....")
        con.commit()
        con.close()
        sys.exit(0)


