# config/db_config.py
import os
import pymysql
from pymysql.cursors import DictCursor

class DB:
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.user = os.getenv("DB_USER", "elevator_ai")
        self.password = os.getenv("DB_PASSWORD", "elevator123")
        self.database = os.getenv("DB_NAME", "elevator_ai")
        self.port = int(os.getenv("DB_PORT", "3306"))

    def connect(self):
        return pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            port=self.port,
            cursorclass=DictCursor,
            autocommit=True,
            charset="utf8mb4"
        )

db = DB()

