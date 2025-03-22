import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from .client_management import get_client_info, add_new_client, save_clients, update_client
from .transaction_management import record_transaction
from .pdf_generator import generate_receipt_pdf, send_email
from .utils import (
    validate_email,
    validate_phone,
    find_image_path_for_color,
    get_full_image_path,
    fetch_df_from_db
)
from .product_management import load_products, update_stock, check_stock

def stock_checker_section(products_df, prefix=""):
    st.markdown('<h3 class="pos-title">🔍 Vérificateur de Stock</h3>', unsafe_allow_html=True)
    stock_search = st.text_input("Rechercher un article", key=f"{prefix}stock_search", placeholder="Référence ou nom")
    if stock_search:
        filtered_products = products_df[
            (products_df['reference'].str.contains(stock_search, case=False, na=False)) |
            (products_df['denomination'].str.contains(stock_search, case=False, na=False))
        ]
        if not filtered_products.empty:
            for _, product in filtered_products.iterrows():
                with st.container(border=True):
                    cols = st.columns([1, 3])
                    with cols[0]:
                        if pd.notna(product['images']):
                            try:
                                first_image = product['images'].split(',')[0].strip()
                                st.image(get_full_image_path(first_image), width=100)
                            except:
                                st.error("Image indisponible")
                    with cols[1]:
                        st.markdown(f"**{product['denomination']}**  \n`{product['reference']}`")
                        st.write(f"**Stock total:** {int(product['quantite_actuelle'] or 0)}")
                        if pd.notna(product['couleurs-dispo-usine']):
                            st.markdown("**Stock par couleur:**")
                            colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')]
                            for color in colors:
                                stock = int(product.get(color.lower(), 0) or 0)
                                st.write(f"- {color}: {stock}")
        else:
            st.warning("Aucun article trouvé")

def pos_page(products_df, clients_df):
    st.title("💰 Point de Vente (POS)")
    username = st.session_state['user']['username']

    # Reset Button
    if st.button("🔄 Réinitialiser Transaction", type="secondary", key="reset_transaction_button"):
        st.session_state.pos_items = []
        st.session_state.pos_client = None
        st.session_state.panier_valide = False
        st.success("Transaction réinitialisée avec succès!")
        st.rerun()

    # Search Section
    with st.container():
        search_term = st.text_input("Rechercher produit", key="search_input_pos")
        if st.button("🔍 Rechercher", key="search_button_pos"):
            pass

    # Retrieve Previous Documents
    with st.container():
        st.markdown('<div class="pos-section"><h3 class="pos-title">📜 Récupérer un Document</h3>', unsafe_allow_html=True)
        doc_type = st.selectbox("Type de Document", ["Facture", "Proforma", "Bon de Commande"], key="retrieve_doc_type_pos")
        search_term = st.text_input("Rechercher (Nom Client ou ID)", key="retrieve_search_pos", placeholder="Entrez nom client ou ID")
        
        if st.button("🔍 Chercher", key="retrieve_button_pos"):
            transactions_df = fetch_df_from_db("transactions")
            orders_df = fetch_df_from_db("orders")
            clients_df = fetch_df_from_db("clients")
            
            if doc_type == "Facture":
                filtered = transactions_df[transactions_df['status'].isin(['completed', 'deposit_paid'])]
                filtered = filtered.merge(clients_df, left_on='client_id', right_on='id_client', how='left')
            elif doc_type == "Proforma":
                filtered = transactions_df[transactions_df['status'] == 'proforma']
                filtered = filtered.merge(clients_df, left_on='client_id', right_on='id_client', how='left')
            else:
                filtered = orders_df
            
            if search_term:
                if doc_type in ["Facture", "Proforma"]:
                    filtered = filtered[
                        (filtered['nom_client'].str.contains(search_term, case=False, na=False)) |
                        (filtered['transaction_id'].astype(str).str.contains(search_term, na=False))
                    ]
                else:
                    filtered = filtered[
                        (filtered['order_id'].astype(str).str.contains(search_term, na=False))
                    ]
            if not filtered.empty:
                if doc_type in ["Facture", "Proforma"]:
                    options = [
                        f"{row['transaction_id']} - {row['nom_client'] or 'Unknown'} - {row['transaction_date']} - {row['status']}"
                        for _, row in filtered.iterrows()
                    ]
                else:
                    options = [f"{row['order_id']} - {row['order_date']}" for _, row in filtered.iterrows()]
                
                selected_doc = st.selectbox("Documents Trouvés", options, key="retrieve_select_pos")
                if st.button("Charger Document", key="load_doc_btn_pos"):
                    if doc_type in ["Facture", "Proforma"]:
                        row = filtered[filtered['transaction_id'] == int(selected_doc.split(' - ')[0])].iloc[0]
                        st.session_state.pos_items = json.loads(row['items'])
                        st.session_state.pos_client = {
                            'id_client': row['client_id'], 'nom_client': row['nom_client'],
                            'prenom_client': row['prenom_client'], 'telephone_client': row['telephone_client'],
                            'address_client': row['address_client'], 'email_client': row['email_client'],
                            'entreprise_client': row['entreprise_client']
                        }
                        date_str = row['transaction_date'].replace('/', '')
                        client_name = row['nom_client'] or 'Unknown'
                        pdf_name = f"{doc_type}-{client_name}-{row['transaction_id']}-{date_str}.pdf"
                        st.session_state.transaction_status = row['status']
                        st.session_state.remaining_amount = row.get('remaining_amount', 0.0)
                    else:
                        row = filtered[filtered['order_id'] == int(selected_doc.split(' - ')[0])].iloc[0]
                        st.session_state.pos_items = json.loads(row['items'])
                        st.session_state.pos_client = None
                        date_str = row['order_date'].replace('/', '')
                        pdf_name = f"Bon-de-commande-{row['order_id']}-{date_str}.pdf"
                    
                    pdf_path = os.path.join("generated_pdfs", pdf_name)
                    if os.path.exists(pdf_path):
                        st.session_state.generated_pdf = pdf_path
                        st.success(f"{doc_type} chargé avec succès!")
                    else:
                        st.error("PDF non trouvé.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Custom CSS Styling
    st.markdown("""
    <style>
    .pos-section {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .pos-title {
        color: #2d3436;
        border-bottom: 2px solid #90EE90;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'pos_items' not in st.session_state:
        st.session_state.pos_items = []
    if 'pos_client' not in st.session_state:
        st.session_state.pos_client = None
    if 'panier_valide' not in st.session_state:
        st.session_state.panier_valide = False
    if 'generated_pdf' not in st.session_state:
        st.session_state.generated_pdf = None
    if 'transaction_status' not in st.session_state:
        st.session_state.transaction_status = None
    if 'remaining_amount' not in st.session_state:
        st.session_state.remaining_amount = 0.0

    # Stock Checker Section
    with st.container():
        st.markdown('<div class="pos-section"><h3 class="pos-title">🔍 Vérificateur de Stock</h3>', unsafe_allow_html=True)
        stock_checker_section(products_df, "pos_")
        st.markdown('</div>', unsafe_allow_html=True)

    # Configuration Section
    with st.container():
        st.markdown('<div class="pos-section"><h3 class="pos-title">⚙️ Configuration</h3>', unsafe_allow_html=True)
        cols = st.columns([1, 1, 2])
        with cols[0]:
            price_type = "prix-détail"
            st.write("Type de prix: prix-détail")
        with cols[1]:
            discount_type = st.selectbox("Type de remise", ["Pourcentage", "Montant fixe"], key="pos_discount_type")
            discount_value = st.number_input("Valeur Remise", min_value=0.0, format="%.2f", step=0.5, key="pos_discount_value")
        with cols[2]:
            apply_tva = st.checkbox("Appliquer TVA 19%", key="pos_apply_tva")
            language = st.selectbox("Langue de la facture", ["French", "Arabic"], key="pos_language")
            notes = st.text_area("Notes", height=80, key="pos_notes")
        st.markdown('</div>', unsafe_allow_html=True)

    # Client Management Section
    with st.container():
        st.markdown('<div class="pos-section"><h3 class="pos-title">👤 Gestion Client</h3>', unsafe_allow_html=True)
        client_action = st.radio("Action", ["Nouveau Client", "Client Existant"], horizontal=True, label_visibility="collapsed")
        
        if client_action == "Client Existant":
            search_cols = st.columns([3, 1])
            with search_cols[0]:
                search_input = st.text_input("Rechercher Client", placeholder="Nom, entreprise ou téléphone", key="pos_search_client")
            with search_cols[1]:
                if st.button("🔍 Rechercher", use_container_width=True, key="pos_search_button"):
                    filtered_clients = clients_df[
                        (clients_df['nom_client'].str.contains(search_input, case=False)) |
                        (clients_df['entreprise_client'].str.contains(search_input, case=False)) |
                        (clients_df['telephone_client'].str.contains(search_input))
                    ]
                    st.session_state.filtered_clients = filtered_clients if not filtered_clients.empty else None
            
            if 'filtered_clients' in st.session_state and st.session_state.filtered_clients is not None:
                selected_client = st.selectbox("Sélectionnez Client", st.session_state.filtered_clients['nom_client'], key="pos_select_client")
                if st.button("Charger Client", type="primary", key="pos_load_client"):
                    client_info = get_client_info(st.session_state.filtered_clients, selected_client, "Nom du client")
                    if client_info:
                        st.session_state.pos_client = client_info
                        st.success("Client chargé avec succès!")
        else:
            with st.form("pos_new_client_form"):
                cols = st.columns(2)
                new_client = {
                    'nom_client': cols[0].text_input("Nom*", key="pos_new_nom"),
                    'prenom_client': cols[1].text_input("Prénom", key="pos_new_prenom"),
                    'entreprise_client': cols[0].text_input("Entreprise", key="pos_new_entreprise"),
                    'telephone_client': cols[1].text_input("Téléphone*", key="pos_new_telephone"),
                    'email_client': cols[0].text_input("Email", key="pos_new_email"),
                    'address_client': cols[1].text_input("Adresse", key="pos_new_address")
                }
                if st.form_submit_button("Enregistrer Nouveau Client", type="primary"):
                    if new_client['nom_client'] and new_client['telephone_client']:
                        clients_df = add_new_client(clients_df, new_client)
                        st.session_state.pos_client = clients_df.iloc[-1].to_dict()
                        st.success("Client enregistré avec succès!")
                    else:
                        st.error("Les champs 'Nom' et 'Téléphone' sont obligatoires.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Item Selection Section
    with st.container():
        st.markdown('<div class="pos-section"><h3 class="pos-title">🛒 Sélection d\'Articles</h3>', unsafe_allow_html=True)
        search_cols = st.columns([3, 1])
        with search_cols[0]:
            search_term = st.text_input("Recherche Articles", placeholder="Référence ou dénomination", key="pos_search_item")
        with search_cols[1]:
            if st.button("🔎 Rechercher", use_container_width=True, key="pos_search_item_button"):
                filtered = products_df[
                    (products_df['reference'].str.contains(search_term, case=False, na=False)) |
                    (products_df['denomination'].str.contains(search_term, case=False, na=False))
                ]
                st.session_state.pos_filtered = filtered if not filtered.empty else None
        
        if 'pos_filtered' in st.session_state and st.session_state.pos_filtered is not None:
            selected_product = st.selectbox("Articles Disponibles", st.session_state.pos_filtered['denomination'], key="pos_select_product")
            product = st.session_state.pos_filtered[
                st.session_state.pos_filtered['denomination'] == selected_product
            ].iloc[0]
            
            colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
            color = None
            full_selected_path = None
            
            if colors:
                color_cols = st.columns([2, 1])
                with color_cols[0]:
                    color = st.selectbox("Couleur", colors, key="pos_select_color")
                with color_cols[1]:
                    if color:
                        full_selected_path = find_image_path_for_color(product['images'], color)
                        if full_selected_path:
                            st.image(get_full_image_path(full_selected_path), caption=color, width=80)

            qty = st.number_input("Quantité", min_value=1, value=1, key="pos_qty")
            
            if st.button("➕ Ajouter au Panier", key="pos_add_to_cart"):
                stock_dispo = product.get(color.lower() if color else 'quantite_actuelle', 0)
                if qty > stock_dispo:
                    st.error(f"Stock insuffisant! Disponible: {stock_dispo}")
                else:
                    item = {
                        "reference": product['reference'],
                        "denomination": product['denomination'],
                        "Quantity": qty,
                        "Price": product[price_type],
                        "Color": color,
                        "Image": get_full_image_path(full_selected_path) if full_selected_path else None
                    }
                    st.session_state.pos_items.append(item)
                    st.success("Article ajouté au panier!")
        st.markdown('</div>', unsafe_allow_html=True)

    # Cart Display and Validation
    if st.session_state.pos_items:
        with st.container():
            st.markdown(f'<div class="pos-section"><h3 class="pos-title">📦 Panier ({len(st.session_state.pos_items)} articles)</h3>', unsafe_allow_html=True)
            
            for idx, item in enumerate(st.session_state.pos_items):
                cols = st.columns([1, 3, 1, 1])
                with cols[0]:
                    if item['Image'] and os.path.exists(item['Image']):
                        st.image(item['Image'], width=60)
                with cols[1]:
                    st.markdown(f"**{item['denomination']}**  \nRéf: `{item['reference']}`  \nCouleur: {item.get('Color', 'N/A')}")
                with cols[2]:
                    st.markdown(f"**{item['Quantity']}x**  \n{item['Price']:.2f} DZD")
                with cols[3]:
                    st.button(
                        "🗑️", 
                        key=f"cart_del_{idx}", 
                        on_click=lambda idx=idx: st.session_state.pos_items.pop(idx)
                    )          
            st.markdown("---")
            subtotal = sum(item['Price'] * item['Quantity'] for item in st.session_state.pos_items)
            
            if st.button("✅ Valider Panier", type="primary", use_container_width=True, key="pos_validate_cart"):
                stock_ok = True
                for item in st.session_state.pos_items:
                    available = int(products_df[products_df['reference'] == item['reference']].iloc[0].get(item['Color'].lower() if item['Color'] else 'quantite_actuelle', 0) or 0)
                    if available < item['Quantity']:
                        st.error(f"Stock insuffisant pour {item['denomination']} ({item['Color']})! Disponible: {available}")
                        stock_ok = False
                if stock_ok:
                    st.session_state.panier_valide = True
                    st.success("Panier validé - Prêt pour finalisation!")
                else:
                    st.warning("Veuillez ajuster les quantités ou restocker les articles.")
            
            if st.session_state.panier_valide:
                if st.button("💳 Finaliser Transaction", type="primary", use_container_width=True, disabled=not st.session_state.pos_client):
                    try:
                        subtotal = sum(item['Price'] * item['Quantity'] for item in st.session_state.pos_items)
                        discount = subtotal * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
                        taxable = subtotal - discount
                        tva_amount = taxable * 0.19 if apply_tva else 0
                        total = taxable + tva_amount

                        # Payment Scenarios
                        payment_type = st.radio("Type de Paiement", ["Paiement Complet", "Acompte"], horizontal=True, key="payment_type")
                        deposit_amount = 0.0
                        remaining_amount = 0.0
                        status = "completed"

                        if payment_type == "Acompte":
                            deposit_amount = st.number_input("Montant Acompte", min_value=0.0, max_value=total, value=min(4000.0, total), key="deposit_amount")
                            remaining_amount = total - deposit_amount
                            status = "deposit_paid"
                            st.info(f"Reste à payer à la collecte: {remaining_amount:.2f} DZD")

                        payments = {"Espèces": 0.0, "Virement": 0.0, "Chèque": 0.0}
                        if payment_type == "Paiement Complet":
                            payment_cols = st.columns(3)
                            with payment_cols[0]:
                                payments["Espèces"] = st.number_input("Espèces", min_value=0.0, value=total, key="pos_cash_full")
                            with payment_cols[1]:
                                if st.checkbox("Virement", key="pos_virement_checkbox"):
                                    payments["Virement"] = st.number_input("Montant Virement", min_value=0.0, max_value=total, value=0.0, key="pos_virement")
                                    payments["Espèces"] = total - payments["Virement"]
                            with payment_cols[2]:
                                if st.checkbox("Chèque", key="pos_cheque_checkbox"):
                                    payments["Chèque"] = st.number_input("Montant Chèque", min_value=0.0, max_value=total, value=0.0, key="pos_cheque")
                                    payments["Espèces"] = max(total - payments["Virement"] - payments["Chèque"], 0.0)
                        else:
                            payments["Espèces"] = deposit_amount

                        payment_total = sum(payments.values())
                        if payment_type == "Paiement Complet" and payment_total != total:
                            st.error("Le montant total des paiements doit égaler le total!")
                            return
                        elif payment_type == "Acompte" and payment_total != deposit_amount:
                            st.error("Le montant des paiements doit égaler l'acompte!")
                            return

                        # Update stock only on full payment
                        if status == "completed":
                            for item in st.session_state.pos_items:
                                update_stock(item['reference'], -item['Quantity'], item['Color'].lower() if item['Color'] else None)

                        payment_details = json.dumps(payments)
                        transaction_id = record_transaction(
                            client_info=st.session_state.pos_client,
                            items=st.session_state.pos_items,
                            total_amount=subtotal,
                            payment_details=payment_details,
                            final_amount=total,
                            status=status,
                            performed_by=username,
                            tva_applied=apply_tva,
                            tva_amount=tva_amount,
                            deposit_amount=deposit_amount,
                            remaining_amount=remaining_amount
                        )
                        pdf_path = generate_receipt_pdf(
                            transaction_info={
                                "transaction_number": transaction_id,
                                "transaction_date": datetime.now().strftime("%d/%m/%Y"),
                                "performed_by": username
                            },
                            items=st.session_state.pos_items,
                            subtotal=subtotal,
                            discount_amount=discount,
                            tva_amount=tva_amount,
                            total=total,
                            payment_details=payment_details,
                            client_info=st.session_state.pos_client,
                            tva_enabled=apply_tva,
                            language=language,
                            notes=notes
                        )
                        st.session_state.generated_pdf = pdf_path
                        st.success(f"Facture {transaction_id} générée! Status: {status}")
                        st.session_state.pos_items = []
                        st.session_state.panier_valide = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la finalisation: {str(e)}")

                # Handle Remaining Payment
                if st.session_state.transaction_status == "deposit_paid":
                    st.markdown("### Paiement du Solde")
                    remaining = st.session_state.remaining_amount
                    st.write(f"Reste à payer: {remaining:.2f} DZD")
                    if st.button("Payer le Solde", key="pay_remaining"):
                        remaining_payments = {"Espèces": 0.0, "Virement": 0.0, "Chèque": 0.0}
                        payment_cols = st.columns(3)
                        with payment_cols[0]:
                            remaining_payments["Espèces"] = st.number_input("Espèces", min_value=0.0, value=remaining, key="pos_cash_remain")
                        with payment_cols[1]:
                            if st.checkbox("Virement (Solde)", key="pos_virement_remain"):
                                remaining_payments["Virement"] = st.number_input("Montant Virement", min_value=0.0, max_value=remaining, value=0.0, key="pos_virement_remain")
                                remaining_payments["Espèces"] = remaining - remaining_payments["Virement"]
                        with payment_cols[2]:
                            if st.checkbox("Chèque (Solde)", key="pos_cheque_remain"):
                                remaining_payments["Chèque"] = st.number_input("Montant Chèque", min_value=0.0, max_value=remaining, value=0.0, key="pos_cheque_remain")
                                remaining_payments["Espèces"] = max(remaining - remaining_payments["Virement"] - remaining_payments["Chèque"], 0.0)

                        if sum(remaining_payments.values()) != remaining:
                            st.error("Le montant total doit égaler le solde restant!")
                        else:
                            # Update transaction
                            transactions_df = fetch_df_from_db("transactions")
                            transaction = transactions_df[transactions_df['transaction_id'] == int(selected_doc.split(' - ')[0])].iloc[0]
                            current_payments = json.loads(transaction['payment_details'])
                            for method, amount in remaining_payments.items():
                                current_payments[method] = current_payments.get(method, 0.0) + amount
                            updated_payment_details = json.dumps(current_payments)
                            for item in st.session_state.pos_items:
                                update_stock(item['reference'], -item['Quantity'], item['Color'].lower() if item['Color'] else None)
                            transaction_id = record_transaction(
                                client_info=st.session_state.pos_client,
                                items=st.session_state.pos_items,
                                total_amount=subtotal,
                                payment_details=updated_payment_details,
                                final_amount=total,
                                status="completed",
                                performed_by=username,
                                tva_applied=apply_tva,
                                tva_amount=tva_amount,
                                deposit_amount=transaction['deposit_amount'],
                                remaining_amount=0.0
                            )
                            pdf_path = generate_receipt_pdf(
                                transaction_info={
                                    "transaction_number": transaction_id,
                                    "transaction_date": datetime.now().strftime("%d/%m/%Y"),
                                    "performed_by": username
                                },
                                items=st.session_state.pos_items,
                                subtotal=subtotal,
                                discount_amount=discount,
                                tva_amount=tva_amount,
                                total=total,
                                payment_details=updated_payment_details,
                                client_info=st.session_state.pos_client,
                                tva_enabled=apply_tva,
                                language=language,
                                notes=notes
                            )
                            st.session_state.generated_pdf = pdf_path
                            st.success(f"Transaction {transaction_id} complétée!")
                            st.session_state.transaction_status = "completed"
                            st.session_state.remaining_amount = 0.0
                            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

    # PDF Actions
    if st.session_state.get('generated_pdf'):
        pdf_path = st.session_state.generated_pdf
        cols = st.columns([1, 1, 1, 2])
        with cols[0]:
            with open(pdf_path, "rb") as f:
                st.download_button("💾 Télécharger PDF", f, file_name=os.path.basename(pdf_path), mime="application/pdf")
        with cols[1]:
            st.markdown(f'<a href="file://{pdf_path}" target="_blank"><button>🖨️ Imprimer PDF</button></a>', unsafe_allow_html=True)
        with cols[2]:
            client_email = st.session_state.pos_client.get('email_client', '')
            if client_email and validate_email(client_email):
                if st.button("📧 Envoyer par email", type="primary"):
                    subject = f"Facture #{transaction_id}"
                    body = f"""Bonjour {st.session_state.pos_client.get('nom_client', '')},
                    
Voici votre facture #{transaction_id}.
Montant total: {total:.2f} DZD
Effectué par: {username}

Cordialement,
Takideco"""
                    if send_email(client_email, subject, body, pdf_path):
                        st.success("Email envoyé avec succès!")