import threading
from io import BytesIO
import qrcode
from logger import logger


def qrcode_generate(url):
	img = qrcode.make(url)
	buffer = BytesIO()
	img.save(buffer, format='PNG')
	buffer.seek(0)
	return buffer


def generate_secure_code(n):
	return ''.join(__import__('secrets').choice('0123456789') for _ in range(n))


def _schedule_delete(callback, seconds):
	timer = threading.Timer(seconds, callback)
	timer.daemon = True
	timer.start()
	return timer


def send_temp_photo(bot, chat_id, buffer, seconds=30, **kwargs):
	try:
		msg = bot.send_photo(chat_id, buffer, **kwargs)

		def delete():
			try:
				bot.delete_message(chat_id, msg.message_id)
			except Exception as e:
				logger.error(f'Ошибка удаления сообщения: {e}')

		_schedule_delete(delete, seconds)
	except Exception as e:
		logger.error(f'Ошибка при отправке временного изображения: {e}')


def send_temp_message(bot, chat_id, text, seconds=30, **kwargs):
	try:
		msg = bot.send_message(chat_id, text, **kwargs)

		def delete():
			try:
				bot.delete_message(chat_id, msg.message_id)
			except Exception as e:
				logger.error(f'Ошибка удаления сообщения: {e}')

		_schedule_delete(delete, seconds)
	except Exception as e:
		logger.error(f'Ошибка при отправке временного сообщения: {e}')


def temp_code_deleter(dict, key, value, seconds=3600):
	dict[key] = value
	def delete():
		try:
			dict.pop(key, None)
		except Exception as e:
			logger.error(f'Ошибка удаления из словаря: {e}')

	_schedule_delete(delete, seconds)
	