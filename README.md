# Noodles Bot

Этот проект запускает Telegram-бота для продажи и управления подписками.

## Требования

- Linux / Ubuntu / Debian
- Python 3.8+
- bash
- wget
- curl

## Быстрая установка и запуск

1. Перейдите в папку проекта:

```bash
cd /path/to/Noodles
```

2. Сделайте скрипт исполняемым:

```bash
chmod +x install_and_run.sh
```

3. Запустите установку и запуск:

```bash
./install_and_run.sh
```

Скрипт автоматически:
- создаст виртуальное окружение Python;
- установит зависимости из requirements.txt;
- установит Xray через предоставленную команду;
- запустит бота в фоне.

## Настройка токенов

Перед запуском создайте файл [secrets.py](secrets.py) и укажите ваши значения:

```python
token = "YOUR_TELEGRAM_BOT_TOKEN"
admin_id = 123456789
owner_id = 123456789
number = 123456789
```

## Ручной запуск

Если нужно запустить вручную без скрипта:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m Noodles.main
```
