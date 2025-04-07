## modules/pos.py
import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from .client_management import get_client_info, add_new_client, save_clients, update_client
from .transaction_management import record_transaction
from .pdf_generator import generate_receipt_pdf, generate_order_pdf, generate_reservation_pdf
from modules.product_management import COLOR_COLUMNS, update_stock
from .utils import (
    get_db_connection,
    find_image_path_for_color,
    get_full_image_path,
    fetch_df_from_db,
    get_db_color_name
)

def replace_nan_with_none(data):
    """Recursively replace NaN with None in data structures for JSON serialization"""
    if isinstance(data, dict):
        return {k: replace_nan_with_none(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_nan_with_none(i) for i in data]
    elif pd.isna(data):
        return None
    return data

# Price validation logic from brainstorm suggestion
price_type_mapping = {
    "prix-super-gros": "prix-super-gros",
    "prix-gros": "prix-gros", 
    "prix-détail": "prix-détail"
}

def get_price(product, price_type):
    """Retrieve price based on price type with validation."""
    try:
        return product[price_type_mapping[price_type]]
    except KeyError:
        st.error("Invalid price type configuration")
        return 0

def display_stock_matrix(product, colors):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {', '.join(COLOR_COLUMNS)}, quantite_actuelle FROM products WHERE reference = ?", (product['reference'],))
    db_product = dict(cursor.fetchone())
    conn.close()

    total_quantity = db_product['quantite_actuelle']
    st.write(f"**Stock Total ({product['denomination']})**: {total_quantity} unités")

    if colors:
        st.write("**Disponibilité par couleur**:")
        num_cols = 4
        color_stock = {c: db_product.get(get_db_color_name(c), 0) for c in colors}
        color_list = list(color_stock.items())
        num_rows = (len(color_list) + num_cols - 1) // num_cols
        for row in range(num_rows):
            cols = st.columns(num_cols)
            for col_idx, col in enumerate(cols):
                idx = row * num_cols + col_idx
                if idx < len(color_list):
                    color, qty = color_list[idx]
                    with col:
                        st.markdown(
                            f"<div>{color}: {qty} unités</div>",
                            unsafe_allow_html=True
                        )
                        if qty < 5:
                            st.warning(f"⚠️ Stock faible pour {color}: {qty} unités")

def stock_checker_section(products_df, prefix=""):
    """Display a standalone stock checker with enhanced stock features."""
    st.subheader("Vérifier la Disponibilité")
    
    product_options = ["Sélectionnez un produit..."] + products_df['denomination'].tolist()
    selected_product = st.selectbox("Produit", product_options, key=f"{prefix}stock_product")
    
    if selected_product != "Sélectionnez un produit...":
        product = products_df[products_df['denomination'] == selected_product].iloc[0]
        colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
        display_stock_matrix(product, colors)

def process_transaction(cart, client_name, sale_type, deduct_stock=True):
    conn = get_db_connection()
    try:
        with conn:
            for item in cart:
                if deduct_stock:
                    update_stock(item['reference'], -item['Quantity'], item['Color'].lower() if item['Color'] else None, conn=conn)
            # Rest of your transaction logic (e.g., record_transaction)
        st.success("Transaction processed successfully!")
    except Exception as e:
        st.error(f"Transaction failed: {str(e)}")
    finally:
        conn.close()

def pos_page(products_df, clients_df):
    """
    Render the Point of Sale (POS) page in Streamlit for issuing receipts and managing transactions.
    """
    st.title("💰 Point de Vente (POS)")
    username = st.session_state['user']['username']

    # Initialize session state
    pos_state_defaults = {
        'pos_items': [],
        'pos_client': None,
        'panier_valide': False,
        'pos_generated_pdf': None,
        'transaction_status': None,
        'remaining_amount': 0.0,
        'payment_type': None,
        'reservation_expiry': datetime.now() + timedelta(days=3)
    }
    for key, val in pos_state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Reset Transaction
    if st.button("🔄 Réinitialiser Transaction", type="secondary", key="reset_transaction_button"):
        reset_keys = [
            'pos_items', 'pos_client', 'panier_valide', 'pos_generated_pdf',
            'transaction_status', 'remaining_amount', 'payment_type',
            'reservation_expiry', 'pos_filtered', 'filtered_clients',
            'pos_price_type', 'pos_discount_type', 'pos_discount_value',
            'pos_apply_tva', 'pos_language', 'pos_notes', 'pos_search_client',
            'pos_select_client', 'pos_search_item', 'pos_select_product',
            'pos_select_color', 'pos_qty', 'pos_transaction_type',
            'pos_payment_option', 'deposit_amount', 'deposit_percent'
        ]
        for key in reset_keys:
            if key in st.session_state:
                del st.session_state[key]
        for key, val in pos_state_defaults.items():
            st.session_state[key] = val
        st.success("Transaction complètement réinitialisée!")
        st.rerun()

    # Styling
    st.markdown("""
    <style>
    .pos-section { border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .pos-title { color: #2d3436; border-bottom: 2px solid #90EE90; padding-bottom: 0.5rem; margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)

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
            price_type = st.radio("Type de prix", ["prix-super-gros", "prix-gros", "prix-détail"], horizontal=True, key="pos_price_type")
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
        default_index = 1 if st.session_state.pos_client else 0
        client_action = st.radio("Action", ["Nouveau Client", "Client Existant"], index=default_index, horizontal=True, label_visibility="collapsed")
        
        if st.session_state.pos_client:
            st.write(f"Client sélectionné: {st.session_state.pos_client['nom_client']}")
        
        if client_action == "Client Existant":
            search_input = st.text_input("Rechercher Client", placeholder="Nom, entreprise ou téléphone", key="pos_search_client")
            if st.button("🔍 Rechercher", key="pos_search_button"):
                filtered_clients = clients_df[
                    (clients_df['nom_client'].str.contains(search_input, case=False, na=False)) |
                    (clients_df['entreprise_client'].str.contains(search_input, case=False, na=False)) |
                    (clients_df['telephone_client'].str.contains(search_input, na=False))
                ]
                st.session_state.filtered_clients = filtered_clients if not filtered_clients.empty else None
            if 'filtered_clients' in st.session_state and st.session_state.filtered_clients is not None:
                selected_client = st.selectbox("Sélectionnez Client", st.session_state.filtered_clients['nom_client'], key="pos_select_client")
                if st.button("Charger Client", type="primary", key="pos_load_client"):
                    client_info = get_client_info(st.session_state.filtered_clients, selected_client, "Nom du client")
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
        search_term = st.text_input("Recherche Articles", placeholder="Référence ou dénomination", key="pos_search_item")
        if st.button("🔎 Rechercher", key="pos_search_item_button"):
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
                        image_path = get_full_image_path(full_selected_path) if full_selected_path else None
                        if image_path and os.path.exists(image_path):
                            st.image(image_path, caption=color, width=80)
                        else:
                            st.warning(f"Image pour {color} non trouvée.")
            
            display_stock_matrix(product, colors)
            
            qty = st.number_input("Quantité", min_value=1, value=1, key="pos_qty")
            
            if st.button("➕ Ajouter au Panier", type="primary", key="pos_add_to_cart"):
                db_color = get_db_color_name(color).lower() if color else None
                stock_dispo = int(product[db_color]) if db_color and db_color in product else int(product['quantite_actuelle'] or 0)
                price = get_price(product, price_type)  # Use get_price for validation
                if qty > stock_dispo:
                    st.warning(f"Stock insuffisant ({stock_dispo} disponible). Utilisez 'Commande Personnalisée' ou 'Achat en Compte'.")
                if price <= 0:
                    st.error(f"Prix invalide pour {product['denomination']} ({price_type}).")
                else:
                    st.session_state.pos_items.append({
                        "reference": product['reference'],
                        "denomination": product['denomination'],
                        "Quantity": qty,
                        "Price": price,
                        "Color": color,
                        "Image": image_path if image_path and os.path.exists(image_path) else None
                    })
                    st.success("Article ajouté au panier!")
        st.markdown('</div>', unsafe_allow_html=True)

    # Cart and Transaction Finalization
    if st.session_state.pos_items:
        with st.container():
            st.markdown(f'<div class="pos-section"><h3 class="pos-title">📦 Panier ({len(st.session_state.pos_items)} articles)</h3>', unsafe_allow_html=True)
            for idx, item in enumerate(st.session_state.pos_items):
                cols = st.columns([1, 3, 1, 1])
                with cols[0]:
                    if item['Image'] and os.path.exists(item['Image']):
                        st.image(item['Image'], width=60)
                    else:
                        st.warning(f"Image manquante pour {item['denomination']}.")
                with cols[1]:
                    st.markdown(f"**{item['denomination']}**  \nRéf: `{item['reference']}`  \nCouleur: {item.get('Color', 'N/A')}")
                with cols[2]:
                    st.markdown(f"**{item['Quantity']}x**  \n{item['Price']:.2f} DZD")
                with cols[3]:
                    st.button("🗑️", key=f"cart_del_{idx}", on_click=lambda i=idx: st.session_state.pos_items.pop(i))
            
            st.markdown("---")
            subtotal = sum(item['Price'] * item['Quantity'] for item in st.session_state.pos_items)
            discount = subtotal * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
            taxable = subtotal - discount
            tva_amount = taxable * 0.19 if apply_tva else 0
            total = taxable + tva_amount
            st.subheader("Récapitulatif de la Transaction")
            st.write(f"**Subtotal:** {subtotal:.2f} DZD")
            st.write(f"**Remise:** {discount:.2f} DZD")
            st.write(f"**TVA (19%):** {tva_amount:.2f} DZD" if apply_tva else "**TVA:** Non appliquée")
            st.write(f"**Total:** {total:.2f} DZD")

            if st.button("✅ Valider Panier", type="primary", use_container_width=True, key="pos_validate_cart"):
                stock_ok = True
                for item in st.session_state.pos_items:
                    product = products_df[products_df['reference'] == item['reference']].iloc[0]
                    db_color = get_db_color_name(item['Color']).lower() if item['Color'] else None
                    stock = int(product[db_color]) if db_color and db_color in product else int(product['quantite_actuelle'] or 0)
                    if item['Quantity'] > stock:
                        st.error(f"Stock insuffisant pour {item['denomination']} ({stock} disponible)")
                        stock_ok = False
                        break
                if stock_ok:
                    st.session_state.panier_valide = True
                    st.success("Panier validé - Prêt pour finalisation!")
                else:
                    st.warning("Ajustez le panier ou choisissez un autre type de transaction.")

            if st.session_state.panier_valide:
                with st.container():
                    st.markdown('<div class="pos-section"><h3 class="pos-title">💳 Finaliser Transaction</h3>', unsafe_allow_html=True)
                    if not st.session_state.pos_client:
                        st.error("Veuillez sélectionner ou ajouter un client avant de finaliser.")
                    else:
                        transaction_types = ["Achat Immédiat", "Commande Personnalisée", "Achat en Compte", "Générer Bon de Commande"]
                        scenario = st.radio("Type de Transaction", transaction_types, key="pos_transaction_type")
                        
                        payment_methods = ["Espèces", "Virement", "CCP", "Chèque"]
                        payments = {}
                        payment_cols = st.columns(len(payment_methods))
                        for i, method in enumerate(payment_methods):
                            with payment_cols[i]:
                                payments[method] = st.number_input(f"{method}", min_value=0.0, value=0.0, key=f"payment_{method.lower()}")

                        total_paid = sum(payments.values())
                        deposit_amount = 0.0
                        remaining_amount = total - total_paid if total_paid < total else 0.0

                        def process_transaction(doc_type, status, receipt_watermark, deduct_stock=False):
                            if deduct_stock:
                                for item in st.session_state.pos_items:
                                    update_stock(item['reference'], -item['Quantity'], item['Color'].lower() if item['Color'] else None)
                            
                            with st.spinner("Enregistrement de la transaction..."):
                                transaction_id = record_transaction(
                                    client_info=replace_nan_with_none(st.session_state.pos_client),
                                    items=replace_nan_with_none(st.session_state.pos_items),
                                    total_amount=subtotal,
                                    payment_details=replace_nan_with_none(payments),
                                    final_amount=total,
                                    status=status,
                                    performed_by=username,
                                    tva_applied=apply_tva,
                                    tva_amount=tva_amount,
                                    deposit_amount=deposit_amount,
                                    remaining_amount=remaining_amount
                                )
                                
                                pdf_paths = []
                                if doc_type == "Facture":
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
                                        payment_details=json.dumps(payments),
                                        client_info=st.session_state.pos_client,
                                        tva_enabled=apply_tva,
                                        language=language,
                                        notes=notes,
                                        deposit_amount=deposit_amount,
                                        remaining_amount=remaining_amount,
                                        watermark="PAYÉ" if status == "completed" else receipt_watermark
                                    )
                                    pdf_paths.append(pdf_path)
                                elif doc_type in ["Bon de Commande", "Bon d'Achat"]:
                                    order_pdf_path = generate_order_pdf(
                                        order_id=transaction_id,
                                        city="Unknown",
                                        order_date=datetime.now().strftime("%d/%m/%Y"),
                                        delivery_address="To be specified",
                                        items=st.session_state.pos_items,
                                        shipping_method="To be specified",
                                        payment_option="Partial Payment" if deposit_amount > 0 else "Full Payment",
                                        created_by=username,
                                        watermark=None
                                    )
                                    pdf_paths.append(order_pdf_path)
                                    
                                    if status == "deposit_paid":
                                        receipt_pdf_path = generate_receipt_pdf(
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
                                            payment_details=json.dumps(payments),
                                            client_info=st.session_state.pos_client,
                                            tva_enabled=apply_tva,
                                            language=language,
                                            notes=notes,
                                            deposit_amount=deposit_amount,
                                            remaining_amount=remaining_amount,
                                            watermark=receipt_watermark
                                        )
                                        pdf_paths.append(receipt_pdf_path)
                                
                                st.session_state.pos_generated_pdf = pdf_paths
                                st.session_state.transaction_status = status
                                st.session_state.remaining_amount = remaining_amount
                                st.success(f"Transaction {transaction_id} enregistrée! Statut: {status}")
                                st.session_state.pos_items = []
                                st.session_state.panier_valide = False
                                st.rerun()

                        if scenario == "Générer Bon de Commande":
                            if st.button("Générer Bon de Commande", type="primary", key="generate_order"):
                                transaction_id = record_transaction(
                                    client_info=replace_nan_with_none(st.session_state.pos_client),
                                    items=replace_nan_with_none(st.session_state.pos_items),
                                    total_amount=subtotal,
                                    payment_details={},
                                    final_amount=total,
                                    status="order_generated",
                                    performed_by=username,
                                    tva_applied=apply_tva,
                                    tva_amount=tva_amount,
                                    deposit_amount=0.0,
                                    remaining_amount=0.0
                                )
                                order_pdf_path = generate_order_pdf(
                                    order_id=transaction_id,
                                    city="Unknown",
                                    order_date=datetime.now().strftime("%d/%m/%Y"),
                                    delivery_address="To be specified",
                                    items=st.session_state.pos_items,
                                    shipping_method="To be specified",
                                    payment_option="Non applicable",
                                    created_by=username,
                                    watermark=""
                                )
                                st.session_state.pos_generated_pdf = [order_pdf_path]
                                st.session_state.transaction_status = "order_generated"
                                st.success(f"Bon de Commande {transaction_id} généré avec succès!")
                                st.session_state.pos_items = []
                                st.session_state.panier_valide = False
                                st.rerun()

                        elif scenario == "Achat Immédiat":
                            stock_ok = all(
                                int(products_df[products_df['reference'] == item['reference']].iloc[0].get(
                                    get_db_color_name(item['Color']).lower() if item['Color'] else 'quantite_actuelle', 0) or 0
                                ) >= item['Quantity']
                                for item in st.session_state.pos_items
                            )
                            if not stock_ok:
                                st.error("Stock insuffisant pour un Achat Immédiat!")
                            elif st.button("Finaliser Paiement Complet", type="primary", key="finalize_full"):
                                if total_paid != total:
                                    st.error(f"Le total payé ({total_paid:.2f} DZD) doit égaler le total ({total:.2f} DZD)!")
                                else:
                                    process_transaction(
                                        doc_type="Facture",
                                        status="completed",
                                        receipt_watermark="PAYÉ",
                                        deduct_stock=True
                                    )

                        elif scenario == "Commande Personnalisée":
                            payment_option = st.radio("Option de Paiement", ["Paiement Complet", "Acompte"], key="pos_payment_option")
                            if payment_option == "Paiement Complet":
                                if st.button("Finaliser Paiement Complet", type="primary", key="finalize_custom_full"):
                                    if total_paid != total:
                                        st.error(f"Le total payé ({total_paid:.2f} DZD) doit égaler le total ({total:.2f} DZD)!")
                                    else:
                                        process_transaction(
                                            doc_type="Facture",
                                            status="completed",
                                            receipt_watermark="PAYÉ",
                                            deduct_stock=True
                                        )
                            else:
                                deposit_amount = st.number_input("Montant de l'acompte", min_value=0.0, max_value=total, 
                                                               value=total * 0.5, key="deposit_amount")
                                remaining_amount = total - deposit_amount
                                st.info(f"Reste à payer: {remaining_amount:.2f} DZD (à la collecte)")
                                if st.button("Finaliser Acompte", type="primary", key="finalize_deposit"):
                                    if total_paid > total:
                                        st.error(f"Le total payé ({total_paid:.2f} DZD) ne peut pas dépasser le total ({total:.2f} DZD)!")
                                    else:
                                        process_transaction(
                                            doc_type="Bon de Commande",
                                            status="deposit_paid",
                                            receipt_watermark="Paiement Partiel Reçu - Solde à Payer à la Livraison",
                                            deduct_stock=False
                                        )

                        elif scenario == "Achat en Compte":
                            deposit_amount = st.number_input(
                                "Montant de l'acompte", 
                                min_value=0.0, 
                                max_value=total, 
                                value=min(total * 0.3, total),
                                key="deposit_amount"
                            )
                            remaining_amount = total - deposit_amount
                            st.info(f"Acompte: {deposit_amount:.2f} DZD | Reste à payer: {remaining_amount:.2f} DZD")
                            if st.button("Finaliser Acompte", type="primary", key="finalize_account"):
                                if total_paid > total:
                                    st.error(f"Le total payé ({total_paid:.2f} DZD) ne peut pas dépasser le total ({total:.2f} DZD)!")
                                else:
                                    process_transaction(
                                        doc_type="Bon d'Achat",
                                        status="deposit_paid",
                                        receipt_watermark="Bon d'Achat - Acompte Versé",
                                        deduct_stock=False
                                    )

                    st.markdown('</div>', unsafe_allow_html=True)

            # Handle Remaining Payment
            if st.session_state.transaction_status in ["deposit_paid"] and st.session_state.remaining_amount > 0:
                with st.container():
                    st.markdown('<div class="pos-section"><h3 class="pos-title">💳 Paiement du Solde</h3>', unsafe_allow_html=True)
                    st.write(f"Reste à payer: {st.session_state.remaining_amount:.2f} DZD")
                    payment_methods = ["Espèces", "Virement", "CCP", "Chèque"]
                    remaining_payments = {}
                    payment_cols = st.columns(len(payment_methods))
                    for i, method in enumerate(payment_methods):
                        with payment_cols[i]:
                            remaining_payments[method] = st.number_input(f"{method} (Solde)", min_value=0.0, value=0.0, 
                                                                        key=f"remaining_payment_{method.lower()}")

                    total_remaining_paid = sum(remaining_payments.values())
                    if st.button("Payer le Solde", type="primary", key="pay_remaining"):
                        if total_remaining_paid != st.session_state.remaining_amount:
                            st.error(f"Le total payé ({total_remaining_paid:.2f} DZD) doit égaler le solde restant ({st.session_state.remaining_amount:.2f} DZD)!")
                        else:
                            transactions_df = fetch_df_from_db("transactions")
                            transaction = transactions_df[transactions_df['status'] == st.session_state.transaction_status].iloc[-1]
                            current_payments = json.loads(transaction['payment_details'])
                            for method, amount in remaining_payments.items():
                                current_payments[method] = current_payments.get(method, 0.0) + amount
                            for item in st.session_state.pos_items:
                                update_stock(item['reference'], -item['Quantity'], item['Color'].lower() if item['Color'] else None)
                            process_transaction(
                                doc_type="Facture",
                                status="completed",
                                receipt_watermark="PAYÉ",
                                deduct_stock=True
                            )
                    st.markdown('</div>', unsafe_allow_html=True)

    # PDF Download
    if st.session_state.get('pos_generated_pdf'):
        pdf_paths = st.session_state.pos_generated_pdf
        if isinstance(pdf_paths, str):
            pdf_paths = [pdf_paths]
        if len(pdf_paths) == 1:
            pdf_path = pdf_paths[0]
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="💾 Télécharger le Document",
                    data=f,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    key="download_single_pdf"
                )
        elif len(pdf_paths) == 2:
            for pdf_path in pdf_paths:
                pdf_filename = os.path.basename(pdf_path)
                if "Facture" in pdf_filename:
                    label = "💾 Télécharger la Facture"
                elif "BonDeCommande" in pdf_filename:
                    label = "💾 Télécharger le Bon de Commande"
                elif "BonDAchat" in pdf_filename:
                    label = "💾 Télécharger le Bon d'Achat"
                else:
                    label = f"💾 Télécharger {pdf_filename}"
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label=label,
                        data=f,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        key=f"download_{pdf_filename}"
                    )
        else:
            st.warning("Nombre inattendu de fichiers PDF générés. Contactez le support.")