#!/bin/sh
cd /volume1/repos/calendar_training
/bin/git pull
/usr/local/bin/docker-compose build
/usr/local/bin/docker-compose up -d