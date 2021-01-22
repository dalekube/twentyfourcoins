#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web application for TwentyFourCoins

@author: Dale Kube (dkube@uwalumni.com)
"""

import os
import json
from flask import Flask, render_template, jsonify, request, redirect, session
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

# Home page
@app.route('/', methods=['GET'])
def index():
    
    return render_template(
            'index.html',
            SUPPORTED_COINS = config['SUPPORTED_COINS'].items(),
            PREMIUM_COINS = config['PREMIUM_COINS']
            )

# Error route for redirects
@app.route('/error', methods=['GET'])
def error_page():
    msg = request.args.get('msg')
    if msg is None:
        msg = ''
    return render_template('error.html', ERROR = msg)

# Validate the passcode
@app.route('/validate_passcode', methods=['POST'])
def validate_passcode():
    
    session['passcode'] = request.get_json()['passcode']
    print('[INFO] Received passcode from the UI')
    if session['passcode'] in access_passcodes:
        print('[INFO] Successfully validated the passcode')
        return jsonify(success=True)
    else:
        print('[ERROR] Invalid passcode')
        return jsonify(success=False), 401

# Collect price prediction
@app.route('/price_prediction', methods=['POST'])
def price_prediction():
    '''Retrieve the latest price prediction
    '''
    if session['passcode'] in access_passcodes:
        COIN = request.get_json()['COIN']
        try:
            JSON_PATH = 'models/' + COIN + '/' + 'latest.json'
            assert os.path.exists(JSON_PATH), '[ERROR] The latest.json file does not exist for ' + COIN
            with open(JSON_PATH) as f:
                latest_json = json.load(f)
            
        except:
            return jsonify(success=False), 500
        
        return jsonify(json.dumps(latest_json))

    else:
        return jsonify(success=False), 401

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

