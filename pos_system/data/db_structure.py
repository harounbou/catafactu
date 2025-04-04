import sqlite3

# Connect to the database
db_path = "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db"  
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Output file
output_file = "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/db_structure.txt"

with open(output_file, "w", encoding="utf-8") as f:
    # Get all table names
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

# Close connection
conn.close()
