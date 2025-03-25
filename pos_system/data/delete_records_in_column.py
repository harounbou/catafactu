import sqlite3

def clear_images_column():
    db_path = '/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db'
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Set the "images" column to an empty string for all rows
    cursor.execute('UPDATE "products" SET "couleurs-dispo-usine" = ""')
    # Commit the changes
    conn.commit()
    # Close the connection
    conn.close()

if __name__ == '__main__':
    clear_images_column()