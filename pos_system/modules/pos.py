# modules/pos.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from .client_management import get_client_info, add_new_client, save_clients, update_client
from .product_management import load_products, update_stock, check_stock
from .transaction_management import record_transaction, fetch_df_from_db
from .pdf_generator import generate_receipt_pdf, send_email
from .utils import COLOR_MAPPING, validate_email, validate_phone, find_image_path_for_color, get_full_image_path
from .utils import get_db_color_name  # Remove local COLOR_MAPPING and get_db_color_name


def get_db_color_name(display_color):
    """Map display color names to database column names"""
    cleaned_color = display_color.lower().replace(" ", "_")
    return COLOR_MAPPING.get(cleaned_color, cleaned_color)

def stock_checker_section(products_df, prefix=""):
    stock_search = st.text_input("Rechercher un article pour vérifier le stock", 
                               key=f"{prefix}stock_search",
                               placeholder="Référence ou nom d'article")
    
    if stock_search:
        filtered_products = products_df[
            (products_df['reference'].str.contains(stock_search, case=False, na=False)) |
            (products_df['denomination'].str.contains(stock_search, case=False, na=False))
        ]
        
        if not filtered_products.empty:
            for _, product in filtered_products.iterrows():
                with st.container(border=True):
                    cols = st.columns([1, 3])
                    
                    # Image Column
                    with cols[0]:
                        if pd.notna(product['images']):
                            try:
                                first_image = product['images'].split(',')[0].strip()
                                image_path = get_full_image_path(first_image)
                                st.image(image_path, width=100)
                            except Exception as e:
                                st.error(f"Erreur de chargement d'image: {str(e)}")
                    
                    # Details Column
                    with cols[1]:
                        st.markdown(f"**{product['denomination']}**  \n`{product['reference']}`")
                        st.write(f"**Stock total:** {int(product['quantite_actuelle'] or 0)}")
                        
                        if pd.notna(product['couleurs-dispo-usine']):
                            st.markdown("**Stock par couleur:**")
                            colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')]
                            for color in colors:
                                color_lower = color.lower()
                                stock = int(product.get(color_lower, 0) or 0)
                                st.write(f"- {color}: {stock}")
        else:
            st.warning("Aucun article trouvé")

def daily_sales_report():
    """Display a daily sales report."""
    st.subheader("Rapport de Vente Quotidien")
    report_date = st.date_input("Sélectionner une date", datetime.today())
    transactions = fetch_df_from_db('transactions')
    
    # Convert transaction_date with explicit format
    transactions['transaction_date'] = pd.to_datetime(
        transactions['transaction_date'], 
        format='%d/%m/%Y %H:%M',  # Add this line to specify the correct format
        errors='coerce'
    )
    
    daily_sales = transactions[transactions['transaction_date'].dt.date == report_date]

def cash_drawer_management():
    """Manage the cash drawer."""
    st.subheader("Gestion de la Caisse")
    if 'cash_drawer' not in st.session_state:
        st.session_state.cash_drawer = 0.0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        initial_cash = st.number_input("Fond de caisse initial", min_value=0.0, value=0.0)
        if st.button("Initialiser la caisse"):
            st.session_state.cash_drawer = initial_cash
            st.success("Caisse initialisée")
    with col2:
        st.metric("Solde Actuel", f"{st.session_state.cash_drawer:.2f} DZD")
    with col3:
        withdrawal = st.number_input("Montant à retirer", min_value=0.0, value=0.0)
        if st.button("Retirer de la caisse"):
            if st.session_state.cash_drawer >= withdrawal:
                st.session_state.cash_drawer -= withdrawal
                st.success("Retrait effectué")
            else:
                st.error("Fonds insuffisants")

def pos_page():
    st.title("Point de Vente (POS)")
    
    # Initialize session state variables
    if 'transaction_number' not in st.session_state:
        transactions_df = fetch_df_from_db('transactions')
        st.session_state['transaction_number'] = transactions_df["transaction_id"].max() + 1 if not transactions_df.empty else 1000
    if 'recent_clients' not in st.session_state:
        st.session_state['recent_clients'] = []
    if 'pos_items' not in st.session_state:
        st.session_state['pos_items'] = []

    products_df = load_products()
    clients_df = st.session_state['clients_df']
    transactions_df = fetch_df_from_db('transactions')
    username = st.session_state['user']['username']

    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Transaction", "Rapport Quotidien", "Gestion Caisse"])
    
    with tab1:
        stock_checker_section(products_df, "pos_")

        # Client Management Section with Autocomplete
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
                search_input = st.text_input("Valeur de recherche", placeholder="Tapez 3 caractères minimum", key="pos_client_search_value")
                if len(search_input) >= 3:
                    if client_search_method == "Nom du client":
                        filtered_clients = clients_df[clients_df['nom_client'].str.lower().str.contains(search_input.lower())]
                    else:
                        filtered_clients = clients_df[clients_df['id_client'].astype(str).str.contains(search_input)]
                    
                    if not filtered_clients.empty:
                        client_options = [f"{row['nom_client']} {row['prenom_client']} (ID: {row['id_client']})" 
                                        for _, row in filtered_clients.iterrows()]
                        selected_client = st.selectbox("Sélectionnez un client", client_options, key="pos_client_select")
                        if selected_client:
                            client_id = int(selected_client.split("ID: ")[1].strip(")"))
                            client_info = get_client_info(clients_df, client_id, "ID Client")
                            if client_info:
                                st.session_state["client_info_loaded"] = client_info
                                st.success(f"Client {client_info.get('nom_client', 'Inconnu')} chargé !")
                    else:
                        st.info("Aucun client trouvé.")
            
            elif client_action == "Ajouter un nouveau client":
                new_nom_client = st.text_input("Nom du client", key="pos_new_nom_client")
                new_prenom_client = st.text_input("Prénom du client", key="pos_new_prenom_client")
                new_nom_entreprise = st.text_input("Nom de l’entreprise", key="pos_new_nom_entreprise")
                new_adresse = st.text_input("Adresse", key="pos_new_adresse")
                new_telephone = st.text_input("Telephone", key="pos_new_telephone")
                new_email = st.text_input("Email du client", key="pos_new_email")
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
                            st.success("Nouveau client ajouté et chargé !")
                            st.session_state['recent_clients'].insert(0, client_info['id_client'])
                            if len(st.session_state['recent_clients']) > 5:
                                st.session_state['recent_clients'].pop()
            
            elif client_action == "Modifier un client chargé" and "client_info_loaded" in st.session_state:
                client_info = st.session_state["client_info_loaded"]
                edit_nom_client = st.text_input("Nom du client", value=client_info.get("nom_client", ""), key="pos_edit_nom_client")
                edit_prenom_client = st.text_input("Prénom du client", value=client_info.get("prenom_client", ""), key="pos_edit_prenom_client")
                edit_nom_entreprise = st.text_input("Nom de l’entreprise", value=client_info.get("entreprise_client", ""), key="pos_edit_nom_entreprise")
                edit_adresse = st.text_input("Adresse", value=client_info.get("address_client", ""), key="pos_edit_adresse")
                edit_telephone = st.text_input("Telephone", value=client_info.get("telephone_client", ""), key="pos_edit_telephone")
                edit_email = st.text_input("Email du client", value=client_info.get("email_client", ""), key="pos_edit_email")
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
                        st.session_state['pos_items'] = json.loads(proforma['items'])
                        st.success(f"Proforma {selected_proforma_id} chargée !")
                else:
                    st.info("Aucune proforma disponible.")
            
            if "client_info_loaded" in st.session_state:
                st.write("#### Client chargé")
                for key, value in st.session_state["client_info_loaded"].items():
                    if pd.notna(value) and key != 'index':
                        st.write(f"{key}: {value}")

        # Articles Section with Barcode and Search (Real-time Stock Updates)
        with st.expander("Articles", expanded=True):
            barcode = st.text_input("Scanner ou taper la référence", 
                                   placeholder="Utilisez un scanner ou entrez la référence", 
                                   key="pos_barcode",
                                   autocomplete="off")
            
            if barcode:
                product = products_df[products_df['reference'] == barcode]
                if not product.empty:
                    selected_row = product.iloc[0]
                    colors = [color.strip() for color in selected_row['couleurs-dispo-usine'].split(',')] if pd.notna(selected_row['couleurs-dispo-usine']) else []
                    if colors:
                        selected_color = st.selectbox("Choisissez une couleur", colors, key="pos_color_select_barcode")
                        db_color = get_db_color_name(selected_color)
                        current_stock = check_stock(selected_row['reference'], selected_color)
                        st.write(f"Stock actuel ({selected_color}): {current_stock} unités")
                        # In the stock checker section:
                        quantity = st.number_input("Quantité", 
                          min_value=1, 
                          max_value=current_stock, 
                          value=1, 
                          key="pos_quantity_barcode",
                          step=1)  # Explicit integer steps
                        if st.button("Ajouter au panier (via barcode)", key="pos_add_barcode"):
                            item_dict = {
                                "denomination": selected_row['denomination'],
                                "reference": selected_row['reference'],
                                "Quantity": quantity,
                                "Price": selected_row['prix-détail'],
                                "ColorDisplay": selected_color,
                                "ColorDB": db_color,
                                "Image": get_full_image_path(find_image_path_for_color(selected_row['images'], selected_color))
                            }
                            st.session_state['pos_items'].append(item_dict)
                            st.success("Article ajouté via barcode !")
                            st.rerun()

            search_term = st.text_input("Rechercher par nom ou référence", key="pos_search")
            if search_term:
                filtered_df = products_df[
                    products_df['denomination'].str.contains(search_term, case=False, na=False) |
                    products_df['reference'].str.contains(search_term, case=False, na=False)
                ]
                if not filtered_df.empty:
                    selected_item = st.selectbox("Sélectionnez un article", filtered_df['denomination'], key="pos_selected")
                    selected_row = filtered_df[filtered_df['denomination'] == selected_item].iloc[0]
                    colors = [color.strip() for color in selected_row['couleurs-dispo-usine'].split(',')] if pd.notna(selected_row['couleurs-dispo-usine']) else []
                    if colors:
                        selected_color = st.selectbox("Choisissez une couleur", colors, key="pos_color_select_search")
                        db_color = get_db_color_name(selected_color)
                        current_stock = check_stock(selected_row['reference'], selected_color)
                        st.write(f"Stock actuel ({selected_color}): {current_stock} unités")
                        # In the stock checker section:
                        quantity = st.number_input("Quantité", 
                          min_value=1, 
                          max_value=current_stock, 
                          value=1, 
                          key="pos_quantity_barcode",
                          step=1)  # Explicit integer steps
                        if st.button("Ajouter au panier (via recherche)", key="pos_add_search"):
                            item_dict = {
                                "denomination": selected_row['denomination'],
                                "reference": selected_row['reference'],
                                "Quantity": quantity,
                                "Price": selected_row['prix-détail'],
                                "ColorDisplay": selected_color,
                                "ColorDB": db_color,
                                "Image": get_full_image_path(find_image_path_for_color(selected_row['images'], selected_color))
                            }
                            st.session_state['pos_items'].append(item_dict)
                            st.success("Article ajouté via recherche !")
                            st.rerun()

            # Cart Display with Real-time Stock
            if st.session_state['pos_items']:
                st.subheader("Panier")
                for i, item in enumerate(st.session_state['pos_items']):
                    with st.container():
                        current_stock = check_stock(item['reference'], item['ColorDB'])
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.markdown(f"**{item['denomination']}**")
                            st.caption(f"Réf: {item['reference']} | Couleur: {item['ColorDisplay']} | Stock: {current_stock}")
                            if item.get('Image'):
                                st.image(item['Image'], width=75)
                        with col2:
                            st.markdown(f"**{item['Quantity']} x {item['Price']:.2f} DZD**")
                            st.markdown(f"Total: **{(item['Quantity'] * item['Price']):.2f} DZD**")
                        with col3:
                            if st.button(f"❌", key=f"pos_delete_{i}"):
                                st.session_state['pos_items'].pop(i)
                                st.rerun()
                        st.divider()

        # Payment Section with TVA
        with st.expander("Paiement", expanded=True):
            if st.session_state.get('pos_items'):
                total_amount = sum(item['Quantity'] * item['Price'] for item in st.session_state['pos_items'])
                
                # TVA Toggle
                apply_tva = st.checkbox("Appliquer TVA 19%", key="pos_tva_toggle")
                if apply_tva:
                    tva_rate = 0.19
                    tva_amount = total_amount * tva_rate
                    final_amount = total_amount + tva_amount
                else:
                    tva_rate = 0.0
                    tva_amount = 0.0
                    final_amount = total_amount

                # Discount Handling
                col1, col2 = st.columns(2)
                with col1:
                    discount_type = st.radio("Type de remise", ["Aucune", "Pourcentage", "Montant fixe"], key="pos_discount_type")
                with col2:
                    discount_value = st.number_input("Valeur de la remise", min_value=0.0, value=0.0, key="pos_discount_value",
                                                    disabled=(discount_type == "Aucune"))
                discount_amount = total_amount * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
                final_amount = max(final_amount - discount_amount, 0.0)

                # Payment Distribution
                st.subheader("Répartition du paiement")
                payments = {"Espèces": final_amount, "Virement bancaire": 0.0, "Chèque": 0.0}
                cash_col, virement_col, cheque_col = st.columns(3)
                with virement_col:
                    if st.checkbox("Virement bancaire", key="pos_virement"):
                        payments["Virement bancaire"] = st.number_input("Montant virement", min_value=0.0, max_value=final_amount, value=0.0, key="pos_virement_amount")
                with cheque_col:
                    if st.checkbox("Chèque", key="pos_cheque"):
                        payments["Chèque"] = st.number_input("Montant chèque", min_value=0.0, max_value=final_amount, value=0.0, key="pos_cheque_amount")
                payments["Espèces"] = max(final_amount - payments["Virement bancaire"] - payments["Chèque"], 0.0)

                # Finalize Transaction
                if st.button("💸 Finaliser la transaction", type="primary", key="pos_finalize"):
                    if not st.session_state.get("client_info_loaded"):
                        st.error("Veuillez sélectionner un client")
                    elif payments["Espèces"] < 0:
                        st.error("Combinaison de paiement invalide")
                    else:
                        # Stock Validation
                        stock_errors = []
                        for item in st.session_state['pos_items']:
                            available = check_stock(item['reference'], item['ColorDB'])
                            if available < item['Quantity']:
                                stock_errors.append(f"{item['denomination']} - Stock insuffisant ({available} disponible)")
                        if stock_errors:
                            st.error("Erreurs de stock:")
                            for error in stock_errors:
                                st.error(error)
                        else:
                            # Update stock and record transaction
                            for item in st.session_state['pos_items']:
                                update_stock(item['reference'], -item['Quantity'], item['ColorDB'])
                            payment_details = json.dumps(payments)
                            transaction_id = record_transaction(
                                st.session_state['client_info_loaded'],
                                st.session_state['pos_items'],
                                payment_details,
                                final_amount,
                                total_amount,
                                status="completed",
                                performed_by=username,
                                tva_applied=apply_tva,
                                tva_amount=tva_amount
                            )
                            # Update cash drawer
                            if 'cash_drawer' in st.session_state:
                                st.session_state.cash_drawer += payments["Espèces"]
                            transaction_info = {
                                "transaction_number": transaction_id,
                                "transaction_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "client_id": st.session_state['client_info_loaded']['id_client'],
                                "performed_by": username
                            }
                            pdf_filename = generate_receipt_pdf(
                                transaction_info,
                                st.session_state['pos_items'],
                                final_amount,
                                discount_amount,
                                payment_details,
                                st.session_state['client_info_loaded'],
                                apply_tva
                            )
                            st.session_state['pos_pdf_filename'] = pdf_filename
                            st.success("Transaction terminée avec succès !")
                            with open(pdf_filename, "rb") as f:
                                st.download_button("📥 Télécharger le reçu", f, file_name=f"receipt_{transaction_id}.pdf", mime="application/pdf")
                            st.session_state['pos_items'] = []
                            st.rerun()

                # Transaction Summary
                st.subheader("Résumé de la transaction")
                summary_col1, summary_col2 = st.columns(2)
                with summary_col1:
                    st.metric("Total articles (HT)", f"{total_amount:.2f} DZD")
                    if apply_tva:
                        st.metric("TVA 19%", f"{tva_amount:.2f} DZD")
                    st.metric("Remise appliquée", f"-{discount_amount:.2f} DZD")
                with summary_col2:
                    st.metric("Total à payer (TTC)", f"{final_amount:.2f} DZD")

            else:
                st.info("Ajoutez des articles pour procéder au paiement")

        # Clear Cart with Confirmation
        if st.session_state.get('pos_items'):
            if st.button("🧹 Vider le panier", type="secondary", key="pos_clear_cart"):
                if st.checkbox("Confirmer la suppression du panier", key="pos_confirm_clear"):
                    for item in st.session_state['pos_items']:
                        update_stock(item['reference'], item['Quantity'], item['ColorDB'])
                    st.session_state['pos_items'] = []
                    st.success("Panier vidé avec succès !")
                    st.rerun()

    with tab2:
        daily_sales_report()

    with tab3:
        cash_drawer_management()