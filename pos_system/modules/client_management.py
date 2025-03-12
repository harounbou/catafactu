#client_management.py
import pandas as pd
import streamlit as st
import sqlite3
from .utils import get_db_connection, fetch_df_from_db, save_df_to_db, validate_email, validate_phone

def initialize_clients_df():
    """Initialize or refresh clients_df from database"""
    conn = get_db_connection()
    try:
        clients_df = pd.read_sql_query("SELECT * FROM clients", conn)
        if 'clients_df' not in st.session_state or st.session_state['clients_df'].empty:
            st.session_state['clients_df'] = clients_df
        return st.session_state['clients_df']
    finally:
        conn.close()
    
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

def add_new_client_info(clients_df, client_info):
    """Add a new client and refresh clients_df"""
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

def add_new_client(clients_df, new_client_info):
    """Add a new client and refresh clients_df"""
    conn = get_db_connection()
    try:
        new_client_df = pd.DataFrame([new_client_info])
        if 'id_client' not in new_client_df.columns or pd.isna(new_client_df['id_client'].iloc[0]):
            max_id = clients_df['id_client'].max() if not clients_df.empty else 0
            new_client_df['id_client'] = max_id + 1
        updated_df = pd.concat([clients_df, new_client_df], ignore_index=True)
        updated_df.to_sql('clients', conn, if_exists='replace', index=False)
        st.session_state['clients_df'] = updated_df
        return updated_df
    finally:
        conn.close()

def update_client(clients_df, client_info, index):
    clients_df.loc[index, client_info.keys()] = client_info.values()
    save_df_to_db(clients_df, 'clients')
    return clients_df

def get_client_info(clients_df, search_value, search_method):
    """Retrieve client information based on search criteria"""
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

def delete_client(clients_df, index):
    """Delete a client and refresh clients_df"""
    conn = get_db_connection()
    try:
        clients_df = clients_df.drop(index)
        clients_df.to_sql('clients', conn, if_exists='replace', index=False)
        st.session_state['clients_df'] = clients_df
        return clients_df
    finally:
        conn.close()

def save_clients(clients_df):
    """Save clients_df to database"""
    conn = get_db_connection()
    try:
        clients_df.to_sql('clients', conn, if_exists='replace', index=False)
        st.session_state['clients_df'] = clients_df  # Update session state
    finally:
        conn.close()
