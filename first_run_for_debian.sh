#!/bin/bash
set -e

sudo apt update -y
sudo apt install -y \
    python-is-python3 \
    python3-pip \
    mc \
    python3-venv

chmod +x first_run_for_debian.sh \
         load_proxy_list_new.py \
         proxycheckerasync_my_new_3.py \
         a.sh

chmod 755 proxycheckerasync_add.py 
