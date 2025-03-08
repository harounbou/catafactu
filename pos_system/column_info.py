import pandas as pd

# Define the path to the data directory
data_dir = '/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/'

# Read the data files
clients_df = pd.read_excel(data_dir + 'clients.xlsx', engine='openpyxl')
expenditures_df = pd.read_csv(data_dir + 'expenditures.csv')
staff_payments_df = pd.read_csv(data_dir + 'staff_payments.csv')
till_df = pd.read_csv(data_dir + 'till.csv')
transactions_df = pd.read_csv(data_dir + 'transactions.csv')

# Function to get column names and data types
def get_column_info(df):
    return df.dtypes

# Get column info for each dataframe
clients_info = get_column_info(clients_df)
expenditures_info = get_column_info(expenditures_df)
staff_payments_info = get_column_info(staff_payments_df)
till_info = get_column_info(till_df)
transactions_info = get_column_info(transactions_df)

# Print column info
print("Clients Table Columns and Data Types:\n", clients_info)
print("\nExpenditures Table Columns and Data Types:\n", expenditures_info)
print("\nStaff Payments Table Columns and Data Types:\n", staff_payments_info)
print("\nTill Table Columns and Data Types:\n", till_info)
print("\nTransactions Table Columns and Data Types:\n", transactions_info)