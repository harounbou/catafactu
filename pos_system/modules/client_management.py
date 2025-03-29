# modules/client_management.py
import pandas as pd
import streamlit as st
import sqlite3
from .utils import get_db_connection, fetch_df_from_db, save_df_to_db, validate_email, validate_phone


def initialize_clients_df():
    conn = get_db_connection()
    try:
        return pd.read_sql_query("SELECT * FROM clients", conn)
    except:
        return pd.DataFrame(columns=[
            'id_client', 'nom_client', 'prenom_client', 
            'telephone_client', 'email_client', 'address_client', 
            'entreprise_client'
        ])
    finally:
        conn.close()

def get_client_info(df, identifier, column_name):
    """Retrieve client information with robust error handling"""
    if df is None or df.empty:
        return None
    
    # Initialize as empty DataFrame
    client = pd.DataFrame()

    try:
        if column_name not in df.columns:
            st.error(f"Column '{column_name}' not found in DataFrame.")
            return None

        # Fixed case conversion - removed .str for non-series object
        client = df[
            df[column_name].astype(str).str.lower() == str(identifier).lower()  # Fixed line
        ]

        if not client.empty:
            return client.iloc[0].to_dict()
        return None

    except Exception as e:
        st.error(f"Error retrieving client info: {str(e)}")
        return None

def add_new_client(clients_df, new_client):
    new_id = clients_df['id_client'].max() + 1 if not clients_df.empty else 1
    new_client['id_client'] = new_id
    return pd.concat([clients_df, pd.DataFrame([new_client])], ignore_index=True)

def save_clients(clients_df):
    conn = get_db_connection()
    try:
        clients_df.to_sql('clients', conn, if_exists='replace', index=False)
        conn.commit()
    finally:
        conn.close()

def clients_page():
    st.title("Gestion des Clients")
    clients_df = initialize_clients_df()
    
    with st.container():
        st.markdown("### Recherche Client")
        search_cols = st.columns([3, 1])
        with search_cols[0]:
            search_term = st.text_input("Rechercher par:", placeholder="Nom, entreprise ou téléphone")
        with search_cols[1]:
            if st.button("🔍 Rechercher", use_container_width=True):
                filtered = clients_df[
                    (clients_df['nom_client'].str.contains(search_term, case=False, na=False)) |
                    (clients_df['entreprise_client'].str.contains(search_term, case=False, na=False)) |
                    (clients_df['telephone_client'].str.contains(search_term, na=False))
                ]
                st.session_state.filtered_clients = filtered if not filtered.empty else None
    
    if 'filtered_clients' in st.session_state and st.session_state.filtered_clients is not None:
        edited_df = st.data_editor(
            st.session_state.filtered_clients,
            use_container_width=True,
            column_config={
                "id_client": st.column_config.NumberColumn("ID", disabled=True),
                "nom_client": "Nom",
                "prenom_client": "Prénom",
                "telephone_client": "Téléphone",
                "email_client": "Email",
                "address_client": "Adresse",
                "entreprise_client": "Entreprise"
            }
        )
    else:
        edited_df = st.data_editor(
            clients_df,
            use_container_width=True,
            column_config={
                "id_client": st.column_config.NumberColumn("ID", disabled=True),
                "nom_client": "Nom",
                "prenom_client": "Prénom",
                "telephone_client": "Téléphone",
                "email_client": "Email",
                "address_client": "Adresse",
                "entreprise_client": "Entreprise"
            }
        )
    
    if st.button("Sauvegarder Modifications", type="primary"):
        save_clients(edited_df)
        st.success("Clients mis à jour avec succès!")
        st.session_state.filtered_clients = None

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
            if 'recent_clients' not in st.session_state:
                st.session_state['recent_clients'] = []
            if client_id in st.session_state['recent_clients']:
                st.session_state['recent_clients'].remove(client_id)
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