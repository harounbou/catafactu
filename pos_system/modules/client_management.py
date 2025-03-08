import pandas as pd
import streamlit as st
from .utils import get_db_connection, fetch_df_from_db, save_df_to_db, validate_email, validate_phone

def initialize_clients_df():
    if 'clients_df' not in st.session_state:
        clients_df = fetch_df_from_db('clients')
        if not clients_df.empty:
            st.session_state['clients_df'] = clients_df
        else:
            st.session_state['clients_df'] = pd.DataFrame(columns=[
                "id_client", "nom_client", "prenom_client", "telephone_client",
                "address_client", "email_client", "entreprise_client"
            ])
    if 'recent_clients' not in st.session_state:
        st.session_state['recent_clients'] = []

def get_client_info(clients_df, search_value, search_method):
    if not clients_df.empty:
        if search_method == "Nom du client":
            client = clients_df[clients_df['nom_client'].astype(str).str.lower() == search_value.lower()]
        elif search_method == "ID Client":
            try:
                client_id = int(search_value)
                client = clients_df[clients_df['id_client'] == client_id]
            except ValueError:
                return None
        if not client.empty:
            client_info = client.iloc[0].to_dict()
            client_info['index'] = client.index[0]
            return client_info
    return None

def add_new_client(clients_df, client_info):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id_client) FROM clients")
            max_id = cursor.fetchone()[0]
            client_info['id_client'] = 2000 if max_id is None else max_id + 1
            clients_df = pd.concat([clients_df, pd.DataFrame([client_info])], ignore_index=True)
            save_df_to_db(clients_df, 'clients')
            client_id = client_info['id_client']
            if client_id not in st.session_state['recent_clients']:
                st.session_state['recent_clients'].insert(0, client_id)
                if len(st.session_state['recent_clients']) > 5:
                    st.session_state['recent_clients'].pop()
            conn.close()
            return clients_df
        except sqlite3.Error as e:
            st.error(f"Failed to add new client: {e}")
            conn.close()
    return clients_df

def update_client(clients_df, client_info, index):
    clients_df.loc[index, client_info.keys()] = client_info.values()
    save_df_to_db(clients_df, 'clients')
    return clients_df

def save_clients(clients_df):
    return save_df_to_db(clients_df, 'clients')