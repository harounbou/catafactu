import sqlite3

# Use raw strings for file paths
db_path = r"C:\Users\nounou\OneDrive - London School of Economics\Desktop\pos\catafactu\pos_system\data\pos_system.db"
output_file = r"C:\Users\nounou\OneDrive - London School of Economics\Desktop\pos\catafactu\pos_system\data\db_structure.txt"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

with open(output_file, "w", encoding="utf-8") as f:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        f.write(f"\nTable: {table_name}\n")
        f.write("Columns:\n")

        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()

        for col in columns:
            col_id, col_name, col_type, not_null, default_value, pk = col
            pk_marker = " [PK]" if pk else ""
            f.write(f"  - {col_name} ({col_type}){pk_marker}\n")

print(f"Database structure has been saved to {output_file}")

conn.close()
