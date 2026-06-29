import sys
from telebot import TeleBot

from config import TOKEN
from logger import logger

try:
    bot = TeleBot(TOKEN)
    bot.get_me()
    logger.info('Бот успешно инициализирован')
except Exception as e:
    logger.error(f'Ошибка инициализации бота: {e}')
    sys.exit(1)
