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

from bokeh.plotting import figure
from bokeh.embed import json_item
from bokeh.models import NumeralTickFormatter, Legend, HoverTool

from datetime import datetime
import pandas as pd

## DEVELOPMENT ONLY
## os.chdir('/home/dale/Downloads/GitHub/TwentyFourCoins/')

# Load the platform configuration
with open('config.json') as f:
    config = json.load(f)
APPLICATION_VERSION = config['APPLICATION_VERSION']

# Define the Flask application object
app = Flask(__name__, static_url_path='')
fa = FontAwesome(app)
app.secret_key = config['MASTER_PASSCODE']

# Session management cookie configuration
app.config['SESSION_COOKIE_NAME'] = 'tfc-tmp-session-mgmt'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_PERMANENT'] = False 

from functions.db_connect import db_connect
emoji_map = {"emojiRocket":"E01", "emojiDeath":"E02"}

# Home
@app.route('/', methods=['GET'])
def index():
    
    # Retrieve the latest predictions for all supported coins
    SUPPORTED_COINS = config['SUPPORTED_COINS'].items()
    SUPPORTED_WINDOWS = config['SUPPORTED_WINDOWS']
    COIN_STATS = {}
    for COIN in config['SUPPORTED_COINS'].values():
        for WINDOW in config['SUPPORTED_WINDOWS']:
            INSTANCE = COIN + '-' + WINDOW
            JSON_PATH = 'models/' + COIN + '/' + WINDOW + '/' + 'latest.json'
            assert os.path.exists(JSON_PATH), '[ERROR] The latest.json file does not exist for ' + COIN
            with open(JSON_PATH) as f:
                COIN_STATS[INSTANCE] = json.load(f)
    
    UPDATE_TIME = datetime.now().astimezone().strftime('%Y-%m-%d %I:%M:%S %p %Z')
    
    return render_template(
            'index.html',
            SUPPORTED_COINS = SUPPORTED_COINS,
            SUPPORTED_WINDOWS = SUPPORTED_WINDOWS,
            COIN_STATS = COIN_STATS,
            UPDATE_TIME = UPDATE_TIME,
            APPLICATION_VERSION = APPLICATION_VERSION
            )
    
# About
@app.route('/about', methods=['GET'])
def about():
    
    return render_template(
            'about.html', 
            APPLICATION_VERSION = APPLICATION_VERSION
            )

# Error route for redirects
@app.route('/error', methods=['GET'])
def error_page():
    msg = request.args.get('msg')
    if msg is None:
        msg = ''
    
    return render_template(
            'error.html', 
            ERROR = msg,
            APPLICATION_VERSION = APPLICATION_VERSION
            )

# Collect price prediction
@app.route('/price_prediction', methods=['POST'])
def price_prediction():
    '''Retrieve the latest price prediction
    '''
    response = request.get_json()
    COIN = response['COIN']
    WINDOW = response['WINDOW']
    
    try:
        
        # Load the latest predictions and performance statistics
        JSON_PATH = 'models/' + COIN + '/' + WINDOW + '/latest.json'
        assert os.path.exists(JSON_PATH), '[ERROR] The latest.json file does not exist at' + JSON_PATH
        with open(JSON_PATH) as f:
            latest_json = json.load(f)
        
        # Retrieve the data for the charts
        JSON_PATH = 'models/' + COIN + '/' + WINDOW + '/charts.json'
        assert os.path.exists(JSON_PATH), '[ERROR] The charts.json file does not exist at' + JSON_PATH
        with open(JSON_PATH) as f:
            chart_data = json.load(f)
        
        actuals = json.loads(chart_data['actuals'])
        actuals_time = list(actuals['time'].values())
        actuals_values = list(actuals['price'].values())
        df_actuals = pd.DataFrame({'time':actuals_time, 'values':actuals_values})
        df_actuals['time'] = pd.to_datetime(df_actuals['time'])
        
        preds = json.loads(chart_data['predictions'])
        preds_time = list(preds['time'].values())
        preds_values = list(preds['pred'].values())
        df_preds = pd.DataFrame({'time':preds_time, 'values':preds_values})
        df_preds['time'] = pd.to_datetime(df_preds['time'])
        
        # Define the chart figure
        fig = figure(x_axis_type='datetime', tools="pan,box_select,reset,wheel_zoom", active_drag="pan")
        fig.add_layout(Legend(location=(50, 0), orientation="horizontal"), "above")
        fig.line(df_actuals['time'], df_actuals['values'], color='#4488EE', line_width=2, legend_label='Actuals')
        fig.line(df_preds['time'], df_preds['values'], color='black', line_width=2, legend_label='Predictions')
        fig.width = 475
        fig.height = 300
        fig.toolbar.logo = None
        fig.background_fill_color = None
        fig.border_fill_color = None
        fig.legend.background_fill_color = None
        fig.legend.border_line_color = None
        fig.legend.padding = 0
        fig.legend.margin = 0
        fig.legend.spacing = 10
        fig.legend.label_text_font_size = '16pt'
        fig.legend.label_text_font = 'Calibri'
        fig.legend.label_text_color = 'black'
        fig.yaxis[0].formatter = NumeralTickFormatter(format="$0,.00")
        hover = HoverTool(tooltips=[("Date", "$x{%F %T %Z}"),("Price", "$y{$0.0000}")], formatters={"$x": 'datetime'})
        fig.add_tools(hover)
    
    except:
        return jsonify(success=False), 500
    
    return jsonify(stats=latest_json, charts=json_item(fig, 'mainChart'))

@app.route('/emoji_load', methods=['GET'])
def emoji_load():
    '''Load the existing values for a coin
    '''
    
    COIN = request.args.get('coin')
    WINDOW = int(request.args.get('window'))
    con = db_connect('./data/db.sqlite')
    
    statement = 'SELECT UTC_TIME, EMOJI FROM emojis \
    WHERE WINDOW = %s AND COIN="%s"' % (WINDOW, COIN)
    df = pd.read_sql(statement, con)
    emoji_cnts = df['EMOJI'].value_counts()
    for v in emoji_map.values():
        if not v in emoji_cnts.index:
            emoji_cnts[v] = 0
    
    ROCKET_TOTAL = int(emoji_cnts['E01'])
    DEATH_TOTAL = int(emoji_cnts['E02'])
    con.close()
    
    return jsonify(totals=[ROCKET_TOTAL, DEATH_TOTAL], success=True)

@app.route('/emoji_pump', methods=['GET'])
def emoji_pump():
    '''Increase the value of the corresponding emoji
    '''
    
    pump_id = request.args.get('id')
    COIN = request.args.get('coin')
    WINDOW = int(request.args.get('window'))
    EMOJI = emoji_map[pump_id]
    
    con = db_connect('./data/db.sqlite')
    cursor = con.cursor()
    statement = 'INSERT INTO emojis \
    VALUES (strftime("%%Y-%%m-%%d %%H:%%M:%%S", datetime("now")), \
    "%s", %s, "%s")' % (EMOJI, WINDOW, COIN)
    cursor.execute(statement)    
    cursor.close()
    con.commit()
    con.close()
    
    return jsonify(success=True), 200
    

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

