"""
repositories/base.py — Abstract Repository Base Class
=====================================================
.NET Equivalent: Repository Base Class (e.g., Repository<T>)
"""
from helpers.config import get_settings, Settings
from typing import Callable
from sqlalchemy.ext.asyncio import AsyncSession

class BaseDataModel:
    """
    Base class for all repository classes (Data Access Layer).
    """

    def __init__(self, db_client: Callable[[], AsyncSession]):
        # The db_client is a SQLAlchemy `sessionmaker`.
        # When called `db_client()`, it returns a new DB session (like instantiating a new DbContext).
        self.db_client = db_client

        # Equivalent to injecting IOptions<AppSettings>
        self.app_settings = get_settings()
