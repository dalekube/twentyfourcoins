#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web application for TwentyFourCoins

@author: Dale Kube (dkube@uwalumni.com)
"""

import sys
import json
from flask import Flask, render_template, jsonify, request, redirect
from flask_fontawesome import FontAwesome

# Load the platform configuration
with open('../config.json') as f:
    config = json.load(f)

app = Flask(__name__, static_url_path='')
fa = FontAwesome(app)
master_password = config['MASTER_PASSCODE']
app.secret_key = master_password
valid_passcode = False

# Create a database connection
sys.path.append('..')

# Import functions for the UI
from functions.predict_price import predict_price

# Home page
@app.route('/', methods=['GET'])
def index():
    
    return render_template(
            'index.html',
            SUPPORTED_COINS = config['SUPPORTED_COINS'].items()
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
    
    global valid_passcode
    passcode = request.get_json()['passcode']
    print('[INFO] Received passcode from the UI')
    if passcode == master_password:
        valid_passcode = True
        print('[INFO] Successfully validated the passcode')
        return jsonify(success=True)
    else:
        valid_passcode = False
        print('[ERROR] Invalid passcode')
        return jsonify(success=False), 401

# Collect price prediction
@app.route('/price_prediction', methods=['POST'])
def price_prediction():
    '''Get the price prediction for a specific coin
    '''
    global valid_passcode
    if valid_passcode:
        COIN = request.get_json()['COIN']
        try:
            response = predict_price(config, COIN)
        except:
            return jsonify(success=False), 500
        
        return jsonify(response)
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

if __name__ == '__main__':
    context = ('cert.pem', 'key.pem')#certificate and key files
    app.run(debug=True, ssl_context=context)