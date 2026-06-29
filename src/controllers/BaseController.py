"""
controllers/BaseController.py — Abstract Service Base Class
============================================================
.NET Equivalent: A base class shared by all service classes (NOT a web controller).

Despite the name, classes in this project's `controllers/` folder are
business-logic SERVICES, not HTTP endpoint handlers. The HTTP layer lives
in `routes/*.py` (which are the true ASP.NET-style controllers).

This base class provides:
  - Access to app configuration      → like injecting IOptions<AppSettings>
  - Shared file-system path helpers  → like IWebHostEnvironment.ContentRootPath
  - A random string generator utility
"""
from helpers.config import get_settings, Settings
import os
import random
import string

class BaseController:
    """
    Base class for all business-logic service classes.

    Subclasses (NLPController, ProcessController, DataController, ProjectController)
    inherit shared infrastructure: configuration and file-system path resolution.
    """

    def __init__(self):
        # Equivalent to injecting IOptions<AppSettings> via constructor DI.
        self.app_settings = get_settings()

        # Root directory of the `src/` folder — computed at runtime using __file__.
        # Equivalent to IWebHostEnvironment.ContentRootPath.
        self.base_dir = os.path.dirname(os.path.dirname(__file__))

        # Directory where uploaded files are stored on disk.
        self.files_dir = os.path.join(self.base_dir, "assets/files")

        # Directory for local SQLite / on-disk databases (used by some vector DB backends).
        self.database_dir = os.path.join(self.base_dir, "assets/database")
        
    def generate_random_string(self, length: int=12):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def get_database_path(self, db_name: str):

        database_path = os.path.join(
            self.database_dir, db_name
        )

        if not os.path.exists(database_path):
            os.makedirs(database_path)

        return database_path