from .manager import DatabaseManager
from config import DATABASE_URL

database_manager = DatabaseManager(DATABASE_URL)

__all__ = ["database_manager"]