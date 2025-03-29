import sqlite3
from modules.utils import DB_PATH  # Import DB_PATH first

print("DB_PATH before modification:", DB_PATH)  # Debugging line

# Corrected replacement logic
test_db_path = DB_PATH.replace("/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db", "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/test_pos_system.db")
print("Final computed DB path:", test_db_path)  # Debugging line

# Ensure the database file exists
try:
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    tables = [
        "staff_payments", "transactions", "expenditures", "till", "orders",
        "products", "clients", "product_buffer", "categories", "audit_log", "price_history"
    ]

    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
    
    conn.commit()
    conn.close()
    print("Test database tables cleared.")

except sqlite3.OperationalError as e:
    print(f"Database connection error: {e}")
