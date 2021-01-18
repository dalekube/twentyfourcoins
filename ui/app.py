#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web application.

@author: Dale Kube (dkube@uwalumni.com)
"""

import sys
import json
from flask import Flask, render_template, jsonify, request
from flask_fontawesome import FontAwesome

app = Flask(__name__, static_url_path='')
fa = FontAwesome(app)
app.secret_key = 'Bella123'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Create a database connection
sys.path.append('..')

# Import functions
from functions.price_history import collect_prices
from functions.predict_price import predict_price

# Load the platform configuration
with open('../config.json') as f:
    config = json.load(f)

# Home page
@app.route('/', methods=['GET'])
def index():
    
    return render_template(
            'index.html',
            SUPPORTED_COINS = config['SUPPORTED_COINS']
            )

# Collect price history
@app.route('/price_history', methods=['GET'])
def price_history():
    '''Execute the function to collect data from the Coinbase API
    and update the 'prices' table in the SQLite3 database
    '''
    
    response = collect_prices(config)
    response = jsonify(success=response)
    
    return response

# Collect price prediction
@app.route('/price_prediction', methods=['POST'])
def price_prediction():
    '''Get the price prediction for a specific coin
    '''
    
    COIN = request.get_json()['COIN']
    response = predict_price(config, COIN)     
    return jsonify(response)
    