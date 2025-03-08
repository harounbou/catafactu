import sqlite3

# Define the path to the SQLite database
db_path = '/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db'

# Connect to the SQLite database
conn = sqlite3.connect(db_path)

# Function to get table structure
def get_table_structure(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return columns

# Get a list of all tables in the database
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# Generate report
report = "SQLite Database Structure Report\n"
report += "=" * 30 + "\n\n"

for table in tables:
    table_name = table[0]
    report += f"Table: {table_name}\n"
    report += "-" * 30 + "\n"
    columns = get_table_structure(cursor, table_name)
    for column in columns:
        report += f"Column: {column[1]}, Type: {column[2]}\n"
    report += "\n"

# Close the connection
conn.close()

# Print the report
print(report)