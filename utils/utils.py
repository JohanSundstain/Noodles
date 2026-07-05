import secrets
from config import ADMIN_ID, OWNER_ID

def generate_secure_code(n : int) -> int:
	return int(''.join(__import__('secrets').choice('0123456789') for _ in range(n)))

def is_admin(user_id):
	return user_id == ADMIN_ID

def is_owner(user_id):
	return user_id == OWNER_ID