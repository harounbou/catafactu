import sqlite3

# Use raw string for the database path
db_path = r"C:\Users\nounou\OneDrive - London School of Economics\Desktop\pos\catafactu\pos_system\data\pos_system.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]
    print(f"\nTable: {table_name}")
    print("Columns:")

    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()

    for col in columns:
        col_id, col_name, col_type, not_null, default_value, pk = col
        pk_marker = " [PK]" if pk else ""
        print(f"  - {col_name} ({col_type}){pk_marker}")

conn.close()