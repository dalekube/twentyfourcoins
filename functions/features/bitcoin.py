#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov 13 21:52:05 2021

@author: dale
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retrieve the BTC price history. The price movements of non-BTC cryptocurrencies
often move with BTC, given it's major influence in the market.

DEPENDENCY: runs from within the train_models.py code.

@author: dale
"""

import pandas as pd

def features_bitcoin(con):
    
    TABLE_NAME = 'prices_coinbase'
    
    # Check if the table already exists
    cursor = con.cursor()
    statement = 'SELECT name FROM sqlite_master WHERE type="table" AND name="%s"' % TABLE_NAME
    cursor.execute(statement)    
    table_check = cursor.fetchall()
    cursor.close()
    assert len(table_check) == 1, '[ERROR] prices_coinbase table does not exist yet'
    
    # Gather all of the bitcoin prices
    statement = 'SELECT time, price FROM %s WHERE COIN="BTC-USD"' % TABLE_NAME
    all_prices = pd.read_sql(statement, con)
    all_prices['time'] = pd.to_datetime(all_prices['time'])
    all_prices.rename(columns={'time':'time_merge'}, inplace=True)
    
    all_prices['time_merge'] = all_prices['time_merge'].dt.strftime('%Y-%m-%d')
    all_prices = all_prices.groupby('time_merge')['price'].max().reset_index()
    all_prices['time_merge'] = pd.to_datetime(all_prices['time_merge'])
    all_prices.rename(columns={'price':'btc_price'}, inplace=True)
    
    print('[INFO] Finished gathering historical Bitcoin prices')
    return all_prices

