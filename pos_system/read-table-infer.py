import pandas as pd

# Define the path to the data directory
data_dir = '/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/'

# Read the data files
clients_df = pd.read_excel(data_dir + 'clients.xlsx', engine='openpyxl')
expenditures_df = pd.read_csv(data_dir + 'expenditures.csv')
products_df = pd.read_excel(data_dir + 'products.xlsx', engine='openpyxl')
staff_payments_df = pd.read_csv(data_dir + 'staff_payments.csv')
till_df = pd.read_csv(data_dir + 'till.csv')
transactions_df = pd.read_csv(data_dir + 'transactions.csv')

# Function to infer data types
def infer_data_types(df):
    data_types = {}
    for column in df.columns:
        if 'date' in column.lower():
            data_types[column] = 'DATE'
        elif 'amount' in column.lower() or 'price' in column.lower() or 'total' in column.lower():
            data_types[column] = 'FLOAT'
        elif 'id' in column.lower():
            data_types[column] = 'INTEGER'
        else:
            data_types[column] = 'TEXT'
    return data_types

# Infer data types for each dataframe
clients_data_types = infer_data_types(clients_df)
expenditures_data_types = infer_data_types(expenditures_df)
products_data_types = infer_data_types(products_df)
staff_payments_data_types = infer_data_types(staff_payments_df)
till_data_types = infer_data_types(till_df)
transactions_data_types = infer_data_types(transactions_df)

# Print inferred data types
print("Clients Data Types:", clients_data_types)
print("Expenditures Data Types:", expenditures_data_types)
print("Products Data Types:", products_data_types)
print("Staff Payments Data Types:", staff_payments_data_types)
print("Till Data Types:", till_data_types)
print("Transactions Data Types:", transactions_data_types)