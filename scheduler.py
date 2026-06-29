import schedule
import time
import threading

from logger import logger
import handlers


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)


def daily_job():
    handlers.db.reduce_days()


def start_scheduler():
    schedule.every().day.at('00:00').do(daily_job)
    threading.Thread(target=run_schedule, daemon=True).start()
    logger.info('Фоновый процесс запущен')
