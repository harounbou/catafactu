import sqlite3
conn = sqlite3.connect("/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/test_pos_system.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(products)")
print(cursor.fetchall())
conn.close()