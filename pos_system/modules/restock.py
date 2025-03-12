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
    product_options = products_df['denomination'].tolist()
    selected_product = st.selectbox("Select Product to Restock", product_options)
    
    if selected_product:
        product = products_df[products_df['denomination'] == selected_product].iloc[0]
        st.write(f"Current Stock: {product['quantite_actuelle']}")
        
        # Get all available colors from couleurs-dispo-usine
        colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
        if not colors:
            st.warning("No colors available for this product.")
            total_quantity = st.number_input("Total Quantity to Restock", min_value=0, value=0)
            color_quantities = {"total": total_quantity}
        else:
            # Dynamically create input fields for each color
            color_quantities = {}
            for color in colors:
                current_stock = int(product.get(color.lower(), 0)) if color.lower() in product.index else 0
                st.write(f"Current {color} Stock: {current_stock}")
                color_quantities[color] = st.number_input(f"{color} Quantity", min_value=0, value=0, key=f"restock_{color}")
            
            # Calculate total quantity dynamically
            total_quantity = sum(color_quantities.values())
            st.number_input("Total Quantity to Restock", value=total_quantity, disabled=True, key="total_restock")
        
        if st.button("Restock"):
            for color, qty in color_quantities.items():
                if qty > 0:
                    restock_product(products_df, product['reference'], qty, color=color if color != "total" else None)
            record_transaction(
                None,
                json.dumps([{
                    "denomination": selected_product,
                    "reference": product['reference'],
                    "quantities": {k: v for k, v in color_quantities.items() if v > 0}
                }]),
                "N/A", 0.0, 0.0, "restock", st.session_state['user']['username']
            )
            st.success(f"Restocked {selected_product} successfully!")
            st.rerun()