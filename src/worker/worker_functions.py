#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 21:40:35 2020

@author: maximilianreihn
"""

import requests
from icalendar import Calendar, Event
from datetime import datetime,timedelta
import json
import string
import random
from sys import platform
from io import StringIO
from html.parser import HTMLParser


def get_scheduled(base_url = 'https://whats.todaysplan.com.au', offset = 0, max_count = 50):
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

    token, client_id = post_auth()

    header = {'Authorization' : 'Bearer %s'%(token),
            'Content-Type' : 'application/json',
            'Api-Key': client_id,
            'tp-nodecorate':   'true'}

    from_date = datetime.now() + timedelta(days=-7)
    to_date = datetime.now() + timedelta(days=14)

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
                    "isNull": [ "fileId" ], #in order to only get scheduled workouts
                    "sports": [], # all sports
                    "fromTs": int(datetime.timestamp(from_date)*1000),
                    "toTs": int(datetime.timestamp(to_date)*1000)
                }
            }

    workout_url = '/rest/users/activities/search/%s/%s'%(offset, max_count)

    resp = requests.post(base_url + workout_url, data = json.dumps(body), headers = header)

    scheduled_workouts = parse_workouts(resp.json())


    return scheduled_workouts, resp.json()


def provide_calender_file(scheduled_workouts):
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


        #event_name = workout['name'] #falls name in zukungt gegeben wird 
        try:
            event_name = workout['sport'] + ' | ' + str(workout['duration'])[:-3] + 'h | ' + str(workout['distance'])+ 'km'
        except:
            event_name = 'Training'

        event_description = workout['description'] + '\n\n'\
         + str(workout['trainingScore']) + ' TSS\n'\
         + str(workout['duration'])[:-3] + ' h\n' \
         + str(workout['distance'])+ ' km\n'\
         + workout['sport'] + '\n'\
         + workout['equipment'] 

        event = Event()

        if workout['type'] == 'rest':
            event_name = 'Restday'
            event_description = workout['description']
            event.add('transp','TRANSPARENT')

        event.add('status', 'CONFIRMED')

        event.add('summary', event_name) # name of the event
        event.add('description', event_description) # descirption
        event.add('dtstart', workout['start']) # datetime object
        #event.add('duration', workout['duration']) # timedelta objecgt
        event.add('dtend', workout['start'] + workout['duration']) # datetime object
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

    with open(folder_path + file_name, 'wb') as ics:
        ics.write(text_calendar.encode('utf-8'))

    return file_name 


def parse_workouts(data):
    """
    Parses  response json in to readable list of dicts
    Args:
        data ([json dict): response of request 

    Returns:
        list : parsed scheduled workouts
    """
    workouts = data['result']['results']

    parsed_list = []

    for number in range(len(workouts)):
        temp_dict = {}

        aspects = {
            'start': ['ts'],
            'distance': ['scheduled', 'distance'],
            'duration' : ['scheduled', 'durationSecs'],
            'trainingScore' : ['scheduled', 'tscorepwr'],
            'name' : ['scheduled', 'name'],
            'sport': ['scheduled', 'type'],
            'description' : ['scheduled', 'preDescr'],
            'equipment' : ['equipment'],
            'type': ['scheduled', 'workout'],
            }
        

        for key in aspects:
            try:
                temp_data = workouts[number]
                for inner_key in aspects[key]:
                    temp_data = temp_data[inner_key]
                
                if key == 'start':
                    temp_data = datetime.fromtimestamp(temp_data/1000)
                elif key == 'distance':
                    temp_data = temp_data/1000
                elif key == 'description':
                    temp_data = strip_html(temp_data)
                elif key == 'sport' or key == 'equipment':
                    temp_data = temp_data[0].upper() + temp_data[1:]
                elif key == 'duration':
                    temp_data = timedelta(seconds = temp_data)

                temp_dict[key] = temp_data

            except:
                temp_dict[key] = ''

        try:
            if temp_dict['type'] == 'rest':
                temp_dict['start'] = datetime(temp_dict['start'].year, temp_dict['start'].month, temp_dict['start'].day, 0, 0, 0)
                temp_dict['duration'] = timedelta(seconds = 86400)
        except:
            None

        parsed_list.append(temp_dict)

    return parsed_list


def id_generator(size=24, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def post_auth():
    """
    Gets bearer token for authentication
    Returns:
        [type]: [description]
    """
    base = 'https://whats.todaysplan.com.au'
    req_url = '/rest/auth/login'

    if platform == 'darwin':
        cred_path = 'credentials.json' #local test
    else:
        cred_path = 'src/credentials.json' #serverside

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