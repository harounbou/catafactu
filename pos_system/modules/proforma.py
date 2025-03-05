# pos_system/modules/proforma.py
import streamlit as st
import pandas as pd  # Added for pd.notna()
from .client_management import get_client_info, add_new_client, save_clients
from .transaction_management import record_transaction
from .pdf_generator import generate_proforma_pdf
from .utils import validate_email, validate_phone, find_image_path_for_color, get_full_image_path
from datetime import datetime

def proforma_page(products_df, clients_df):
    st.title("Générateur de Facture Proforma")

    with st.expander("Options de la facture", expanded=True):
        price_type = st.radio("Type de prix", ["prix-super-gros", "prix-gros", "prix-détail"], key='price_type')
        apply_tva = st.checkbox("Appliquer la TVA (19%)", value=False, key='apply_tva')
        show_onama = st.checkbox("Basculer à L'Onama", value=False, key='show_onama')
        discount_type = st.radio("Type de remise", ["Pourcentage", "Montant fixe"], key='discount_type')
        discount_value = st.number_input("Valeur de la remise", min_value=0.0, value=0.0, key='discount_value')
        delivery_days = st.selectbox("Délai de livraison (jours)", list(range(0, 31)), key='delivery_days')

    with st.expander("Ajouter des articles", expanded=True):
        if 'items' not in st.session_state:
            st.session_state['items'] = []
        categories = ['Toutes'] + sorted(products_df['category'].dropna().unique().tolist())
        selected_category = st.selectbox("Filtrer par catégorie", categories, key="category_filter")
        search_term = st.text_input("Rechercher un article par Dénomination", key="article_search")
        col1, col2 = st.columns([1, 10])
        with col1:
            pass  # No icon displayed
        with col2:
            if st.button("Rechercher l'article"):
                if search_term:
                    filtered_df = products_df[products_df['denomination'].str.contains(search_term, case=False, na=False, regex=False)]
                    if selected_category != 'Toutes':
                        filtered_df = filtered_df[filtered_df['category'] == selected_category]
                    if not filtered_df.empty:
                        st.session_state['filtered_articles'] = filtered_df
                    else:
                        st.error("Aucun article trouvé.")
                else:
                    st.warning("Veuillez entrer un terme de recherche.")

        if 'filtered_articles' in st.session_state:
            filtered_df = st.session_state['filtered_articles']
            selected_item = st.selectbox("Sélectionnez un article", filtered_df['denomination'], key="selected_item")
            selected_row = filtered_df[filtered_df['denomination'] == selected_item].squeeze()
            if price_type in selected_row.index:
                st.write(f"**Prix ({price_type}) :** {selected_row[price_type]}")
                available_stock = selected_row.get('quantite_actuelle', 0)
                st.write(f"**Stock Disponible :** {int(available_stock)} unités")
                colors = [color.strip() for color in selected_row['couleurs-dispo-usine'].split(',')] if pd.notna(selected_row['couleurs-dispo-usine']) else []
                selected_color = st.selectbox("Choisissez une couleur", colors, key="color_select") if colors else None
                image_path = get_full_image_path(find_image_path_for_color(selected_row['images'], selected_color)) if selected_color else None
                if image_path:
                    st.image(image_path, caption=f"Aperçu ({selected_color})", width=150)
                quantity = st.number_input("Quantité", min_value=1, value=1, key="quantity")
                can_add_item = quantity <= available_stock
                if not can_add_item:
                    st.error(f"La quantité demandée ({quantity}) dépasse le stock disponible ({int(available_stock)}).")
                if st.button("Ajouter l'article", key="add_article", disabled=not can_add_item):
                    item_dict = {
                        "denomination": selected_row['denomination'],
                        "reference": selected_row['reference'],
                        "Quantity": quantity,
                        "Price": selected_row[price_type],
                        "Color": selected_color,
                        "Image": image_path,
                        "category": selected_row.get('category', 'Sans Catégorie')
                    }
                    st.session_state['items'].append(item_dict)
                    st.success("Article ajouté !")
                    del st.session_state['filtered_articles']

        if st.session_state['items']:
            st.write("#### Articles sélectionnés")
            for i, item in enumerate(st.session_state['items']):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{item['denomination']} - {item['reference']} - Couleur: {item['Color']} - {item['Quantity']} x {item['Price']}")
                    if item.get('Image'):
                        st.image(item['Image'], width=100)
                with col2:
                    if st.button(f"Supprimer {i+1}", key=f"delete_item_{i}"):
                        st.session_state['items'].pop(i)
                        st.success("Article supprimé !")
                        st.rerun()

    with st.expander("Gestion des clients", expanded=True):
        client_action = st.radio("Action", ["Client récent", "Rechercher un client", "Ajouter un nouveau client", "Modifier un client chargé"], key="client_action")
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
                        if st.button(f"Charger {client_name} (ID: {client_id})", key=f"recent_{client_id}"):
                            st.session_state["client_info_loaded"] = client_info
                            st.session_state["client_index"] = client_info['index']
                            st.success(f"Client {client_name} chargé !")
        elif client_action == "Rechercher un client":
            client_search_method = st.radio("Rechercher par", ["Nom du client", "ID Client"], key="client_search_method")
            client_search_value = st.text_input("Valeur de recherche", key="client_search_value")
            if st.button("Rechercher client"):
                if client_search_value:
                    client_info = get_client_info(clients_df, client_search_value, client_search_method)
                    if client_info:
                        st.session_state["client_info_loaded"] = client_info
                        st.session_state["client_index"] = client_info['index']
                        st.success(f"Client {client_info.get('nom_client', 'Inconnu')} chargé !")
                    else:
                        st.info("Aucun client trouvé.")
        elif client_action == "Ajouter un nouveau client":
            new_nom_client = st.text_input("Nom du client", key="new_nom_client")
            new_prenom_client = st.text_input("Prénom du client", key="new_prenom_client")
            new_nom_entreprise = st.text_input("Nom de l’entreprise", key="new_nom_entreprise")
            new_adresse = st.text_input("Adresse", key="new_adresse")
            new_telephone = st.text_input("Telephone", key="new_telephone")
            new_email = st.text_input("Email du client", key="new_email")
            if new_email and not validate_email(new_email):
                st.error("Format d'email invalide.")
            if new_telephone and not validate_phone(new_telephone):
                st.error("Le numéro de téléphone doit contenir 10 chiffres.")
            if st.button("Ajouter nouveau client", key="add_new_client"):
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
            edit_nom_client = st.text_input("Nom du client", value=client_info.get("nom_client", ""), key="edit_nom_client")
            edit_prenom_client = st.text_input("Prénom du client", value=client_info.get("prenom_client", ""), key="edit_prenom_client")
            edit_nom_entreprise = st.text_input("Nom de l’entreprise", value=client_info.get("entreprise_client", ""), key="edit_nom_entreprise")
            edit_adresse = st.text_input("Adresse", value=client_info.get("address_client", ""), key="edit_adresse")
            edit_telephone = st.text_input("Telephone", value=client_info.get("telephone_client", ""), key="edit_telephone")
            edit_email = st.text_input("Email du client", value=client_info.get("email_client", ""), key="edit_email")
            if st.button("Sauvegarder les modifications", key="save_edit_client"):
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

    with st.expander("Générer la facture", expanded=True):
        client_info = st.session_state.get("client_info_loaded", {
            "nom_client": "", "prenom_client": "", "entreprise_client": "", "address_client": "", "telephone_client": "", "email_client": "", "id_client": "N/A"
        })
        transaction_info = {
            "transaction_number": st.session_state.get('transaction_number', 1000),
            "transaction_date": datetime.now().strftime("%d/%m/%Y"),
            "client_id": client_info.get("id_client", "N/A")
        }
        st.write(f"N° De transaction : {transaction_info['transaction_number']}")
        st.write(f"Date de transaction : {transaction_info['transaction_date']}")
        st.write(f"ID Client : {transaction_info['client_id']}")
        if st.button("Générer la facture proforma"):
            if st.session_state['items'] and "client_info_loaded" in st.session_state:
                total_amount = sum(item['Quantity'] * item['Price'] for item in st.session_state['items'])
                transaction_id = record_transaction(client_info, st.session_state['items'], "Proforma", 0, total_amount)
                transaction_info["transaction_number"] = transaction_id
                pdf_filename = generate_proforma_pdf(
                    st.session_state['items'], price_type, client_info, transaction_info,
                    apply_tva, discount_type, discount_value, show_onama, delivery_days
                )
                with open(pdf_filename, "rb") as file:
                    st.download_button("Télécharger la facture proforma", file, pdf_filename, mime="application/pdf")
                st.session_state['transaction_number'] = transaction_id + 1
                st.success("Facture générée !")
                del st.session_state["client_info_loaded"]
                st.session_state['items'] = []
            else:
                st.error("Ajoutez des articles et chargez un client !")