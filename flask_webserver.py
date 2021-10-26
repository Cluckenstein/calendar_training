#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 21:17:49 2020

@author: maximilianreihn
"""


from src.app import app 


app.run(host = '0.0.0.0', port = 80, debug = True)