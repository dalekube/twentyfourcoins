#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collect current prices for supported coins from the Nomics API.
https://nomics.com/docs/#operation/getCurrenciesTicker

@author: Dale Kube (dkube@uwalumni.com)
"""

import json
import requests
from datetime import datetime
from db_connect import db_connect

TABLE_NAME = 'prices_current'

# Load the platform configuration
with open('../config.json') as f:
    config = json.load(f)

## DEVELOPMENT ONLY
## import os
## os.chdir('/home/dale/Downloads/GitHub/TwentyFourCoins/functions')

# Establish the database connection
# Create the initial table if it does not already exist
con = db_connect('../data/db.sqlite')
statement = 'CREATE TABLE IF NOT EXISTS %s (coin TEXT NOT NULL, time DATETIME NOT NULL, price FLOAT NOT NULL)' % TABLE_NAME
cursor = con.cursor()
cursor.execute(statement)

# Consider all supported coins
URL = 'https://api.nomics.com/v1/currencies/ticker?key=d0bafa2affe78db0f83d37cf6a27c20f8382efd5&ids='
coin_dict = {}
for COIN_NAME, COIN in config['SUPPORTED_COINS'].items():
    
    # Focus on the first three characters for the Nomics API
    COIN_FIRST_THREE = COIN[0:3]
    coin_dict[COIN_FIRST_THREE] = COIN
    URL = URL + COIN_FIRST_THREE + ','

# Retrieve the data from the API and extract the relevant fields from the JSON data
# Save the data into the database table
URL = URL[:-1]
response = requests.get(URL)
print(response.status_code)
json_data = json.loads(response.text)
for i in range(0,len(json_data)):
    coin = coin_dict[json_data[i]['id']]
    timestamp = json_data[i]['price_timestamp']
    timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S')
    price = float(json_data[i]['price'])
    statement = 'INSERT INTO %s VALUES ("%s", "%s", %s)' % (TABLE_NAME, coin, timestamp, price)
    cursor.execute(statement)

# Close the database connection
cursor.close()
con.commit()
con.close()
print('[FINISHED] Successfully collected current prices')
