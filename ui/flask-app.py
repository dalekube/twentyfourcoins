#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web application.

@author: Dale Kube (dkube@uwalumni.com)
"""

import sys
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = 'Bella123'

# Create a database connection
sys.path.append('..')
from functions.db_connect import db_connect
con = db_connect('../data/db.sqlite')

@app.route('/')
def index():
    
    return render_template('index.html')