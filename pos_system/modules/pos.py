## modules/pos.py
import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from .client_management import get_client_info, add_new_client, save_clients, update_client
from .transaction_management import record_transaction
#from .pdf_generator import send_email
from .pdf_generator import generate_receipt_pdf
from .utils import get_db_color_name  # Ensure this import works
from .utils import (
   # validate_email,
    validate_phone,
    find_image_path_for_color,
    get_full_image_path,
    fetch_df_from_db
)
from .product_management import load_products, update_stock, check_stock
from .utils import get_db_color_name  # Add this import

def replace_nan_with_none(data):
    """Recursively replace NaN with None in data structures for JSON serialization"""
    if isinstance(data, dict):
        return {k: replace_nan_with_none(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_nan_with_none(i) for i in data]
    elif pd.isna(data):
        return None
    else:
        return data

def pos_page(products_df, clients_df):
    st.title("💰 Point de Vente (POS)")
    username = st.session_state['user']['username']

    # Reset Transaction
    if st.button("🔄 Réinitialiser Transaction", type="secondary", key="reset_transaction_button"):
        st.session_state.pos_items = []
        st.session_state.pos_client = None
        st.session_state.panier_valide = False
        st.session_state.generated_pdf = None
        st.session_state.transaction_status = None
        st.session_state.remaining_amount = 0.0
        st.session_state.payment_type = None
        st.success("Transaction réinitialisée avec succès!")
        st.rerun()

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
    if 'payment_type' not in st.session_state:
        st.session_state.payment_type = None

    # Styling
    st.markdown("""
    <style>
    .pos-section { border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .pos-title { color: #2d3436; border-bottom: 2px solid #90EE90; padding-bottom: 0.5rem; margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)

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

    # Client Management (unchanged for brevity, assuming it works as is)
    with st.container():
        st.markdown('<div class="pos-section"><h3 class="pos-title">👤 Gestion Client</h3>', unsafe_allow_html=True)
        client_action = st.radio("Action", ["Nouveau Client", "Client Existant"], horizontal=True, label_visibility="collapsed")
        if client_action == "Client Existant":
            # Existing client logic (simplified)
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

    # Item Selection (unchanged for brevity)
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
            color = st.selectbox("Couleur", colors, key="pos_select_color") if colors else None
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
                        "Image": find_image_path_for_color(product['images'], color) if color else None
                    }
                    st.session_state.pos_items.append(item)
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
                    available = int(products_df[products_df['reference'] == item['reference']].iloc[0].get(item['Color'].lower() if item['Color'] else 'quantite_actuelle', 0) or 0)
                    if available < item['Quantity']:
                        st.error(f"Stock insuffisant pour {item['denomination']} ({item['Color'] or 'N/A'})! Disponible: {available}")
                        stock_ok = False
                if stock_ok:
                    st.session_state.panier_valide = True
                    st.success("Panier validé - Prêt pour finalisation!")
                else:
                    st.warning("Veuillez ajuster les quantités ou restocker les articles.")

            if st.session_state.panier_valide:
                with st.container():
                    st.markdown('<div class="pos-section"><h3 class="pos-title">💳 Finaliser Transaction</h3>', unsafe_allow_html=True)
                    if not st.session_state.pos_client:
                        st.error("Veuillez sélectionner ou ajouter un client avant de finaliser.")
                    else:
                        # Scenario Selection
                        scenario = st.radio("Type de Commande", 
                                          ["En magasin (disponible)", "En magasin (à produire)", "Commande en ligne"],
                                          key="pos_scenario")
                        
                        payment_methods = ["Espèces", "Virement", "CCP"]
                        payments = {}
                        payment_cols = st.columns(len(payment_methods))
                        for i, method in enumerate(payment_methods):
                            with payment_cols[i]:
                                payments[method] = st.number_input(f"{method}", min_value=0.0, value=0.0, key=f"payment_{method.lower()}")

                        total_paid = sum(payments.values())
                        deposit_amount = 0.0
                        remaining_amount = 0.0
                        status = "completed"

                        if scenario == "En magasin (disponible)":
                            # Full payment expected if goods are available
                            if st.button("Finaliser Paiement Complet", type="primary", key="finalize_full"):
                                if total_paid != total:
                                    st.error(f"Le total payé ({total_paid:.2f} DZD) doit égaler le total ({total:.2f} DZD)!")
                                else:
                                    for item in st.session_state.pos_items:
                                        update_stock(item['reference'], -item['Quantity'], item['Color'].lower() if item['Color'] else None)
                                    process_transaction(
                                        client_info=st.session_state.pos_client,
                                        items=st.session_state.pos_items,
                                        subtotal=subtotal,
                                        discount=discount,
                                        tva_amount=tva_amount,
                                        total=total,
                                        payments=payments,
                                        status="completed",
                                        username=username,
                                        apply_tva=apply_tva,
                                        language=language,
                                        notes=notes,
                                        deposit_amount=0.0,
                                        remaining_amount=0.0
                                    )
                                    st.session_state.payment_type = "Paiement Complet"

                        elif scenario in ["En magasin (à produire)", "Commande en ligne"]:
                            # Partial payment (50% default) with remainder due later
                            default_deposit = total * 0.5
                            deposit_amount = st.number_input("Montant de l'acompte", min_value=0.0, max_value=total, 
                                                           value=default_deposit, key="deposit_amount")
                            remaining_amount = total - deposit_amount
                            status = "deposit_paid"
                            st.info(f"Reste à payer: {remaining_amount:.2f} DZD ({'à la collecte' if scenario == 'En magasin (à produire)' else 'avant expédition'})")

                            if st.button("Finaliser Acompte", type="primary", key="finalize_deposit"):
                                if total_paid != deposit_amount:
                                    st.error(f"Le total payé ({total_paid:.2f} DZD) doit égaler l'acompte ({deposit_amount:.2f} DZD)!")
                                else:
                                    process_transaction(
                                        client_info=st.session_state.pos_client,
                                        items=st.session_state.pos_items,
                                        subtotal=subtotal,
                                        discount=discount,
                                        tva_amount=tva_amount,
                                        total=total,
                                        payments=payments,
                                        status="deposit_paid",
                                        username=username,
                                        apply_tva=apply_tva,
                                        language=language,
                                        notes=notes,
                                        deposit_amount=deposit_amount,
                                        remaining_amount=remaining_amount
                                    )
                                    st.session_state.payment_type = "Acompte"

                    st.markdown('</div>', unsafe_allow_html=True)

            # Handle Remaining Payment for Deposit Transactions
            if st.session_state.transaction_status == "deposit_paid" and st.session_state.remaining_amount > 0:
                with st.container():
                    st.markdown('<div class="pos-section"><h3 class="pos-title">💳 Paiement du Solde</h3>', unsafe_allow_html=True)
                    st.write(f"Reste à payer: {st.session_state.remaining_amount:.2f} DZD")
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
                            transaction = transactions_df[transactions_df['status'] == 'deposit_paid'].iloc[-1]  # Assuming latest
                            current_payments = json.loads(transaction['payment_details'])
                            for method, amount in remaining_payments.items():
                                current_payments[method] = current_payments.get(method, 0.0) + amount
                            process_transaction(
                                client_info=st.session_state.pos_client,
                                items=st.session_state.pos_items,
                                subtotal=subtotal,
                                discount=discount,
                                tva_amount=tva_amount,
                                total=total,
                                payments=current_payments,
                                status="completed",
                                username=username,
                                apply_tva=apply_tva,
                                language=language,
                                notes=notes,
                                deposit_amount=transaction['deposit_amount'],
                                remaining_amount=0.0
                            )
                            for item in st.session_state.pos_items:
                                update_stock(item['reference'], -item['Quantity'], item['Color'].lower() if item['Color'] else None)
                            st.session_state.transaction_status = "completed"
                            st.session_state.remaining_amount = 0.0
                    st.markdown('</div>', unsafe_allow_html=True)

    # PDF Download
    if st.session_state.get('generated_pdf'):
        pdf_path = st.session_state.generated_pdf
        with open(pdf_path, "rb") as f:
            st.download_button("💾 Télécharger PDF", f, file_name=os.path.basename(pdf_path), mime="application/pdf")

def stock_checker_section(products_df, prefix=""):
    """Display a standalone stock checker for a selected product and color."""
    st.subheader("Vérifier la Disponibilité")
    
    product_options = ["Sélectionnez un produit..."] + products_df['denomination'].tolist()
    selected_product = st.selectbox("Produit", product_options, key=f"{prefix}stock_product")
    
    if selected_product != "Sélectionnez un produit...":
        product = products_df[products_df['denomination'] == selected_product].iloc[0]
        colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
        color_options = ["Sans couleur"] + colors if colors else ["Sans couleur"]
        selected_color = st.selectbox("Couleur", color_options, key=f"{prefix}stock_color")
        
        if selected_color != "Sans couleur":
            db_color = get_db_color_name(selected_color)
            available_stock = int(product.get(db_color, 0) or 0)
            color_display = selected_color
        else:
            available_stock = int(product.get('quantite_actuelle', 0) or 0)
            color_display = "N/A"
        
        st.write(f"Stock disponible pour **{selected_product}** ({color_display}) : **{available_stock}** unités")


def process_transaction(client_info, items, subtotal, discount, tva_amount, total, payments, status, username, 
                       apply_tva, language, notes, deposit_amount, remaining_amount):
    """Helper function to process and record transactions"""
    with st.spinner("Enregistrement de la transaction..."):
        transaction_id = record_transaction(
            client_info=replace_nan_with_none(client_info),
            items=replace_nan_with_none(items),
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
        pdf_path = generate_receipt_pdf(
            transaction_info={
                "transaction_number": transaction_id,
                "transaction_date": datetime.now().strftime("%d/%m/%Y"),
                "performed_by": username
            },
            items=items,
            subtotal=subtotal,
            discount_amount=discount,
            tva_amount=tva_amount,
            total=total,
            payment_details=json.dumps(payments),
            client_info=client_info,
            tva_enabled=apply_tva,
            language=language,
            notes=notes,
            deposit_amount=deposit_amount,
            remaining_amount=remaining_amount
        )
        st.session_state.generated_pdf = pdf_path
        st.session_state.transaction_status = status
        st.session_state.remaining_amount = remaining_amount
        st.success(f"Transaction {transaction_id} enregistrée avec succès! Status: {status}")
        st.session_state.pos_items = []
        st.session_state.panier_valide = False
        st.rerun()