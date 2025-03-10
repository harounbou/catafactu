# pos.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from .client_management import get_client_info, add_new_client, save_clients, update_client
from .product_management import load_products, update_stock
from .transaction_management import record_transaction, fetch_df_from_db
from .pdf_generator import generate_receipt_pdf
from .utils import validate_email, validate_phone, find_image_path_for_color, get_full_image_path

def stock_checker_section(products_df, section_key_prefix=""):
    with st.expander("Vérificateur de Stock", expanded=False):
        search_term = st.text_input("Rechercher par nom ou référence", placeholder="Tapez le nom ou la référence", key=f"{section_key_prefix}stock_search")
        if st.button("Vérifier", key=f"{section_key_prefix}stock_check"):
            filtered_df = products_df[
                products_df['denomination'].str.contains(search_term, case=False, na=False) |
                products_df['reference'].str.contains(search_term, case=False, na=False)
            ]
            if not filtered_df.empty:
                for _, row in filtered_df.iterrows():
                    st.write(f"**{row['denomination']} ({row['reference']})**")
                    st.write(f"- Stock Total: {int(row['quantite_actuelle'])} unités")
                    colors = [color.strip() for color in row['couleurs-dispo-usine'].split(',')] if pd.notna(row['couleurs-dispo-usine']) else []
                    for color in colors:
                        color_lower = color.lower()
                        if color_lower in row.index and pd.notna(row[color_lower]):
                            stock = int(row[color_lower])
                            image_path = get_full_image_path(find_image_path_for_color(row['images'], color))
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                if image_path:
                                    st.image(image_path, width=50)
                                else:
                                    st.write("Image non disponible")
                            with col2:
                                st.write(f"- {color}: {stock} unités")
                                if stock <= 5:
                                    st.warning(f"Alerte: Stock faible pour {color} ({stock} unités restantes)")
                    if row['quantite_actuelle'] <= 5:
                        st.warning(f"Alerte: Stock total faible ({int(row['quantite_actuelle'])} unités restantes)")
            else:
                st.error("Aucun article trouvé.")

def pos_page():
    st.title("Point de Vente (POS)")
    if 'transaction_number' not in st.session_state:
        transactions_df = fetch_df_from_db('transactions')
        st.session_state['transaction_number'] = transactions_df["transaction_id"].max() + 1 if not transactions_df.empty else 1000
    if 'recent_clients' not in st.session_state:
        st.session_state['recent_clients'] = []
    products_df = load_products()
    clients_df = st.session_state['clients_df']
    transactions_df = fetch_df_from_db('transactions')
    username = st.session_state['user']['username']

    stock_checker_section(products_df, "pos_")

    with st.expander("Gestion des clients", expanded=True):
        client_action = st.radio("Action", ["Client récent", "Rechercher un client", "Ajouter un nouveau client", "Modifier un client chargé", "Récupérer une proforma"], key="pos_client_action")
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
                        st.session_state['recent_clients'].insert(0, client_info['id_client'])
                        if len(st.session_state['recent_clients']) > 5:
                            st.session_state['recent_clients'].pop()
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
        elif client_action == "Récupérer une proforma":
            proforma_ids = transactions_df[transactions_df['status'] == "proforma"]["transaction_id"].tolist()
            if proforma_ids:
                selected_proforma_id = st.selectbox("Sélectionnez une proforma", proforma_ids, key="pos_proforma_select")
                if st.button("Charger la proforma", key="pos_load_proforma"):
                    proforma = transactions_df[transactions_df['transaction_id'] == selected_proforma_id].iloc[0]
                    client_id = proforma['client_id']
                    client_info = clients_df[clients_df['id_client'] == client_id].iloc[0].to_dict()
                    client_info['index'] = clients_df[clients_df['id_client'] == client_id].index[0]
                    st.session_state["client_info_loaded"] = client_info
                    st.session_state["client_index"] = client_info['index']
                    st.session_state['pos_items'] = json.loads(proforma['items'])
                    st.success(f"Proforma {selected_proforma_id} chargée !")
            else:
                st.info("Aucune proforma disponible.")
        if "client_info_loaded" in st.session_state:
            st.write("#### Client chargé")
            for key, value in st.session_state["client_info_loaded"].items():
                if pd.notna(value):
                    st.write(f"{key}: {value}")

    with st.expander("Articles", expanded=True):
        if 'pos_items' not in st.session_state:
            st.session_state['pos_items'] = []
        barcode = st.text_input("Scanner ou taper la référence", placeholder="Utilisez un scanner ou entrez la référence", key="pos_barcode")
        if barcode and st.button("Ajouter par référence"):
            filtered_df = products_df[products_df['reference'] == barcode]
            if not filtered_df.empty:
                st.session_state['pos_filtered'] = filtered_df
            else:
                st.error("Référence non trouvée.")
        
        search_term = st.text_input("Rechercher par nom ou référence", placeholder="Tapez le nom ou la référence", key="pos_search")
        if st.button("Rechercher"):
            filtered_df = products_df[
                products_df['denomination'].str.contains(search_term, case=False, na=False) |
                products_df['reference'].str.contains(search_term, case=False, na=False)
            ]
            if not filtered_df.empty:
                st.session_state['pos_filtered'] = filtered_df
            else:
                st.error("Aucun article trouvé.")
        
        if 'pos_filtered' in st.session_state:
            filtered_df = st.session_state['pos_filtered']
            selected_item = st.selectbox("Sélectionnez un article", filtered_df['denomination'], key="pos_selected")
            selected_row = filtered_df[filtered_df['denomination'] == selected_item].squeeze()
            price = selected_row['prix-détail'] if pd.notna(selected_row['prix-détail']) else 0.0
            st.write(f"**Prix détail :** {price:.2f} DZD")
            
            total_stock = selected_row.get('quantite_actuelle', 0)
            st.write(f"**Stock Total Disponible :** {int(total_stock)} unités")
            if total_stock <= 5:
                st.warning(f"Alerte: Stock total faible ({int(total_stock)} unités)")
            colors = [color.strip() for color in selected_row['couleurs-dispo-usine'].split(',')] if pd.notna(selected_row['couleurs-dispo-usine']) else []
            selected_color = st.selectbox("Choisissez une couleur", colors, key="pos_color_select") if colors else None
            
            color_stock = 0
            if selected_color:
                color_lower = selected_color.lower()
                if color_lower in selected_row.index and pd.notna(selected_row[color_lower]):
                    color_stock = int(selected_row[color_lower])
                    st.write(f"**Stock pour {selected_color} :** {color_stock} unités")
                    if color_stock <= 5:
                        st.warning(f"Alerte: Stock faible pour {selected_color} ({color_stock} unités)")
                else:
                    st.warning(f"Stock pour {selected_color} non défini.")
            
            image_path = get_full_image_path(find_image_path_for_color(selected_row['images'], selected_color)) if selected_color else None
            if image_path:
                st.image(image_path, caption=f"Aperçu ({selected_color})", width=150)
            
            quantity = st.number_input("Quantité", min_value=1, value=1, key="pos_quantity")
            can_add_item = True
            if selected_color and quantity > color_stock:
                st.error(f"La quantité demandée ({quantity}) dépasse le stock disponible pour {selected_color} ({color_stock}).")
                can_add_item = False
            elif not selected_color and quantity > total_stock:
                st.error(f"La quantité demandée ({quantity}) dépasse le stock total disponible ({int(total_stock)}).")
                can_add_item = False
            
            if st.button("Ajouter", disabled=not can_add_item):
                item_dict = {
                    "denomination": selected_row['denomination'],
                    "reference": selected_row['reference'],
                    "Quantity": quantity,
                    "Price": price,
                    "Color": selected_color,
                    "Image": image_path,
                    "category": selected_row.get('category', 'Sans Catégorie')
                }
                st.session_state['pos_items'].append(item_dict)
                st.success("Article ajouté !")
        
        if st.session_state['pos_items']:
            st.write("#### Articles sélectionnés")
            for i, item in enumerate(st.session_state['pos_items']):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{item['denomination']} - {item['reference']} - Couleur: {item['Color']} - {item['Quantity']} x {item['Price']:.2f}")
                    if item.get('Image'):
                        st.image(item['Image'], width=100)
                with col2:
                    if st.button(f"Supprimer {i+1}", key=f"pos_delete_{i}"):
                        st.session_state['pos_items'].pop(i)
                        st.rerun()

    with st.expander("Paiement", expanded=True):
        if 'pos_items' in st.session_state and st.session_state['pos_items']:
            total_amount = sum(item['Quantity'] * item['Price'] for item in st.session_state['pos_items'])
            discount_type = st.radio("Type de remise", ["Aucune", "Pourcentage", "Montant fixe"], key="pos_discount_type")
            discount_value = st.number_input("Valeur de la remise", min_value=0.0, value=0.0, key="pos_discount_value") if discount_type != "Aucune" else 0.0
            discount_amount = total_amount * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
            final_amount = total_amount - discount_amount
            st.write(f"**Total avant remise :** {total_amount:.2f} DZD")
            if discount_amount > 0:
                st.write(f"**Remise :** {discount_amount:.2f} DZD")
            st.write(f"**Total à payer :** {final_amount:.2f} DZD")

            cash_amount = final_amount
            payments = {"Espèces": cash_amount, "Virement bancaire": 0.0, "Chèque": 0.0}

            st.markdown(
                f"""
                <div style="background-color: lightblue; padding: 20px; border-radius: 10px; text-align: center;">
                    <h3>Montant</h3>
                    <h1>{cash_amount:.2f} DZD</h1>
                </div>
                """,
                unsafe_allow_html=True
            )

            use_virement = st.checkbox("Montant en Virement bancaire")
            if use_virement:
                virement_amount = st.number_input("Montant en Virement bancaire", min_value=0.0, value=0.0, key="pos_virement")
                payments["Virement bancaire"] = virement_amount
            else:
                payments["Virement bancaire"] = 0.0

            use_cheque = st.checkbox("Montant en Chèque")
            if use_cheque:
                cheque_amount = st.number_input("Montant en Chèque", min_value=0.0, value=0.0, key="pos_cheque")
                payments["Chèque"] = cheque_amount
            else:
                payments["Chèque"] = 0.0

            total_other_payments = payments["Virement bancaire"] + payments["Chèque"]
            if total_other_payments > final_amount:
                st.error("Le total des paiements (Virement + Chèque) dépasse le montant à payer !")
                cash_amount = 0.0
            else:
                cash_amount = final_amount - total_other_payments
                payments["Espèces"] = cash_amount

            st.markdown(
                f"""
                <div style="background-color: lightblue; padding: 20px; border-radius: 10px; text-align: center;">
                    <h3>Montant à Payer</h3>
                    <h1>{cash_amount:.2f} DZD</h1>
                </div>
                """,
                unsafe_allow_html=True
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Process Sale"):
                    if total_other_payments > final_amount:
                        st.error("Le paiement dépasse le total à payer. Veuillez ajuster les montants.")
                    elif not st.session_state.get("client_info_loaded"):
                        st.error("Chargez un client !")
                    else:
                        if update_stock(st.session_state['pos_items']):
                            payment_details = "; ".join([f"{k}: {v:.2f}" for k, v in payments.items() if v > 0])
                            transaction_id = record_transaction(
                                st.session_state['client_info_loaded'],
                                st.session_state['pos_items'],
                                payment_details,
                                final_amount,
                                total_amount,
                                status="completed",
                                performed_by=username
                            )
                            transaction_info = {"transaction_number": transaction_id, "transaction_date": datetime.now().strftime("%d/%m/%Y"), "client_id": st.session_state['client_info_loaded']['id_client'], "performed_by": username}
                            pdf_filename = generate_receipt_pdf(transaction_info, st.session_state['pos_items'], final_amount, discount_amount, payment_details)
                            st.session_state['pos_pdf_filename'] = pdf_filename
                            st.session_state['pos_transaction_generated'] = True
                            st.session_state['recent_clients'].insert(0, st.session_state['client_info_loaded']['id_client'])
                            if len(st.session_state['recent_clients']) > 5:
                                st.session_state['recent_clients'].pop()
                            st.success("Vente terminée !")
                            st.rerun()

            if st.session_state.get('pos_transaction_generated', False):
                pdf_filename = st.session_state['pos_pdf_filename']
                with col2:
                    with open(pdf_filename, "rb") as file:
                        st.download_button("Télécharger le reçu", file, pdf_filename, mime="application/pdf", key="pos_download")
                with col3:
                    st.markdown(f'<a href="file://{pdf_filename}" target="_blank"><button>Imprimer le reçu</button></a>', unsafe_allow_html=True)

                client_email = st.session_state['client_info_loaded'].get('email_client', '')
                if client_email and validate_email(client_email):
                    if st.button("Envoyer par email", key="pos_email"):
                        subject = f"Reçu de vente #{transaction_info['transaction_number']}"
                        body = f"Bonjour {st.session_state['client_info_loaded'].get('nom_client', '')},\n\nVoici votre reçu pour la transaction #{transaction_info['transaction_number']}.\nMontant total: {final_amount:.2f} DZD\nEffectué par: {username}\n\nCordialement,\nTakideco"
                        from .app import send_email  # Import from app.py
                        if send_email(client_email, subject, body, pdf_filename):
                            st.success("Reçu envoyé par email !")

            with col2:
                if st.button("Effacer tout"):
                    if 'pos_items' in st.session_state:
                        del st.session_state['pos_items']
                    if 'pos_filtered' in st.session_state:
                        del st.session_state['pos_filtered']
                    if 'client_info_loaded' in st.session_state:
                        del st.session_state['client_info_loaded']
                    if 'pos_transaction_generated' in st.session_state:
                        del st.session_state['pos_transaction_generated']
                    if 'pos_pdf_filename' in st.session_state:
                        del st.session_state['pos_pdf_filename']
                    st.success("Tout effacé !")
                    st.rerun()
        else:
            st.info("Ajoutez des articles pour procéder au paiement.")