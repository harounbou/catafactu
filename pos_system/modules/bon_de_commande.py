# modules/bon_de_commande.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from .product_management import load_products
from .transaction_management import fetch_df_from_db, get_db_connection
from .utils import find_image_path_for_color, get_full_image_path
from .pdf_generator import generate_order_pdf
import sqlite3

def initialize_orders_table():
    """Initialize the orders table in the database."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    order_date TEXT NOT NULL,
                    delivery_address TEXT,
                    items TEXT NOT NULL,
                    shipping_method TEXT NOT NULL,
                    payment_option TEXT,
                    created_by TEXT NOT NULL,
                    status TEXT DEFAULT 'pending'
                 )''')
    
    conn.commit()
    conn.close()

def save_order(city, delivery_address, items, shipping_method, payment_option, created_by):
    """Save an order to the orders table."""
    initialize_orders_table()
    conn = get_db_connection()
    c = conn.cursor()
    try:
        order_date = datetime.now().strftime("%d/%m/%Y")
        items_json = json.dumps(items)
        st.write(f"Saving order with: city={city}, date={order_date}, items={items_json}")  # Debug
        c.execute("""
            INSERT INTO orders (city, order_date, delivery_address, items, shipping_method, payment_option, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (city, order_date, delivery_address, items_json, shipping_method, payment_option, created_by))
        order_id = c.lastrowid
        conn.commit()
        st.write(f"Order saved with ID: {order_id}")  # Debug
        return order_id
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de l'enregistrement de la commande : {e}")
        return None
    finally:
        conn.close()

def update_order_status(order_id, new_status):
    """Update the status of an order."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour du statut : {e}")
        return False
    finally:
        conn.close()

def bon_de_commande_page(products_df):
    """Display and manage the Bon de Commande page."""
    st.title("Bon de Commande")
    username = st.session_state['user']['username']
    city_map = {"admin": "Alger", "eulma": "Eulmi", "alger": "Alger", "constantine": "Constantine"}
    city = city_map.get(username, "Alger")
    tab1, tab2 = st.tabs(["Créer un Bon de Commande", "Suivi des Commandes"])

    with tab1:
        order_date = datetime.now().strftime("%d/%m/%Y")
        st.write(f"**Ville :** {city} | **Date de Commande :** {order_date}")
        st.write("**Méthode par défaut :** Envoi via ONAMA à EULAM")
        known_addresses = ["Bureau Alger", "Dépôt Constantine", "Magasin Eulmi", "Inconnue pour l'instant"]
        delivery_address = st.selectbox("Adresse de Livraison", known_addresses, key="bdc_address")
        if delivery_address == "Inconnue pour l'instant":
            delivery_address = st.text_input("Adresse personnalisée", key="bdc_custom_address")

        st.subheader("Sélection des Articles")
        if 'order_items' not in st.session_state:
            st.session_state['order_items'] = []

        col1, col2 = st.columns([3, 1])
        with col1:
            selected_product = st.selectbox(
                "Produit",
                ["Sélectionnez un produit..."] + products_df['denomination'].tolist(),
                key="bdc_product_select"
            )
        with col2:
            qty = st.number_input("Quantité", min_value=1, value=1, key="bdc_qty")

        if selected_product != "Sélectionnez un produit...":
            product = products_df[products_df['denomination'] == selected_product].iloc[0]
            colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
            color = st.selectbox("Couleur", ["Sans couleur"] + colors, key="bdc_color") if colors else None
            image_path = get_full_image_path(find_image_path_for_color(product['images'], color)) if color and color != "Sans couleur" else None
            if image_path:
                st.image(image_path, caption=f"Aperçu ({color})", width=150)
            if st.button("➕ Ajouter", key="bdc_add"):
                item = {
                    "reference": product['reference'],
                    "denomination": product['denomination'],
                    "color": color if color != "Sans couleur" else None,
                    "quantity": qty,
                    "images": product['images']
                }
                st.session_state['order_items'].append(item)
                st.success(f"{qty} x {product['denomination']} ({color or 'N/A'}) ajouté !")
                st.rerun()

        if st.session_state['order_items']:
            st.subheader("Articles dans la Commande")
            order_df = pd.DataFrame(st.session_state['order_items']).rename(columns={
                "reference": "Réf",
                "denomination": "Désignation",
                "color": "Couleur",
                "quantity": "Quantité"
            })
            st.dataframe(order_df.drop(columns=['images'], errors='ignore'), use_container_width=True)
            if st.button("🗑️ Supprimer le dernier", key="bdc_remove"):
                st.session_state['order_items'].pop()
                st.rerun()

        st.subheader("Importer depuis Reçu ou Proforma")
        transactions_df = fetch_df_from_db('transactions')
        transactions_df = transactions_df[transactions_df['performed_by'] == username]
        import_options = ["Aucune"] + [
            f"{'Reçu' if row['status'] == 'completed' else 'Proforma'} #{row['transaction_id']} - {row['transaction_date']}"
            for _, row in transactions_df[transactions_df['status'].isin(['completed', 'proforma'])].iterrows()
        ]
        selected_import = st.selectbox("Sélectionnez une importation", import_options, key="bdc_import_select")
        if selected_import != "Aucune":
            tid = int(selected_import.split('#')[1].split(' - ')[0])
            imported_items = transactions_df[transactions_df['transaction_id'] == tid]['items'].iloc[0]
            st.write("**Aperçu des articles importés :**")
            preview_df = pd.DataFrame(imported_items).rename(columns={
                "reference": "Réf",
                "denomination": "Désignation",
                "Color": "Couleur",
                "Quantity": "Quantité"
            })
            st.dataframe(preview_df, use_container_width=True)
            if st.button("✅ Confirmer l'importation", key="bdc_import_btn"):
                st.session_state['order_items'] = [
                    {"reference": item['reference'], "denomination": item['denomination'], "color": item.get('Color'), "quantity": item['Quantity']}
                    for item in imported_items
                ]
                st.success(f"Importé depuis {selected_import} !")
                st.rerun()

        shipping_options = ["Inconnue pour l'instant", "Yalidin", "Casi Tour", "Sacfalie", "Transport El Hannaa", "Transport Hamada", "Transport organisé par Onama (payé par le client)", "Transport organisé par le client"]
        shipping_method = st.selectbox("Méthode de Livraison", shipping_options, key="bdc_shipping")
        payment_options = ["Non payé pour l'instant", "Payé partiellement à Eulma", "Payé partiellement à Fifou", "Paiement direct à Onama", "Paiement à la livraison", "CCP", "Espèces"]
        payment_option = st.selectbox("Option de Paiement", payment_options, key="bdc_payment")

        if st.button("✅ Créer Bon de Commande", type="primary", key="bdc_submit"):
            if not st.session_state['order_items']:
                st.error("Ajoutez au moins un article.")
            elif delivery_address == "Inconnue pour l'instant" and shipping_method != "Inconnue pour l'instant":
                st.error("Précisez une adresse ou choisissez 'Inconnue pour l'instant' pour la livraison.")
            else:
                st.write("Attempting to save order...")  # Debug
                order_id = save_order(city, delivery_address, st.session_state['order_items'], shipping_method, payment_option, username)
                st.write(f"Order ID returned: {order_id}")  # Debug
                if order_id:
                    st.success(f"Bon de Commande #{order_id} créé !")
                    st.write("Generating PDF...")  # Debug
                    pdf_path = generate_order_pdf(order_id, city, order_date, delivery_address, st.session_state['order_items'], shipping_method, payment_option, username)
                    st.write(f"PDF path: {pdf_path}")  # Debug
                    col1, col2 = st.columns(2)
                    with col1:
                        try:
                            with open(pdf_path, "rb") as file:
                                st.download_button("📥 Télécharger", file, f"BonDeCommande-{order_id}.pdf", key=f"bdc_download_{order_id}")
                        except Exception as e:
                            st.error(f"Failed to open PDF: {e}")
                    # Move st.rerun() to a separate button to avoid interrupting the download button
                    if st.button("Réinitialiser le formulaire", key=f"reset_{order_id}"):
                        st.session_state['order_items'] = []
                        st.rerun()
                else:
                    st.error("Failed to create order. Order ID is None.")

    with tab2:
        st.subheader("Suivi des Commandes")
        orders_df = fetch_df_from_db('orders')
        if not orders_df.empty:
            for i, order in orders_df.iterrows():
                with st.expander(f"Commande #{order['order_id']} - {order['order_date']} ({order['status']})"):
                    st.write(f"**Ville :** {order['city']}")
                    st.write(f"**Adresse :** {order['delivery_address'] or 'Non spécifiée'}")
                    st.write(f"**Livraison :** {order['shipping_method']}")
                    st.write(f"**Paiement :** {order['payment_option']}")
                    st.write(f"**Créé par :** {order['created_by']}")
                    items = order['items']
                    items_df = pd.DataFrame(items).rename(columns={
                        "reference": "Réf",
                        "denomination": "Désignation",
                        "color": "Couleur",
                        "quantity": "Quantité"
                    })
                    st.write("**Articles :**")
                    st.dataframe(items_df.drop(columns=['images'], errors='ignore'), use_container_width=True)
                    status_options = ["pending", "in production", "ready", "shipped"]
                    status_display = {"pending": "En attente", "in production": "En production", "ready": "Prêt", "shipped": "Expédié"}
                    display_options = [status_display[s] for s in status_options]
                    current_index = status_options.index(order['status']) if order['status'] in status_options else 0
                    new_status_display = st.selectbox("Statut", display_options, index=current_index, key=f"status_{order['order_id']}")
                    new_status = status_options[display_options.index(new_status_display)]
                    if st.button("Mettre à jour", key=f"update_{order['order_id']}"):
                        if update_order_status(order['order_id'], new_status):
                            st.success(f"Statut mis à jour : '{status_display[new_status]}' !")
                            st.rerun()
        else:
            st.info("Aucune commande enregistrée.")