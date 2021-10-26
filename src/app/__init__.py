#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 21:38:29 2020

@author: maximilianreihn
"""


from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

cors = CORS(app)


from src.app import routes


