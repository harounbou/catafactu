# modules/proforma.py
import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from modules.client_management import get_client_info, add_new_client, save_clients
from modules.transaction_management import record_transaction
from modules.pdf_generator import generate_proforma_pdf
from modules.utils import (
    #validate_email,
    validate_phone,
    find_image_path_for_color,
    get_full_image_path,
    #send_email,
    fetch_df_from_db
)
from modules.product_management import check_stock
from modules.pos import stock_checker_section

def proforma_page(products_df, clients_df):
    st.title("📄 Générateur de Facture Proforma")
    username = st.session_state['user']['username']

    # Reset Button (unchanged)
    if st.button("🔄 Réinitialiser Proforma", type="secondary"):
        st.session_state.proforma_items = []
        st.session_state.proforma_client = None
        st.session_state.panier_valide = False
        st.session_state.generated_pdf = None
        st.session_state.pop('proforma_filtered', None)
        st.session_state.pop('filtered_clients', None)
        st.success("Proforma réinitialisée avec succès!")
        st.rerun()

    # Retrieve Previous Documents (Updated)
    with st.container():
        st.markdown('<div class="proforma-section"><h3 class="proforma-title">📜 Récupérer un Document</h3>', unsafe_allow_html=True)
        doc_type = st.selectbox("Type de Document", ["Proforma", "Facture", "Bon de Commande"], key="retrieve_doc_type")
        search_term = st.text_input("Rechercher (Nom Client ou ID)", key="retrieve_search", placeholder="Entrez nom client ou ID")
        
        if st.button("🔍 Chercher", key="retrieve_button"):
            transactions_df = fetch_df_from_db("transactions")
            orders_df = fetch_df_from_db("orders")
            clients_df = fetch_df_from_db("clients")
            
            if doc_type == "Proforma":
                filtered = transactions_df[transactions_df['status'] == 'proforma']
                filtered = filtered.merge(clients_df, left_on='client_id', right_on='id_client', how='left')
            elif doc_type == "Facture":
                filtered = transactions_df[transactions_df['status'] == 'completed']
                filtered = filtered.merge(clients_df, left_on='client_id', right_on='id_client', how='left')
            else:  # Bon de Commande
                filtered = orders_df
            
            # Filter by search term if provided, otherwise show all
            if search_term:
                if doc_type in ["Proforma", "Facture"]:
                    filtered = filtered[
                        (filtered['nom_client'].str.contains(search_term, case=False, na=False)) |
                        (filtered['transaction_id'].astype(str).str.contains(search_term, na=False))
                    ]
                else:
                    filtered = filtered[
                        (filtered['order_id'].astype(str).str.contains(search_term, na=False))
                    ]
            # If no search term, show all documents
            if not filtered.empty:
                if doc_type in ["Proforma", "Facture"]:
                    options = [
                        f"{row['transaction_id']} - {row['nom_client'] or 'Unknown'} - {row['transaction_date']}"
                        for _, row in filtered.iterrows()
                    ]
                else:
                    options = [f"{row['order_id']} - {row['order_date']}" for _, row in filtered.iterrows()]
                
                selected_doc = st.selectbox("Documents Trouvés", options, key="retrieve_select")
                if st.button("Charger Document", key="load_doc_btn"):
                    if doc_type in ["Proforma", "Facture"]:
                        row = filtered[filtered['transaction_id'] == int(selected_doc.split(' - ')[0])].iloc[0]
                        st.session_state.proforma_items = json.loads(row['items'])
                        st.session_state.proforma_client = {
                            'id_client': row['client_id'], 'nom_client': row['nom_client'],
                            'prenom_client': row['prenom_client'], 'telephone_client': row['telephone_client'],
                            'address_client': row['address_client'], 'email_client': row['email_client'],
                            'entreprise_client': row['entreprise_client']
                        }
                        date_str = row['transaction_date'].replace('/', '')
                        client_name = row['nom_client'] or 'Unknown'
                        pdf_name = f"{doc_type}-{client_name}-{row['transaction_id']}-{date_str}.pdf"
                    else:
                        row = filtered[filtered['order_id'] == int(selected_doc.split(' - ')[0])].iloc[0]
                        st.session_state.proforma_items = json.loads(row['items'])
                        st.session_state.proforma_client = None
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
    .proforma-section {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .proforma-title {
        color: #2d3436;
        border-bottom: 2px solid #90EE90;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'proforma_items' not in st.session_state:
        st.session_state.proforma_items = []
    if 'proforma_client' not in st.session_state:
        st.session_state.proforma_client = None
    if 'panier_valide' not in st.session_state:
        st.session_state.panier_valide = False
    if 'generated_pdf' not in st.session_state:
        st.session_state.generated_pdf = None

    # Stock Checker Section
    with st.container():
        st.markdown('<div class="proforma-section"><h3 class="proforma-title">🔍 Vérificateur de Stock</h3>', unsafe_allow_html=True)
        stock_checker_section(products_df, "proforma_")
        st.markdown('</div>', unsafe_allow_html=True)

    # Configuration Section
    with st.container():
        st.markdown('<div class="proforma-section"><h3 class="proforma-title">⚙️ Configuration</h3>', unsafe_allow_html=True)
        cols = st.columns([1, 1, 2])
        with cols[0]:
            price_type = st.radio("Type de prix", ["prix-super-gros", "prix-gros", "prix-détail"], horizontal=True)
        with cols[1]:
            discount_type = st.selectbox("Type de remise", ["Pourcentage", "Montant fixe"])
            discount_value = st.number_input("Valeur Remise", min_value=0.0, format="%.2f", step=0.5)
        with cols[2]:
            apply_tva = st.checkbox("Appliquer TVA 19%")
            show_onama = st.checkbox("Basculer à l'Onama", help="Ajoute le numéro ONAMA au contact")
            delivery_days = st.slider("Délai Livraison (jours)", 0, 30, 5)
            custom_notes = st.text_area("Notes", height=80)
        st.markdown('</div>', unsafe_allow_html=True)

    # Client Management Section
    with st.container():
        st.markdown('<div class="proforma-section"><h3 class="proforma-title">👤 Gestion Client</h3>', unsafe_allow_html=True)
        client_action = st.radio("Action", ["Nouveau Client", "Client Existant"], horizontal=True, label_visibility="collapsed")
        
        if client_action == "Client Existant":
            search_cols = st.columns([3, 1])
            with search_cols[0]:
                search_input = st.text_input("Rechercher Client", placeholder="Nom, entreprise ou téléphone")
            with search_cols[1]:
                if st.button("🔍 Rechercher", use_container_width=True):
                    filtered_clients = clients_df[
                        (clients_df['nom_client'].str.contains(search_input, case=False)) |
                        (clients_df['entreprise_client'].str.contains(search_input, case=False)) |
                        (clients_df['telephone_client'].str.contains(search_input))
                    ]
                    st.session_state.filtered_clients = filtered_clients if not filtered_clients.empty else None
            
            if 'filtered_clients' in st.session_state and st.session_state.filtered_clients is not None:
                selected_client = st.selectbox("Sélectionnez Client", st.session_state.filtered_clients['nom_client'])
                if st.button("Charger Client", type="primary"):
                    client_info = get_client_info(st.session_state.filtered_clients, selected_client, "Nom du client")
                    if client_info:
                        st.session_state.proforma_client = client_info
                        st.success("Client chargé avec succès!")
        else:
            with st.form("new_client_form"):
                cols = st.columns(2)
                new_client = {
                    'nom_client': cols[0].text_input("Nom*", key="new_nom"),
                    'prenom_client': cols[1].text_input("Prénom", key="new_prenom"),
                    'entreprise_client': cols[0].text_input("Entreprise", key="new_entreprise"),
                    'telephone_client': cols[1].text_input("Téléphone*", key="new_telephone"),
                    'email_client': cols[0].text_input("Email", key="new_email"),
                    'address_client': cols[1].text_input("Adresse", key="new_address")
                }
                if st.form_submit_button("Enregistrer Nouveau Client", type="primary"):
                    if new_client['nom_client'] and new_client['telephone_client']:
                        clients_df = add_new_client(clients_df, new_client)
                        st.session_state.proforma_client = clients_df.iloc[-1].to_dict()
                        st.success("Client enregistré avec succès!")
                    else:
                        st.error("Les champs 'Nom' et 'Téléphone' sont obligatoires.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Item Selection Section
    with st.container():
        st.markdown('<div class="proforma-section"><h3 class="proforma-title">🛒 Sélection d\'Articles</h3>', unsafe_allow_html=True)
        search_cols = st.columns([3, 1])
        with search_cols[0]:
            search_term = st.text_input("Recherche Articles", placeholder="Référence ou dénomination")
        with search_cols[1]:
            if st.button("🔎 Rechercher", use_container_width=True):
                filtered = products_df[
                    (products_df['reference'].str.contains(search_term, case=False, na=False)) |
                    (products_df['denomination'].str.contains(search_term, case=False, na=False))
                ]
                st.session_state.proforma_filtered = filtered if not filtered.empty else None
        
        if 'proforma_filtered' in st.session_state and st.session_state.proforma_filtered is not None:
            selected_product = st.selectbox("Articles Disponibles", st.session_state.proforma_filtered['denomination'])
            product = st.session_state.proforma_filtered[
                st.session_state.proforma_filtered['denomination'] == selected_product
            ].iloc[0]
            
            colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
            color = None
            full_selected_path = None
            
            if colors:
                color_cols = st.columns([2, 1])
                with color_cols[0]:
                    color = st.selectbox("Couleur", colors)
                with color_cols[1]:
                    if color:
                        full_selected_path = find_image_path_for_color(product['images'], color)
                        if full_selected_path:
                            st.image(get_full_image_path(full_selected_path), caption=color, width=80)

            qty = st.number_input("Quantité", min_value=1, value=1)
            
            if st.button("➕ Ajouter au Panier", type="primary", use_container_width=True):
                item = {
                    "reference": product['reference'],
                    "denomination": product['denomination'],
                    "Quantity": qty,
                    "Price": product[price_type],
                    "Color": color,
                    "Image": get_full_image_path(full_selected_path) if full_selected_path else None
                }
                st.session_state.proforma_items.append(item)
                st.success("Article ajouté au panier!")
        st.markdown('</div>', unsafe_allow_html=True)

    # Cart Display and Validation
    if st.session_state.proforma_items:
        with st.container():
            st.markdown(f'<div class="proforma-section"><h3 class="proforma-title">📦 Panier ({len(st.session_state.proforma_items)} articles)</h3>', unsafe_allow_html=True)
            
            for idx, item in enumerate(st.session_state.proforma_items):
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
                        key=f"del_{idx}", 
                        on_click=lambda idx=idx: st.session_state.proforma_items.pop(idx)
                    )
            
            st.markdown("---")
            subtotal = sum(item['Price'] * item['Quantity'] for item in st.session_state.proforma_items)
            
            if st.button("✅ Valider Panier", type="primary", use_container_width=True):
                st.session_state.panier_valide = True
                st.success("Panier validé - Prêt pour génération!")
            
            if st.session_state.panier_valide:
                if st.button("📄 Générer Proforma", type="primary", use_container_width=True, disabled=not st.session_state.proforma_client):
                    try:
                        subtotal = sum(item['Price'] * item['Quantity'] for item in st.session_state.proforma_items)
                        discount = subtotal * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
                        taxable = subtotal - discount
                        tva_amount = taxable * 0.19 if apply_tva else 0
                        total = taxable + tva_amount

                        transaction_id = record_transaction(
                            client_info=st.session_state.proforma_client,
                            items=st.session_state.proforma_items,
                            total_amount=subtotal,
                            payment_details="Proforma",
                            final_amount=0,
                            status="proforma",
                            performed_by=username,
                            tva_applied=apply_tva,
                            tva_amount=tva_amount
                        )
                        
                        pdf_path = generate_proforma_pdf(
                            items=st.session_state.proforma_items,
                            price_type=price_type,
                            client_info=st.session_state.proforma_client,
                            transaction_info={
                                "transaction_number": transaction_id,
                                "transaction_date": datetime.now().strftime("%d/%m/%Y"),
                                "performed_by": username
                            },
                            apply_tva=apply_tva,
                            discount_type=discount_type,
                            discount_value=discount_value,
                            show_onama=show_onama,
                            delivery_days=delivery_days,
                            notes=custom_notes
                        )

                        if os.path.exists(pdf_path):
                            st.session_state.generated_pdf = pdf_path
                            st.success(f"Proforma {transaction_id} générée avec succès!")
                        else:
                            st.error("Échec de la génération du PDF - fichier non trouvé")
                            
                    except Exception as e:
                        st.error(f"Erreur lors de la génération: {str(e)}")
            
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
       # with cols[2]:
       #    client_email = st.session_state.proforma_client.get('email_client', '')
       #   if client_email and validate_email(client_email):
       #      if st.button("📧 Envoyer par email", type="primary"):
       #         subject = f"Facture Proforma #{transaction_id}"
       #        body = f"""Bonjour {st.session_state.proforma_client.get('nom_client', '')},
                    
#Voici votre facture proforma #{transaction_id}.
#Montant total: {total:.2f} DZD
#Effectué par: {username}

#Cordialement,
#Takideco"""
#                    if send_email(client_email, subject, body, pdf_path):
 #                       st.success("Email envoyé avec succès!")