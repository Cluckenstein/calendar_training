import json
from datetime import datetime, timedelta
from worker.worker_functions import *
import requests



test,a, summary = get_scheduled(include_completed=True)
calendar_file_path = provide_calender_file(test, summary)

