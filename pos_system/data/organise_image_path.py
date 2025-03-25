import os
import sqlite3

# Print the current working directory
print("Current working directory:", os.getcwd())

# Print the absolute path to the database file
db_path = 'pos_system.db'
print("Database path:", os.path.abspath(db_path))

# Check if the database file exists
if not os.path.exists(db_path):
    print("Database file not found.")
    exit(1)

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables in the database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in the database:", tables)