import mysql.connector
import os

def get_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "tiger"),
        database=os.environ.get("DB_NAME", "food_web"),
        ssl_ca=None,
        use_pure=True,
        connection_timeout=30,
        buffered=True
    )
