import schedule
import time
import threading

from logger import logger
import handlers

from database import database_manager


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)


def daily_job():
    result = database_manager.bulk_decrease_days()
    logger.info(f"Уменьшено дней у {result} польз.")
    

def start_scheduler():
    schedule.every().day.at('00:00').do(daily_job)
    threading.Thread(target=run_schedule, daemon=True).start()
    logger.info('Фоновый процесс запущен')
