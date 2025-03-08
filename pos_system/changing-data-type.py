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

# Function to change data types
def change_data_types(df, data_types):
    for column, dtype in data_types.items():
        if dtype == 'INTEGER':
            if df[column].dtype == 'object':
                df[column] = pd.to_numeric(df[column].str.replace(' ', ''), errors='coerce').fillna(0).astype(int)
            else:
                df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0).astype(int)
        elif dtype == 'FLOAT':
            if df[column].dtype == 'object':
                df[column] = pd.to_numeric(df[column].str.replace(' ', ''), errors='coerce').fillna(0.0).astype(float)
            else:
                df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0.0).astype(float)
        elif dtype == 'DATE':
            df[column] = pd.to_datetime(df[column], errors='coerce')
        else:
            df[column] = df[column].astype(str)
    return df

# Define the corrected data types
clients_data_types = {'id_client': 'INTEGER', 'nom_client': 'TEXT', 'prenom_client': 'TEXT', 'telephone_client': 'TEXT', 'address_client': 'TEXT', 'email_client': 'TEXT', 'entreprise_client': 'TEXT'}
expenditures_data_types = {'expenditure_id': 'INTEGER', 'date': 'DATE', 'assistant_name': 'TEXT', 'amount': 'FLOAT', 'description': 'TEXT'}
products_data_types = {'reference': 'TEXT', 'denomination': 'TEXT', 'quantite_initiale': 'INTEGER', 'quantite_restockee': 'INTEGER', 'quantite_vendue': 'INTEGER', 'quantite_actuelle': 'INTEGER', 
                       'couleurs-dispo-usine': 'TEXT', 'images': 'TEXT', 
                       'prix-super-gros': 'FLOAT', 
                       'prix-gros': 'FLOAT', 
                       'prix-détail': 'FLOAT',
                       'uni_colour': 'TEXT', 
                       'default_colour': 'TEXT',
                       # other color columns remain TEXT
                       }
staff_payments_data_types = {'payment_id': 'INTEGER', 'date': 'DATE', 'staff_name': 'TEXT', 'amount': 'FLOAT'}
till_data_types = {'date': 'DATE', 'amount': 'FLOAT', 'direction': 'TEXT', 'description': 'TEXT', 'balance': 'FLOAT'}
transactions_data_types = {'transaction_id': 'INTEGER', 'date': 'DATE', 'client_id': 'INTEGER', 'items': 'TEXT', 'total_amount': 'FLOAT', 'status': 'TEXT', 'payment_type': 'TEXT', 'deposit_amount': 'FLOAT', 'remaining_amount': 'FLOAT'}

# Change data types for each dataframe
clients_df = change_data_types(clients_df, clients_data_types)
expenditures_df = change_data_types(expenditures_df, expenditures_data_types)
products_df = change_data_types(products_df, products_data_types)
staff_payments_df = change_data_types(staff_payments_df, staff_payments_data_types)
till_df = change_data_types(till_df, till_data_types)
transactions_df = change_data_types(transactions_df, transactions_data_types)

# Print the dataframes to verify changes
print(clients_df.dtypes)
print(expenditures_df.dtypes)
print(products_df.dtypes)
print(staff_payments_df.dtypes)
print(till_df.dtypes)
print(transactions_df.dtypes)