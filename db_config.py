import pymysql

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="krishi1234",
        database="krishibondhondb",
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor  # This makes cursor.fetchone() return dict
    )
