#!/bin/sh
cd /volume1/repos/calendar_training
/bin/git fetch --all
/bin/git reset --hard origin/master
/bin/git pull origin master
[[ ":$PATH:" != *":/usr/local/bin:"* ]] && PATH="/usr/local/bin:${PATH}"
[[ ":$PATH:" != *":/usr/syno/sbin:"* ]] && PATH="/usr/syno/sbin:${PATH}"
[[ ":$PATH:" != *":/usr/syno/bin:"* ]] && PATH="/usr/syno/bin:${PATH}"
[[ ":$PATH:" != *":/usr/local/sbin:"* ]] && PATH="/usr/local/sbin:${PATH}"
[[ ":$PATH:" != *":/usr/local/bin:"* ]] && PATH="/usr/local/bin:${PATH}"
/usr/local/bin/docker-compose up --build -d --remove-orphans