import os

port = int(os.getenv("FLOWER_PORT", "5555"))
max_tasks = 10000
auto_refresh = True

basic_auth_env = os.getenv("FLOWER_BASIC_AUTH")
if basic_auth_env:
    basic_auth = [basic_auth_env]
