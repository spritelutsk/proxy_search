#!/bin/bash

chmod +x first_run_for_debian.sh
chmod +x load_proxy_list_new.py
chmod +x proxycheckerasync_my_new_3.py
chmod 755 proxycheckerasync_add.py

# ./first_run_for_debian.sh

# если какая-то команда завершится с ошибкой (ненулевым кодом), скрипт сразу прервётся
# set -e 

sudo apt udate
sudo apt uprgade
sudo apt install python-is-python3
sudo apt install pip
sudo apt install mc
sudo apt install python3.11-venv
