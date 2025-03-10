# restock.py
import streamlit as st
import pandas as pd
from .product_management import load_products, restock_product
from .transaction_management import record_transaction
from .utils import get_full_image_path, find_image_path_for_color
from .pos import stock_checker_section

def restock_page():
    st.title("Re-stocking")
    products_df = load_products()
    username = st.session_state['user']['username']
    
    stock_checker_section(products_df, "restock_")
    
    with st.expander("Restocker un produit", expanded=True):
        search_term = st.text_input("Rechercher par nom ou référence", placeholder="Tapez le nom ou la référence", key="restock_search")
        if st.button("Rechercher", key="restock_search_btn"):
            filtered_df = products_df[
                products_df['denomination'].str.contains(search_term, case=False, na=False) |
                products_df['reference'].str.contains(search_term, case=False, na=False)
            ]
            if not filtered_df.empty:
                st.session_state['restock_filtered'] = filtered_df
            else:
                st.error("Aucun produit trouvé.")
        
        if 'restock_filtered' in st.session_state:
            filtered_df = st.session_state['restock_filtered']
            selected_item = st.selectbox("Sélectionnez un produit", filtered_df['denomination'], key="restock_selected")
            selected_row = filtered_df[filtered_df['denomination'] == selected_item].squeeze()
            st.write(f"**Référence :** {selected_row['reference']}")
            st.write(f"**Stock actuel :** {int(selected_row['quantite_actuelle'])} unités")
            
            colors = [color.strip() for color in selected_row['couleurs-dispo-usine'].split(',')] if pd.notna(selected_row['couleurs-dispo-usine']) else []
            selected_color = st.selectbox("Choisissez une couleur", colors, key="restock_color_select") if colors else None
            
            image_path = get_full_image_path(find_image_path_for_color(selected_row['images'], selected_color)) if selected_color else None
            if image_path:
                st.image(image_path, caption=f"Aperçu ({selected_color})", width=150)
            else:
                st.write("Image non disponible")
            
            quantity = st.number_input("Quantité à ajouter", min_value=1, key="restock_quantity")
            if st.button("Restocker", key="restock_btn"):
                total_cost = restock_product(products_df, selected_row['reference'], quantity, 0, selected_color)
                record_transaction(None, [{"denomination": selected_row['denomination'], "reference": selected_row['reference'], "Quantity": quantity, "Color": selected_color}], "Restock", 0, 0, "restock", username)
                st.success(f"{quantity} unités de {selected_row['denomination']} ({selected_color}) restockées !")
                del st.session_state['restock_filtered']
                st.rerun()