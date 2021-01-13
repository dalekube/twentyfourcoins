#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create a connection to the platform SQLite3 database.

@author: Dale Kube (dkube@uwalumni.com)
"""

import os
import sqlite3
from sqlite3 import Error

def db_connect(db_file):
    """ create a database connection """
    con = None
    try:
        
        con = sqlite3.connect(db_file, isolation_level=None)
        if os.path.exists(db_file):
            
            print("[INFO] Successfully connected to the database", db_file)
            
        else:
            
            print("[INFO] Successfully created the database file:", db_file)
        
        print("[INFO] SQLite3 version =", sqlite3.version)
        return(con)
        
    except Error as e:
        
        return(e)