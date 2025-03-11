# modules/bon_de_commande.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from .product_management import load_products
from .transaction_management import fetch_df_from_db, get_db_connection
from .utils import find_image_path_for_color, get_full_image_path, send_email
from .pdf_generator import generate_order_pdf

def initialize_orders_table():
    """Initialiser la table des commandes dans la base de données."""
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
    """Enregistrer un Bon de Commande dans la table des commandes."""
    initialize_orders_table()
    conn = get_db_connection()
    c = conn.cursor()
    try:
        order_date = datetime.now().strftime("%d/%m/%Y")
        items_json = pd.Series(items).to_json(orient='records')
        c.execute("""
            INSERT INTO orders (city, order_date, delivery_address, items, shipping_method, payment_option, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (city, order_date, delivery_address, items_json, shipping_method, payment_option, created_by))
        order_id = c.lastrowid
        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        st.error(f"Erreur lors de l'enregistrement de la commande : {e}")
        return None
    finally:
        conn.close()

def update_order_status(order_id, new_status):
    """Mettre à jour le statut d'une commande."""
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
    """Afficher et gérer la page du Bon de Commande."""
    st.title("Bon de Commande")
    username = st.session_state['user']['username']

    city_map = {
        "admin": "Alger",
        "eulma": "Eulmi",
        "alger": "Alger",
        "constantine": "Constantine"
    }
    city = city_map.get(username, "Alger")

    tab1, tab2 = st.tabs(["Créer un Bon de Commande", "Suivi des Commandes"])

    with tab1:
        order_date = datetime.now().strftime("%d/%m/%Y")
        st.write(f"**Ville :** {city} | **Date de Commande :** {order_date}")

        # Delivery Options
        delivery_option = st.selectbox("Option de Livraison", ["Livraison à Ville Client", "Pickup from Onama"], key="bdc_delivery_option")
        if delivery_option == "Livraison à Ville Client":
            known_addresses = ["Bureau Alger", "Dépôt Constantine", "Magasin Eulmi", "Inconnue pour l'instant"]
            delivery_address = st.selectbox("Adresse de Livraison", known_addresses, key="bdc_address")
            if delivery_address == "Inconnue pour l'instant":
                delivery_address = st.text_input("Adresse personnalisée (si connue plus tard)", key="bdc_custom_address")
        else:
            delivery_address = "Pickup from Onama"

        # Import from POS
        st.subheader("Importer depuis POS (optionnel)")
        transactions_df = fetch_df_from_db('transactions')
        completed_sales = transactions_df[transactions_df['status'] == 'completed']
        if not completed_sales.empty:
            sale_options = [f"Transaction #{tid} - {date}" for tid, date in zip(completed_sales['transaction_id'], completed_sales['transaction_date'])]
            selected_sale = st.selectbox("Sélectionnez une vente", ["Aucune"] + sale_options, key="bdc_import_sale")
            if selected_sale != "Aucune":
                selected_tid = int(selected_sale.split('#')[1].split(' - ')[0])
                items_json = completed_sales[completed_sales['transaction_id'] == selected_tid]['items'].iloc[0]
                imported_items = json.loads(items_json)
                if st.button("Importer les articles", key="bdc_import_btn"):
                    st.session_state['order_items'] = [
                        {"reference": item['reference'], "denomination": item['denomination'], "color": item.get('Color'), "quantity": item['Quantity']}
                        for item in imported_items
                    ]
                    st.success("Articles importés depuis la vente !")
                    st.rerun()

        # Import from Proforma
        st.subheader("Récupérer une Facture Proforma (optionnel)")
        proforma_df = fetch_df_from_db('transactions')
        proforma_sales = proforma_df[proforma_df['status'] == 'proforma']
        if not proforma_sales.empty:
            proforma_options = [f"Proforma #{tid} - {date}" for tid, date in zip(proforma_sales['transaction_id'], proforma_sales['transaction_date'])]
            selected_proforma = st.selectbox("Sélectionnez une proforma", ["Aucune"] + proforma_options, key="bdc_import_proforma")
            if selected_proforma != "Aucune":
                selected_tid = int(selected_proforma.split('#')[1].split(' - ')[0])
                items_json = proforma_sales[proforma_sales['transaction_id'] == selected_tid]['items'].iloc[0]
                imported_items = json.loads(items_json)
                if st.button("Importer depuis Proforma", key="bdc_import_proforma_btn"):
                    st.session_state['order_items'] = [
                        {"reference": item['reference'], "denomination": item['denomination'], "color": item.get('Color'), "quantity": item['Quantity']}
                        for item in imported_items
                    ]
                    st.success("Articles importés depuis la proforma !")
                    st.rerun()

        st.subheader("Détails de la Commande")
        if 'order_items' not in st.session_state:
            st.session_state['order_items'] = []

        search_term = st.text_input("Rechercher un produit", placeholder="Nom ou référence", key="bdc_search")
        if st.button("Rechercher", key="bdc_search_btn"):
            filtered_df = products_df[
                products_df['denomination'].str.contains(search_term, case=False, na=False) |
                products_df['reference'].str.contains(search_term, case=False, na=False)
            ]
            if not filtered_df.empty:
                st.session_state['bdc_filtered'] = filtered_df
            else:
                st.error("Aucun produit trouvé.")

        if 'bdc_filtered' in st.session_state:
            filtered_df = st.session_state['bdc_filtered']
            selected_item = st.selectbox("Sélectionnez un produit", filtered_df['denomination'], key="bdc_select")
            selected_row = filtered_df[filtered_df['denomination'] == selected_item].iloc[0]

            st.write(f"**Référence :** {selected_row['reference']}")
            st.write(f"**Désignation :** {selected_row['denomination']}")
            
            colors = [color.strip() for color in selected_row['couleurs-dispo-usine'].split(',')] if pd.notna(selected_row['couleurs-dispo-usine']) else []
            selected_color = st.selectbox("Couleur", colors, key="bdc_color") if colors else None
            
            image_path = get_full_image_path(find_image_path_for_color(selected_row['images'], selected_color)) if selected_color else None
            if image_path:
                st.image(image_path, caption=f"Aperçu ({selected_color})", width=150)
            
            quantity = st.number_input("Quantité", min_value=1, value=1, key="bdc_quantity")
            
            if st.button("Ajouter à la commande", key="bdc_add"):
                item = {
                    "reference": selected_row['reference'],
                    "denomination": selected_row['denomination'],
                    "color": selected_color,
                    "quantity": quantity,
                    "images": selected_row['images']
                }
                st.session_state['order_items'].append(item)
                st.success(f"{quantity} x {selected_row['denomination']} ({selected_color}) ajouté !")

        if st.session_state['order_items']:
            st.subheader("Articles dans la Commande")
            order_df = pd.DataFrame(st.session_state['order_items'])
            order_df = order_df.rename(columns={
                "reference": "Réf",
                "denomination": "Désignation",
                "color": "Couleur",
                "quantity": "Quantité"
            })
            st.dataframe(order_df.drop(columns=['images'], errors='ignore'), use_container_width=True)
            
            if st.button("Supprimer le dernier article", key="bdc_remove"):
                st.session_state['order_items'].pop()
                st.rerun()

        st.subheader("Options de Livraison et Paiement")
        shipping_options = [
            "Inconnue pour l'instant",
            "Yalidin",
            "Casi Tour",
            "Sacfalie",
            "Transport El Hannaa",
            "Transport Hamada",
            "Transport organisé par Onama (payé par le client)",
            "Transport organisé par le client"
        ]
        shipping_method = st.selectbox("Méthode de Livraison", shipping_options, key="bdc_shipping")
        
        payment_options = [
            "Non payé pour l'instant",
            "Payé partiellement à Eulma",
            "Payé partiellement à Fifou",
            "Paiement direct à Onama",
            "Paiement à la livraison"
        ]
        payment_option = st.selectbox("Option de Paiement", payment_options, key="bdc_payment")

        email_options = ["Aucun"] + [st.text_input("Envoyer le Bon de Commande par email (optionnel)", placeholder="Entrez l'adresse email", key="bdc_email")]
        email_to_send = st.selectbox("Envoyer par email", email_options, key="bdc_email_select")

        if st.button("Créer Bon de Commande", key="bdc_submit"):
            if not st.session_state['order_items']:
                st.error("Veuillez ajouter au moins un article à la commande.")
            elif delivery_option == "Livraison à Ville Client" and delivery_address == "Inconnue pour l'instant" and shipping_method not in ["Inconnue pour l'instant", "Pickup from Onama"]:
                st.error("Veuillez préciser une adresse ou sélectionner 'Inconnue pour l'instant' comme méthode de livraison.")
            else:
                order_id = save_order(city, delivery_address, st.session_state['order_items'], shipping_method, payment_option, username)
                if order_id:
                    st.success(f"Bon de Commande #{order_id} créé avec succès !")
                    pdf_path = generate_order_pdf(order_id, city, order_date, delivery_address, st.session_state['order_items'], shipping_method, payment_option, username)
                    
                    with open(pdf_path, "rb") as file:
                        st.download_button("Télécharger Bon de Commande", file, f"BonDeCommande-{order_id}.pdf", key=f"bdc_download_{order_id}")
                    
                    if email_to_send != "Aucun":
                        email_body = f"Bonjour,\n\nVeuillez trouver ci-joint le Bon de Commande #{order_id} créé le {order_date}.\n\nCordialement,\n{username}"
                        if send_email(email_to_send, f"Bon de Commande #{order_id}", email_body, pdf_path):
                            st.success(f"Bon de Commande envoyé à {email_to_send} !")
                        else:
                            st.error("Échec de l'envoi de l'email.")
                    
                    manufacturing_email = "manufacturing@onama.com"
                    if send_email(manufacturing_email, f"Nouveau Bon de Commande #{order_id}", f"Un nouveau Bon de Commande #{order_id} a été créé par {username}."):
                        st.success("Équipe de fabrication notifiée !")
                    
                    st.session_state['order_items'] = []
                    st.rerun()

    with tab2:
        st.subheader("Suivi des Commandes")
        orders_df = fetch_df_from_db('orders')
        if not orders_df.empty:
            for i, order in orders_df.iterrows():
                with st.expander(f"Commande #{order['order_id']} - {order['order_date']} ({order['status']})"):
                    st.write(f"**Ville :** {order['city']}")
                    st.write(f"**Adresse de Livraison :** {order['delivery_address'] or 'Non spécifiée'}")
                    st.write(f"**Méthode de Livraison :** {order['shipping_method']}")
                    st.write(f"**Option de Paiement :** {order['payment_option']}")
                    st.write(f"**Créé par :** {order['created_by']}")
                    items = json.loads(order['items'])
                    items_df = pd.DataFrame(items).rename(columns={
                        "reference": "Réf",
                        "denomination": "Désignation",
                        "color": "Couleur",
                        "quantity": "Quantité"
                    })
                    st.write("**Articles :**")
                    st.dataframe(items_df.drop(columns=['images'], errors='ignore'), use_container_width=True)
                    
                    status_options = ["en attente", "en production", "prêt", "expédié"]
                    new_status = st.selectbox("Mettre à jour le statut", status_options, index=status_options.index(order['status']), key=f"status_{order['order_id']}")
                    if st.button("Mettre à jour", key=f"update_{order['order_id']}"):
                        if update_order_status(order['order_id'], new_status):
                            st.success(f"Statut de la commande #{order['order_id']} mis à jour à '{new_status}' !")
                            st.rerun()
        else:
            st.info("Aucune commande enregistrée.")