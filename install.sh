#!/bin/bash

set -e

echo "Обновление списка пакетов..."
apt update

echo "Установка Python, pip и venv..."
apt install -y python3 python3-pip python3-venv

echo "Создание виртуального окружения..."
python3 -m venv venv

echo "Активация виртуального окружения..."
source venv/bin/activate

echo "Обновление pip..."
python -m pip install --upgrade pip

echo "Установка зависимостей..."
pip install -r requirements.txt

source venv/bin/activate

echo "====================================="
echo "Установка завершена!"
echo "====================================="