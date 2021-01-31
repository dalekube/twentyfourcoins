#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web application for TwentyFourCoins

@author: Dale Kube (dkube@uwalumni.com)
"""

import os
import json
from flask import Flask, render_template, jsonify, request, redirect
from flask_fontawesome import FontAwesome

# Load the platform configuration
with open('config.json') as f:
    config = json.load(f)

# Define the Flask application object
app = Flask(__name__, static_url_path='')
fa = FontAwesome(app)
master_passcode = config['MASTER_PASSCODE']
access_passcodes = config['TEMPORARY_PASSCODES']
access_passcodes.append(master_passcode)
app.secret_key = master_passcode

# Session management cookie configuration
app.config['SESSION_COOKIE_NAME'] = 'tfc-tmp-session-mgmt'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_PERMANENT'] = False 

# Establish database connection
from functions.db_connect import db_connect

# Save user activity in logs
def log_activity(activity, route, coin=None):
    cnx = db_connect('./data/db.sqlite')
    cursorx = cnx.cursor()
    statement = 'INSERT INTO logs VALUES (strftime("%%s","now"), "%s", NULL, NULL, NULL, "%s", "%s")' % (activity, route, coin)
    cursorx.execute(statement)    
    cursorx.close()
    cnx.commit()

# Home
@app.route('/', methods=['GET'])
def index():
    
    # Retrieve the latest predictions for all supported coins
    SUPPORTED_COINS = config['SUPPORTED_COINS'].items()
    COIN_STATS = {}
    for COIN in config['SUPPORTED_COINS'].values():
        JSON_PATH = 'models/' + COIN + '/' + 'latest.json'
        assert os.path.exists(JSON_PATH), '[ERROR] The latest.json file does not exist for ' + COIN
        with open(JSON_PATH) as f:
            COIN_STATS[COIN] = json.load(f)
    
    # Log the user activity
    # A01 = User visit
    log_activity("A01", "/")
    
    return render_template(
            'index.html',
            SUPPORTED_COINS = SUPPORTED_COINS,
            COIN_STATS = COIN_STATS,
            PREMIUM_COINS = config['PREMIUM_COINS']
            )
    
# About
@app.route('/about', methods=['GET'])
def about():
    
    # Log the user activity
    # A01 = User visit
    log_activity("A01", "/about")
    
    return render_template('about.html')

# Error route for redirects
@app.route('/error', methods=['GET'])
def error_page():
    msg = request.args.get('msg')
    if msg is None:
        msg = ''
    
    # Log the user activity
    # A01 = User visit
    log_activity("A01", "/error")
    
    return render_template('error.html', ERROR = msg)

# Collect price prediction
@app.route('/price_prediction', methods=['POST'])
def price_prediction():
    '''Retrieve the latest price prediction
    '''
    response = request.get_json()
    COIN = response['COIN']
    CLICK = response['CLICK']
    
    # Avoid the logging for the view of the default coin
    if CLICK == 'Y':
        # Log the user activity
        # A02 = Viewed price prediction
        log_activity("A02", "/price_prediction", COIN)
    
    try:
        JSON_PATH = 'models/' + COIN + '/' + 'latest.json'
        assert os.path.exists(JSON_PATH), '[ERROR] The latest.json file does not exist for ' + COIN
        with open(JSON_PATH) as f:
            latest_json = json.load(f)
    
    except:
        return jsonify(success=False), 500
    
    return jsonify(json.dumps(latest_json))

# Error handling
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(406)
@app.errorhandler(500)
@app.errorhandler(502)
@app.errorhandler(503)
def page_not_found(e):
    return redirect('/error?msg=' + str(e))

