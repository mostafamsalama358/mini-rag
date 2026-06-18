import os
from dotenv import dotenv_values

config = dotenv_values(".env")
flower_password = os.getenv("CELERY_FLOWER_PASSWORD") or config.get("CELERY_FLOWER_PASSWORD")

# Flower configuration
port = 5555
max_tasks = 10000
# db = 'flower.db'  # SQLite database for persistent storage
auto_refresh = True

# Authentication (optional)
if flower_password:
    basic_auth = [f"admin:{flower_password}"]

