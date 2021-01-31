#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clear the logs and start over

@author: Dale Kube (dkube@uwalumni.com)
"""

from db_connect import db_connect
con = db_connect('../data/db.sqlite')

# Clear all of the logs and start over
statement = "DELETE FROM logs"
cursor = con.cursor()
cursor.execute(statement)
cursor.close()
con.close()
