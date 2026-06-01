import os

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
USERNAME = os.getenv("MYSQL_USER", "root")
PASSWORD = os.getenv("MYSQL_PASSWORD", "")
HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = os.getenv("MYSQL_PORT", "3306")
DATABASE = os.getenv("MYSQL_DATABASE", "flaskserver")
STEPFUN_KEY = os.getenv("STEPFUN_KEY", "")
