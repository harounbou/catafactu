# modules/restock.py
import json
import streamlit as st
import pandas as pd
from .product_management import load_products, restock_product
from .transaction_management import record_transaction
from .utils import get_full_image_path, find_image_path_for_color
from .pos import stock_checker_section  # Updated import

def restock_page():
    st.title("Re-stocking")
    products_df = load_products()
    product_options = products_df['denomination'].tolist()
    
    # Stock checker section with unique prefix
    stock_checker_section(products_df, "restock_")
    
    # First selectbox with unique key
    selected_product = st.selectbox(
        "Select Product to Restock",
        product_options,
        key="restock_product_select_1"
    )
    
    if selected_product:
        product = products_df[products_df['denomination'] == selected_product].iloc[0]
        st.write(f"Current Stock: {product['quantite_actuelle']}")
        
        colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
        if not colors:
            st.warning("No colors available for this product.")
            total_quantity = st.number_input(
                "Total Quantity to Restock",
                min_value=0,
                value=0,
                key="restock_total_qty_no_color"
            )
            color_quantities = {"total": total_quantity}
        else:
            color_quantities = {}
            for color in colors:
                current_stock = int(product.get(color.lower(), 0)) if color.lower() in product else 0
                st.write(f"Current {color} Stock: {current_stock}")
                color_quantities[color] = st.number_input(
                    f"{color} Quantity",
                    min_value=0,
                    value=0,
                    key=f"restock_qty_{color}"
                )
            
            total_quantity = sum(color_quantities.values())
            st.number_input(
                "Total Quantity to Restock",
                value=total_quantity,
                disabled=True,
                key="restock_total_qty"
            )
        
        if st.button("Restock", key="restock_submit"):
            restock_items = []
            for color, qty in color_quantities.items():
                if qty > 0:
                    success = restock_product(product['reference'], qty, color if color != "total" else None)
                    if success:
                        restock_items.append({
                            "denomination": selected_product,
                            "reference": product['reference'],
                            "color": color if color != "total" else None,
                            "quantity": qty
                        })
            if restock_items:
                record_transaction(
                    None,
                    json.dumps(restock_items),
                    "N/A", 0.0, 0.0, "restock", st.session_state['user']['username']
                )
                st.success(f"Restocked {selected_product} successfully!")
                st.rerun()