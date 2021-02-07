#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb  6 22:15:57 2021

@author: dale
"""

# Append closing prices and volumes for correlative coins
# Correlative data helps the model to understand confounding market trends
correlations = config['MODEL_CORRELATIONS']['BAT-USDC']
close_cols = []
for i in correlations:
        # Load the data for the coin
        # Print the row count when finished
        print('[INFO] Reading historical data for correlative coin', i)
        statement = 'SELECT time, close, volume FROM prices WHERE coin = "%s"' % i
        df_cor = pd.read_sql(statement, con)
        N_DF_COR = len(df_cor)
        assert N_DF_COR > 0, '[ERROR] Missing prices for correlative coin'
        print('[INFO] Successfully read', '{:,}'.format(N_DF_COR), 'rows from the database')
        
        print('[INFO] Merging the correlative prices and volumes')
        cols_cor = [j + '-' + i for j in df_cor.columns if j != 'time']
        close_cols = close_cols + [cols_cor[0]]
        df_cor.columns = ['time'] + cols_cor
        df = df.merge(df_cor,on='time',how='left')
        assert N_DF == len(df), '[ERROR] Unintended row expansion from correlative data merger'