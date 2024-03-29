#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web server gateway interface for Gunicorn

@author: Dale Kube (dkube@uwalumni.com)
"""

from twentyfourcoins import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
    