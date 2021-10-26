import json
from datetime import datetime, timedelta
from worker.worker_functions import *
import requests



test,a = get_scheduled()
calendar_file_path = provide_calender_file(test)
