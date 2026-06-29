import time

from logger import logger
from bot import bot
import handlers
from scheduler import start_scheduler


if __name__ == '__main__':
    try:
        logger.info('Запуск бота...')
        start_scheduler()

        while True:
            try:
                bot.infinity_polling(timeout=60, long_polling_timeout=60)
            except Exception as e:
                logger.error(f'Ошибка в polling: {e}')
                logger.info('Перезапуск через 5 секунд...')
                time.sleep(5)
                continue
            break
    except KeyboardInterrupt:
        logger.info('Бот остановлен пользователем')
    except Exception as e:
        logger.error(f'Критическая ошибка: {e}')
    finally:
        handlers.db.close()
        logger.info('Ресурсы освобождены')
