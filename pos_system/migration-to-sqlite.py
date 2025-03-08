import pandas as pd
import sqlite3

# Database path
db_path = "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db"

# File paths
file_paths = {
    "products": "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/products.xlsx",
    "clients": "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/clients.xlsx",
    "expenditures": "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/expenditures.csv",
    "staff_payments": "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/staff_payments.csv",
    "till": "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/till.csv",
    "transactions": "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/transactions.csv"
}

# Connect to SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Function to load file (Excel or CSV)
def load_file(file_path):
    if file_path.endswith(".xlsx"):
        return pd.read_excel(file_path)
    elif file_path.endswith(".csv"):
        return pd.read_csv(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

# 1. Migrate products (Excel)
products_df = load_file(file_paths["products"])
products_df = products_df.rename(columns={
    "Prix Super Gros": "prix-super-gros",
    "Prix Gros": "prix-gros",
    "Prix Détail": "prix-détail",
    "Reference": "reference",
    "Denomination": "denomination",
    "Quantite Initiale": "quantite_initiale",
    "Quantite Restockee": "quantite_restockee",
    "Quantite Vendue": "quantite_vendue",
    "Quantite Actuelle": "quantite_actuelle",
    "Couleurs Dispo Usine": "couleurs-dispo-usine",
    "Images": "images",
    "Uni Colour": "uni_colour",
    "Default Colour": "default_colour",
    "Brown": "brown",
    "Brown Deg": "brown_deg",
    "Blue": "blue",
    "White": "white",
    "Black": "black",
    "Green Bottle": "green_bottle",
    "Red": "red",
    "Grey": "grey",
    "Grey Deg": "grey_deg",
    "Beige": "beige",
    "Yellow": "yellow",
    "Orange": "orange",
    "Garnet": "garnet",
    "Golden": "golden",
    "Green": "green",
    "Rose": "rose",
    "Note": "note",
    "Category": "category",
    "Quantite Vendu Actue": "quantite_vendu_actue"
})
numeric_cols = [
    "prix-super-gros", "prix-gros", "prix-détail", "quantite_initiale",
    "quantite_restockee", "quantite_vendue", "quantite_actuelle",
    "brown", "brown_deg", "blue", "white", "black", "green_bottle",
    "red", "grey", "grey_deg", "beige", "yellow", "orange", "garnet",
    "golden", "green", "rose", "quantite_vendu_actue"
]
for col in numeric_cols:
    products_df[col] = pd.to_numeric(products_df[col], errors='coerce').fillna(0)
products_df.to_sql("products", conn, if_exists="replace", index=False)

# 2. Migrate clients (Excel)
clients_df = load_file(file_paths["clients"])
clients_df = clients_df.rename(columns={
    "id_client": "id_client",
    "nom_client": "nom_client",
    "prenom_client": "prenom_client",
    "telephone_client": "telephone_client",
    "address_client": "address_client",
    "email_client": "email_client",
    "entreprise_client": "entreprise_client"
})
numeric_cols = ["id_client", "telephone_client"]
for col in numeric_cols:
    clients_df[col] = pd.to_numeric(clients_df[col], errors='coerce').fillna(0)
clients_df.to_sql("clients", conn, if_exists="replace", index=False)

# 3. Migrate expenditures (CSV)
expenditures_df = load_file(file_paths["expenditures"])
expenditures_df = expenditures_df.rename(columns={
    "expenditure_id": "expenditure_id",
    "date": "date",
    "assistant_name": "assistant_name",
    "amount": "amount",
    "description": "description"
})
numeric_cols = ["expenditure_id", "amount"]
for col in numeric_cols:
    expenditures_df[col] = pd.to_numeric(expenditures_df[col], errors='coerce').fillna(0)
expenditures_df.to_sql("expenditures", conn, if_exists="replace", index=False)

# 4. Migrate staff_payments (CSV)
staff_payments_df = load_file(file_paths["staff_payments"])
staff_payments_df = staff_payments_df.rename(columns={
    "payment_id": "payment_id",
    "date": "date",
    "staff_name": "staff_name",
    "amount": "amount"
})
numeric_cols = ["payment_id", "amount"]
for col in numeric_cols:
    staff_payments_df[col] = pd.to_numeric(staff_payments_df[col], errors='coerce').fillna(0)
staff_payments_df.to_sql("staff_payments", conn, if_exists="replace", index=False)

# 5. Migrate till (CSV)
till_df = load_file(file_paths["till"])
till_df = till_df.rename(columns={
    "date": "date",
    "amount": "amount",
    "direction": "direction",
    "description": "description",
    "balance": "balance"
})
numeric_cols = ["amount", "balance"]
for col in numeric_cols:
    till_df[col] = pd.to_numeric(till_df[col], errors='coerce').fillna(0)
till_df.to_sql("till", conn, if_exists="replace", index=False)

# 6. Migrate transactions (CSV)
transactions_df = load_file(file_paths["transactions"])
transactions_df = transactions_df.rename(columns={
    "transaction_id": "transaction_id",
    "date": "date",
    "client_id": "client_id",
    "items": "items",
    "total_amount": "total_amount",
    "status": "status",
    "payment_type": "payment_type",
    "deposit_amount": "deposit_amount",
    "remaining_amount": "remaining_amount"
})
numeric_cols = ["transaction_id", "client_id", "total_amount", "deposit_amount", "remaining_amount"]
for col in numeric_cols:
    transactions_df[col] = pd.to_numeric(transactions_df[col], errors='coerce').fillna(0)
transactions_df.to_sql("transactions", conn, if_exists="replace", index=False)

# Commit changes and close connection
conn.commit()
conn.close()

print("Migration completed successfully! Database saved to:", db_path)