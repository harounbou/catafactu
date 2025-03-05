# pos_system/app.py
import streamlit as st
import pandas as pd  # Added for pd.notna()
from datetime import datetime
from modules.client_management import initialize_clients_df, get_client_info, add_new_client, save_clients
from modules.product_management import load_products, update_stock, restock_product
from modules.transaction_management import record_transaction, record_expenditure, record_staff_payment, get_till_balance
from modules.pdf_generator import generate_receipt_pdf
from modules.proforma import proforma_page
from modules.utils import validate_email, validate_phone

# Global CSS styling for the app
st.markdown(
    """
    <style>
    .stApp { 
        background-color: #f0f0f0; /* Default background for all pages */
    }
    button[kind="primary"] { 
        background-color: #90EE90 !important; 
        color: black !important; 
    }
    button[kind="secondary"] { 
        background-color: #90EE90 !important; 
        color: black !important; 
    }
    /* Style all text inputs globally */
    div[data-baseweb="input"] > div {
        background-color: #e6e6e6; /* Light gray background */
        border: 1px solid #333; /* Dark border */
        border-radius: 4px;
    }
    /* Style all select boxes globally */
    div[data-baseweb="select"] > div {
        background-color: #e6e6e6; /* Light gray background */
        border: 1px solid #333; /* Dark border */
        border-radius: 4px;
    }
    /* Style placeholder text */
    input::placeholder {
        color: #555; /* Darker gray */
        opacity: 1;
    }
    /* Ensure text is black */
    input, div[data-baseweb="select"] {
        color: #000 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def initialize_session_state():
    if 'transaction_number' not in st.session_state:
        st.session_state['transaction_number'] = 1000
    initialize_clients_df()

def pos_page():
    st.title("Point of Sale")
    initialize_session_state()
    products_df = load_products()
    clients_df = st.session_state['clients_df']

    with st.expander("Gestion des clients", expanded=True):
        client_action = st.radio("Action", ["Client récent", "Rechercher un client", "Ajouter un nouveau client", "Modifier un client chargé"], key="pos_client_action")
        if client_action == "Client récent":
            recent_clients = st.session_state['recent_clients']
            if recent_clients:
                st.write("#### Clients récents")
                for client_id in recent_clients:
                    client = clients_df[clients_df['id_client'] == client_id]
                    if not client.empty:
                        client_info = client.iloc[0].to_dict()
                        client_info['index'] = client.index[0]
                        client_name = client_info.get('nom_client', 'Inconnu')
                        if st.button(f"Charger {client_name} (ID: {client_id})", key=f"pos_recent_{client_id}"):
                            st.session_state["client_info_loaded"] = client_info
                            st.session_state["client_index"] = client_info['index']
                            st.success(f"Client {client_name} chargé !")
        elif client_action == "Rechercher un client":
            client_search_method = st.radio("Rechercher par", ["Nom du client", "ID Client"], key="pos_client_search_method")
            client_search_value = st.text_input("Valeur de recherche", placeholder="Tapez le nom du client ou ID", key="pos_client_search_value")
            if st.button("Rechercher client", key="pos_search_client"):
                if client_search_value:
                    client_info = get_client_info(clients_df, client_search_value, client_search_method)
                    if client_info:
                        st.session_state["client_info_loaded"] = client_info
                        st.session_state["client_index"] = client_info['index']
                        st.success(f"Client {client_info.get('nom_client', 'Inconnu')} chargé !")
                    else:
                        st.info("Aucun client trouvé.")
        elif client_action == "Ajouter un nouveau client":
            new_nom_client = st.text_input("Nom du client", placeholder="Tapez le nom du client", key="pos_new_nom_client")
            new_prenom_client = st.text_input("Prénom du client", placeholder="Tapez le prénom", key="pos_new_prenom_client")
            new_nom_entreprise = st.text_input("Nom de l’entreprise", placeholder="Tapez le nom de l’entreprise", key="pos_new_nom_entreprise")
            new_adresse = st.text_input("Adresse", placeholder="Tapez l’adresse", key="pos_new_adresse")
            new_telephone = st.text_input("Telephone", placeholder="Tapez le numéro de téléphone", key="pos_new_telephone")
            new_email = st.text_input("Email du client", placeholder="Tapez l’email", key="pos_new_email")
            if new_email and not validate_email(new_email):
                st.error("Format d'email invalide.")
            if new_telephone and not validate_phone(new_telephone):
                st.error("Le numéro de téléphone doit contenir 10 chiffres.")
            if st.button("Ajouter nouveau client", key="pos_add_new_client"):
                if new_nom_client:
                    new_client_info = {
                        "nom_client": new_nom_client,
                        "prenom_client": new_prenom_client,
                        "entreprise_client": new_nom_entreprise,
                        "address_client": new_adresse,
                        "telephone_client": new_telephone,
                        "email_client": new_email
                    }
                    clients_df = add_new_client(clients_df, new_client_info)
                    if save_clients(clients_df):
                        st.session_state['clients_df'] = clients_df
                        client_info = clients_df.iloc[-1].to_dict()
                        client_info['index'] = len(clients_df) - 1
                        st.session_state["client_info_loaded"] = client_info
                        st.session_state["client_index"] = client_info['index']
                        st.success("Nouveau client ajouté et chargé !")
        elif client_action == "Modifier un client chargé" and "client_info_loaded" in st.session_state:
            client_info = st.session_state["client_info_loaded"]
            edit_nom_client = st.text_input("Nom du client", value=client_info.get("nom_client", ""), placeholder="Tapez le nom du client", key="pos_edit_nom_client")
            edit_prenom_client = st.text_input("Prénom du client", value=client_info.get("prenom_client", ""), placeholder="Tapez le prénom", key="pos_edit_prenom_client")
            edit_nom_entreprise = st.text_input("Nom de l’entreprise", value=client_info.get("entreprise_client", ""), placeholder="Tapez le nom de l’entreprise", key="pos_edit_nom_entreprise")
            edit_adresse = st.text_input("Adresse", value=client_info.get("address_client", ""), placeholder="Tapez l’adresse", key="pos_edit_adresse")
            edit_telephone = st.text_input("Telephone", value=client_info.get("telephone_client", ""), placeholder="Tapez le numéro de téléphone", key="pos_edit_telephone")
            edit_email = st.text_input("Email du client", value=client_info.get("email_client", ""), placeholder="Tapez l’email", key="pos_edit_email")
            if st.button("Sauvegarder les modifications", key="pos_save_edit_client"):
                updated_client_info = {
                    "id_client": client_info["id_client"],
                    "nom_client": edit_nom_client,
                    "prenom_client": edit_prenom_client,
                    "entreprise_client": edit_nom_entreprise,
                    "address_client": edit_adresse,
                    "telephone_client": edit_telephone,
                    "email_client": edit_email
                }
                clients_df = update_client(clients_df, updated_client_info, st.session_state["client_index"])
                if save_clients(clients_df):
                    st.session_state['clients_df'] = clients_df
                    updated_client_info['index'] = st.session_state["client_index"]
                    st.session_state["client_info_loaded"] = updated_client_info
                    st.success("Client modifié avec succès !")
        if "client_info_loaded" in st.session_state:
            st.write("#### Client chargé")
            for key, value in st.session_state["client_info_loaded"].items():
                if pd.notna(value):
                    st.write(f"{key}: {value}")

    with st.expander("Articles", expanded=True):
        if 'pos_items' not in st.session_state:
            st.session_state['pos_items'] = []
        search_term = st.text_input("Rechercher un article", placeholder="Tapez le nom de l'article", key="pos_search")
        if st.button("Rechercher"):
            filtered_df = products_df[products_df['denomination'].str.contains(search_term, case=False, na=False)]
            if not filtered_df.empty:
                st.session_state['pos_filtered'] = filtered_df
        if 'pos_filtered' in st.session_state:
            selected_item = st.selectbox("Sélectionnez un article", st.session_state['pos_filtered']['denomination'], key="pos_selected")
            selected_row = st.session_state['pos_filtered'][st.session_state['pos_filtered']['denomination'] == selected_item].squeeze()
            st.write(f"Prix détail : {selected_row['prix-détail']}")
            quantity = st.number_input("Quantité", min_value=1, value=1, key="pos_quantity")
            if st.button("Ajouter"):
                item_dict = {
                    "denomination": selected_row['denomination'],
                    "reference": selected_row['reference'],
                    "Quantity": quantity,
                    "Price": selected_row['prix-détail'],
                    "category": selected_row.get('category', 'Sans Catégorie')
                }
                st.session_state['pos_items'].append(item_dict)
                st.success("Article ajouté !")
        if st.session_state['pos_items']:
            for i, item in enumerate(st.session_state['pos_items']):
                st.write(f"{item['denomination']} - {item['Quantity']} x {item['Price']}")
                if st.button(f"Supprimer {i+1}", key=f"pos_delete_{i}"):
                    st.session_state['pos_items'].pop(i)
                    st.rerun()

    with st.expander("Paiement", expanded=True):
        total_amount = sum(item['Quantity'] * item['Price'] for item in st.session_state['pos_items'])
        st.write(f"Total : {total_amount:.2f} DZD")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Process Sale"):
                client_info = st.session_state.get("client_info_loaded", None)
                if not client_info:
                    st.error("Chargez un client !")
                elif not st.session_state['pos_items']:
                    st.error("Ajoutez des articles !")
                else:
                    if update_stock(products_df, st.session_state['pos_items']):
                        transaction_id = record_transaction(client_info, st.session_state['pos_items'], "Full Payment", total_amount, total_amount, status="completed")
                        transaction_info = {"transaction_number": transaction_id, "transaction_date": datetime.now().strftime("%d/%m/%Y"), "client_id": client_info['id_client']}
                        pdf_filename = generate_receipt_pdf(transaction_info, st.session_state['pos_items'], total_amount)
                        with open(pdf_filename, "rb") as file:
                            st.download_button("Télécharger le reçu", file, pdf_filename, mime="application/pdf")
                        st.success("Vente terminée !")
                        # Reset POS page after sale
                        if 'pos_items' in st.session_state:
                            del st.session_state['pos_items']
                        if 'pos_filtered' in st.session_state:
                            del st.session_state['pos_filtered']
                        if 'client_info_loaded' in st.session_state:
                            del st.session_state['client_info_loaded']
                        st.rerun()
        with col2:
            if st.button("Effacer tout"):
                if 'pos_items' in st.session_state:
                    del st.session_state['pos_items']
                if 'pos_filtered' in st.session_state:
                    del st.session_state['pos_filtered']
                if 'client_info_loaded' in st.session_state:
                    del st.session_state['client_info_loaded']
                st.success("Tout effacé !")
                st.rerun()

def restock_page():
    st.title("Re-stocking")
    products_df = load_products()
    reference = st.text_input("Référence du produit", placeholder="Tapez la référence", key="restock_reference")
    quantity = st.number_input("Quantité à ajouter", min_value=1)
    cost_per_unit = st.number_input("Coût par unité (DZD)", min_value=0.0)
    if st.button("Restock"):
        total_cost = restock_product(products_df, reference, quantity, cost_per_unit)
        st.success(f"Produit restocké ! Coût total : {total_cost:.2f} DZD")

def expenditure_page():
    st.title("Dépenses")
    assistant_name = st.text_input("Nom de l’assistant", placeholder="Tapez le nom de l’assistant", key="exp_assistant_name")
    amount = st.number_input("Montant (DZD)", min_value=0.0)
    description = st.text_area("Description", placeholder="Tapez une description")
    if st.button("Enregistrer la dépense"):
        record_expenditure(assistant_name, amount, description)
        st.success("Dépense enregistrée !")

def staff_payment_page():
    st.title("Paiements du personnel")
    staff_name = st.text_input("Nom du personnel", placeholder="Tapez le nom du personnel", key="staff_name")
    amount = st.number_input("Montant (DZD)", min_value=0.0)
    if st.button("Enregistrer le paiement"):
        record_staff_payment(staff_name, amount)
        st.success("Paiement enregistré !")

def till_page():
    st.title("Caisse")
    balance = get_till_balance()
    st.write(f"Solde actuel de la caisse : {balance:.2f} DZD")

def main():
    st.sidebar.title("Menu")
    page = st.sidebar.radio("Aller à", ["Proforma", "POS", "Restock", "Expenditures", "Staff Payments", "Till"])
    initialize_session_state()
    products_df = load_products()
    clients_df = st.session_state['clients_df']
    if page == "Proforma":
        proforma_page(products_df, clients_df)
    elif page == "POS":
        pos_page()
    elif page == "Restock":
        restock_page()
    elif page == "Expenditures":
        expenditure_page()
    elif page == "Staff Payments":
        staff_payment_page()
    elif page == "Till":
        till_page()

if __name__ == "__main__":
    main()