#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 21:40:35 2020

@author: maximilianreihn
"""

from flask import render_template, request, redirect, Response, send_from_directory, send_file
from src.app import app
from src.worker.worker_functions import get_scheduled, provide_calender_file
import requests
import json
import os 

@app.route('/update_calender/1VItIaXahzWFOgy5PIowr22G', methods=['GET', 'POST'])
@app.route('/update_calender/1VItIaXahzWFOgy5PIowr22G/', methods=['GET', 'POST'])
def update():
    """
    Route to create new calendar from current data and then send file forward to client.
    Returns:
        file : .ics file in which the past 7 and future 14 days are marked
    """

    workouts, _, summary = get_scheduled()
    calendar_file_path = provide_calender_file(workouts, summary)

    return send_file('calendar_folder/'+calendar_file_path)

