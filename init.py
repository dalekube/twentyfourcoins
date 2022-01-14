#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from subprocess import call

print("Reminder, you should have already installed the required Python modules \
      using the command 'pip3 install -r requirements.txt'")

# Check if the database file exists
DB_FILE_PATH = './data/db.sqlite'
assert os.path.isfile(DB_FILE_PATH), 'Database file does not exist: ' + DB_FILE_PATH

# Execute sequential core functions
call(['python3','./functions/api_collect_prices_coinbase.py'])
call(['python3','./functions/train_models.py'])
call(['python3','./functions/predict_prices.py'])

print("The initialization process is finished!")