#!/bin/sh
cd /volume1/repos/calendar_training
/bin/git fetch --all
/bin/git reset --hard origin/master
/bin/git pull origin master
/usr/local/bin/docker-compose build
/usr/local/bin/docker-compose up -d