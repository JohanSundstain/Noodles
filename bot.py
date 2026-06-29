import telebot
import sys
from telebot import types
from contextlib import contextmanager

from utils import logger
from config import TOKEN

# Инициализация бота с обработкой ошибок
try:
	bot = telebot.TeleBot(TOKEN)
	bot.get_me()  # Проверка токена
	logger.info("Бот успешно инициализирован")
except Exception as e:
	logger.error(f"Ошибка инициализации бота: {e}")
	sys.exit(1)
