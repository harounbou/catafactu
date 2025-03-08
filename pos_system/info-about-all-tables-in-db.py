import sqlite3

def get_database_info(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Dictionary to store table information
    database_info = {}

    # Iterate over each table to get headers and data types
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        # Store column names and data types
        headers = [(column[1], column[2]) for column in columns]
        database_info[table_name] = headers

    # Close the connection
    conn.close()

    return database_info

def print_database_info(database_info):
    for table_name, headers in database_info.items():
        print(f"Table: {table_name}")
        for header in headers:
            print(f"  Column: {header[0]}, Data Type: {header[1]}")

if __name__ == "__main__":
    db_path = '/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db'  # Update this path to your database file
    database_info = get_database_info(db_path)
    print_database_info(database_info)