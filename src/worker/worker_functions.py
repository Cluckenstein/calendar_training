#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 21:40:35 2020

@author: maximilianreihn
"""

import requests
from icalendar import Calendar, Event
from datetime import datetime,timedelta,date
import json
import string
import random
import os 
from sys import platform
from io import StringIO
from html.parser import HTMLParser
import numpy as np


def get_scheduled(base_url = 'https://whats.todaysplan.com.au', offset = 0, max_count = 70, include_completed = True):
    """
    Here the post request is send to get the scheduled workouts and relevant details
    Args:
        base_url (str, optional): Default post request URL . Defaults to 'https://whats.todaysplan.com.au'.
        offset (int, optional): Relevant only to post request. Defaults to 0.
        max_count (int, optional): Max number of workouts returned from post request. Defaults to 50.

    Returns:
        list : list of workouts in the format seen down below 
        dict : plain json response from post request with everything received
    """
    # get bearer token by using username and password 
    token, client_id = post_auth()

    # use response to build header for post request
    header = {'Authorization' : 'Bearer %s'%(token), 
            'Content-Type' : 'application/json',
            'Api-Key': client_id,
            'tp-nodecorate':   'true'}

    # define time frame in which to search for acitvities

    #from the monday of the week before until 2 week in advance
    today = datetime(datetime.now().year, datetime.now().month, datetime.now().day)
    monday_before = today + timedelta(days=-today.weekday(), weeks= -1)

    to_date = datetime(datetime.now().year, datetime.now().month, datetime.now().day) + timedelta(days=14)

    # build body in order to get the response desired
    body = {
            "fields": ["scheduled.distance", 
                    "scheduled.durationSecs", 
                    "scheduled.name", 
                    "scheduled.pace", 
                    "scheduled.preDescr", 
                    "scheduled.time", 
                    "scheduled.tscorepwr", 
                    "scheduled.type", 
                    "scheduled.workout"
                ],
            "criteria": {
                    #"isNull": [ "fileId" ], #in order to only get scheduled workouts
                    "sports": [], # all sports
                    "fromTs": int(datetime.timestamp(monday_before)*1000),
                    "toTs": int(datetime.timestamp(to_date)*1000)
                }
            }

    # change depending on, if you want to include only scheduled or also completed workouts
    if not include_completed:
        body['criteria']['isNull'] = [ "fileId" ]
    else:
        body['fields'].extend([
            'avgBpm',
            'avgSpeed',
            'distance',
            'startTs',
            'training'
        ])

    #request url of the zone5 rest api
    workout_url = '/rest/users/activities/search/%s/%s'%(offset, max_count)
    # send get request
    resp = requests.post(base_url + workout_url, data = json.dumps(body), headers = header)
    # parse request
    scheduled_workouts, summary = parse_workouts(resp.json())

    return scheduled_workouts, resp.json(), summary


def parse_workouts(data):
    """
    Parses  response json in to readable list of dicts
    Args:
        data ([json dict): response of request 

    Returns:
        list : parsed scheduled workouts
    """
    workouts = data['result']['results']

    timestamps = [datetime.fromtimestamp(workouts[k]['ts']/1000) for k in range(len(workouts))]
    kalenderwochen = list(set([k.isocalendar()[1] for k in timestamps]))

    parsed_list = []

    aspects = { 'all': {'start': ['ts'],
                        'equipment' : ['equipment'],
                        'sport': ['type']
                        },
                'scheduled':{
                    'distance': ['scheduled', 'distance'], # These only exist if activity was scheduled
                    'duration' : ['scheduled', 'durationSecs'],
                    'trainingScore' : ['scheduled', 'tscorepwr'],
                    'name' : ['scheduled', 'name'],
                    'description' : ['scheduled', 'preDescr'],
                    'type': ['scheduled', 'workout'],
                    },
                'completed':{
                    'hf' : ['avgBpm'], # Those only exist if completed 
                    'speed': ['avgSpeed'],
                    'c_distance': ['distance'],
                    'c_duration': ['training'] # time of actual training
                    }           
                }

    summary = { k : {'scheduled': {'time' : timedelta(seconds = 0.), 'distance' : {'run' :0., 'ride':0.}},
                    'completed' : {'time' : timedelta(seconds = 0.), 'distance' : {'run' :0., 'ride':0.}}} for k in kalenderwochen}


    for number in range(len(workouts)):
        activity = {}

        activity['completed'] = 'fileId' in workouts[number]
        activity['scheduled'] = 'scheduled' in workouts[number]

        correct_aspects = aspects['all'].copy()
        if activity['completed']:
            correct_aspects.update(aspects['completed'])
        if activity['scheduled']:
            correct_aspects.update(aspects['scheduled'])

        
        for key in correct_aspects:
            temp_data = workouts[number]
            try:
                for inner_key in correct_aspects[key]:
                    temp_data = temp_data[inner_key]
                
                if key == 'start':
                    temp_data = datetime.fromtimestamp(temp_data/1000)
                elif key == 'equipment':
                    temp_data = temp_data[0].upper() + temp_data[1:]
                elif key == 'sport':
                    temp_data = temp_data[0].upper() + temp_data[1:]

                if activity['scheduled']:
                    if key == 'distance':
                        temp_data = temp_data/1000
                    elif key == 'description':
                        temp_data = strip_html(temp_data)
                    elif key == 'duration':
                        temp_data = timedelta(seconds = temp_data)

                if activity['completed']:
                    if key == 'c_duration':
                        temp_data = timedelta(seconds = temp_data)
                    elif key == 'c_distance':
                        temp_data = temp_data/1000


                activity[key] = temp_data

            except:
                activity[key] = 'No data'

        try:
            if activity['completed']:
                summary[activity['start'].isocalendar()[1]]['completed']['time'] += activity['c_duration']
                if activity['sport'] == 'Ride':
                    summary[activity['start'].isocalendar()[1]]['completed']['distance']['ride'] += activity['c_distance'] #summary according to week of calendar
                elif activity['sport'] == 'Run':
                    summary[activity['start'].isocalendar()[1]]['completed']['distance']['run'] += activity['c_distance']

            if activity['scheduled']:
                summary[activity['start'].isocalendar()[1]]['scheduled']['time'] += activity['duration']
                if activity['sport'] == 'Ride':
                    summary[activity['start'].isocalendar()[1]]['scheduled']['distance']['ride'] += activity['distance']
                elif activity['sport'] == 'Run':
                    summary[activity['start'].isocalendar()[1]]['scheduled']['distance']['run'] += activity['distance']
        except:
            None

        try:
            if activity['type'] == 'rest':
                activity['start'] = datetime(activity['start'].year, activity['start'].month, activity['start'].day, 0, 0, 0)
                activity['duration'] = timedelta(seconds = 86400)
        except:
            None

        parsed_list.append(activity)

    return parsed_list, summary



def provide_calender_file(scheduled_workouts, summary, show_completed = False):
    """
    In this function the parsed workouts are worked into a .ics file format and saved at specified place
    Args:
        scheduled_workouts (list): parsed scheduled workouts

    Returns:
        str : filename of the .ics file
    """

    current_calender = Calendar()
    current_calender.add('version', '2.0')
    current_calender.add('X-WR-CALNAME','Custom Trainingsplan')
    current_calender.add('X-WR-CALDESC','https://whats.todaysplan.com.au')
    current_calender.add('CALSCALE','GREGORIAN')
    current_calender.add('method','PUBLISH')
    current_calender.add('prodid', '-//Custom Training Plan/dsfdfdf//')


    for workout in scheduled_workouts:
        event = Event()

        if workout['scheduled'] and workout['completed'] and show_completed:
            if str(workout['sport']) == 'Gym':
                dist = ''
                dist_d = ''
            else:
                dist = ' | ' + str(np.round(workout['c_distance'],1))+ 'km'
                dist_d = str(np.round(workout['c_distance'],1))

            event_name = workout['sport'] + ' | ' + str(workout['c_duration'])[:-3] + 'h' + dist
            event_description = 'Completed\n'\
            + workout['description'] + '\n'\
            + str(workout['trainingScore']) + ' TSS\n'\
            + str(workout['c_duration'])[:-3] + ' h\n' \
            + dist_d+ ' km\n'\
            + workout['sport'] + '\n'
            #+ workout['equipment'] 

            event.add('dtend', workout['start'] + workout['c_duration']) # datetime object
            event.add('status', 'CONFIRMED')
            event.add('summary', event_name) # name of the event
            event.add('description', event_description) # descirption
            event.add('dtstart', workout['start']) # datetime object
            event.add('uid', id_generator())

            current_calender.add_component(event)



        elif workout['scheduled'] and not workout['completed'] and \
        not workout['start'] < (datetime(datetime.now().year, datetime.now().month, datetime.now().day) - timedelta(days=2)):
            if str(workout['sport']) == 'Gym':
                dist = ''
            else:
                dist = ' | ' + str(np.round(workout['distance'],1))+ 'km'

            event_name = workout['sport'] + ' | ' + str(workout['duration'])[:-3] + 'h' + dist
            event_description = workout['description'] + '\n\n'\
            + str(workout['trainingScore']) + ' TSS\n'\
            + str(workout['duration'])[:-3] + ' h\n' \
            + str(workout['distance'])+ ' km\n'\
            + workout['sport'] + '\n'
            #+ workout['equipment'] 

            event.add('dtend', workout['start'] + workout['duration']) # datetime object

            if workout['type'] == 'rest':
                event_name = 'Restday'
                event_description = workout['description']
                event.add('transp','TRANSPARENT')

            event.add('status', 'CONFIRMED')
            event.add('summary', event_name) # name of the event
            event.add('description', event_description) # descirption
            event.add('dtstart', workout['start']) # datetime object
            event.add('uid', id_generator())

            current_calender.add_component(event)


    for week in summary:
        monday = monday_of_week(week)

        sum_string = 'Scheduled\n'\
            + str(summary[week]['scheduled']['time'])[:-3] + 'h\n'\
            + 'Run: '+ str(int(summary[week]['scheduled']['distance']['run'])) + ' km\n'\
            + 'Ride: '+ str(int(summary[week]['scheduled']['distance']['ride'])) + ' km\n\n'\
            'Completed\n'\
            + str(summary[week]['completed']['time'])[:-3] + 'h\n'\
            + 'Run: '+ str(int(summary[week]['completed']['distance']['run'])) + ' km\n'\
            + 'Ride: '+ str(int(summary[week]['completed']['distance']['ride'])) + ' km\n\n'\

        event = Event()
        event.add('transp','TRANSPARENT')
        event.add('status', 'CONFIRMED')
        event.add('summary', 'Training Summary') # name of the event
        event.add('description', sum_string) # descirption
        event.add('dtstart', date(monday.year, monday.month, monday.day)) # datetime object
        #event.add('dtend', monday + timedelta(seconds=86400)) # datetime object
        event.add('uid', id_generator())
        current_calender.add_component(event)

    if platform == 'darwin':
        folder_path = 'app/calendar_folder/' 
    else:
        folder_path = 'src/app/calendar_folder/' 

    file_name = 'cur_calendar_%s.ics'%(str(datetime.now())[11:19])
    text_calendar = current_calender.to_ical().decode('utf-8')
    
    text_calendar = text_calendar.replace(';VALUE=DATE-TIME:', ':').replace('/nDESCRIPTION','Z/nDESCRIPTION').replace('/nDTEND','Z/nDTEND')
    
    if 'Restday' in text_calendar:
        text_calendar = text_calendar.replace('T000000', '')
        
    dir_volume = os.listdir(folder_path) 
    if len(dir_volume) > 100:
        for fil in dir_volume:
            os.remove(folder_path + fil)
        

    with open(folder_path + file_name, 'wb') as ics:
        ics.write(text_calendar.encode('utf-8'))

    return file_name 


def id_generator(size=24, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def monday_of_week(calendar_week):
    return datetime(datetime.now().year,1,1)+timedelta(days=-datetime(datetime.now().year,1,1).weekday(), weeks = calendar_week)

def post_auth():
    """
    Gets bearer token for authentication
    Returns:
        [type]: [description]
    """
    base = 'https://whats.todaysplan.com.au'
    req_url = '/rest/auth/login'

    if platform == 'darwin':
        cred_path = 'conf/credentials.json' #local test
    else:
        cred_path = 'src/conf/credentials.json' #serverside

    with open(cred_path) as cred:
        auth_data = json.load(cred)
        auth_id = auth_data['username']
        auth_key = auth_data['pw']

    body = {"username": auth_id, 
            "password": auth_key}

    r = requests.post(base+req_url, data = body)  

    return r.json()['token'], r.json()['user']['cid']


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def strip_html(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()
