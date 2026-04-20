#!/bin/bash

set -e

BASE_DIR="/home/sprite_lutsk"
ENV_DIR="$BASE_DIR/venv"
PYTHON="$ENV_DIR/bin/python"
PIP="$ENV_DIR/bin/pip"
#PIP="pip"
python3 -m venv venv
source venv/bin/activate
pip install requests

cd "$BASE_DIR"

echo "Start: $(date)"

# Создание venv (один раз)
if [ ! -d "$ENV_DIR" ]; then
    echo "Создаётся виртуальное окружение..."
    /usr/bin/python3 -m venv "$ENV_DIR"
fi

# УСТАНОВКУ ПАКЕТОВ ДЕЛАТЬ ТОЛЬКО ЕСЛИ НАДО
"$PIP" install --quiet aiohttp rich termcolor requests geoip2 bs4

# Запуск скриптов
#"$PYTHON" load_proxy_list_new.py
"$PYTHON" proxycheckerasync_my_new_3.py

echo "End: $(date)"
