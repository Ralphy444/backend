import mysql.connector

# Connect to MySQL
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='foodordering'
)

cursor = conn.cursor()

# Delete all migration records
cursor.execute("DELETE FROM django_migrations")
conn.commit()

print("All migration records cleared!")

cursor.close()
conn.close()
