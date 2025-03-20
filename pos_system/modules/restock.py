# modules/restock.py
import datetime
import json
import streamlit as st
import pandas as pd
from .product_management import load_products, restock_product
from .transaction_management import record_transaction
from .pos import stock_checker_section
from .utils import get_db_connection

# Color configuration
COLOR_MAPPING = {
    'brown_gradient': 'brown_deg',
    'grey_gradient': 'grey_deg',
    'gradient_brown': 'brown_deg',
    'gradient_grey': 'grey_deg'
}

COLOR_STYLES = {
    'uni_colour': '#f5f5f5',
    'default_colour': '#e0e0e0',
    'brown': '#d7ccc8',
    'brown_deg': '#d7ccc8',
    'blue': '#bbdefb',
    'white': '#ffffff',
    'black': '#b0bec5',
    'green_bottle': '#c8e6c9',
    'red': '#ffcdd2',
    'grey': '#cfd8dc',
    'grey_deg': '#cfd8dc',
    'beige': '#d2b48c',
    'yellow': '#fff9c4',
    'orange': '#ffe0b2',
    'garnet': '#ffccbc',
    'golden': '#fff3e0',
    'green': '#c8e6c9',
    'rose': '#f8bbd0',
    'default': '#f5f5f5'
}

def get_db_color_name(display_color):
    """Map display color names to database column names"""
    cleaned_color = display_color.lower().replace(" ", "_")
    return COLOR_MAPPING.get(cleaned_color, cleaned_color)

def restock_page():
    st.title("📦 Re-stocking Manager")
    
    @st.cache_data(ttl=0.1)
    def get_products():
        return load_products()
    
    products_df = get_products()

    # Real-time stock checker
    stock_checker_section(products_df, "restock_")
    
    # Product selection
    selected_product = st.selectbox(
        "Select Product to Restock",
        products_df['denomination'].unique(),
        key="restock_product_select"
    )
    
    if not selected_product:
        return
    
    product = products_df[products_df['denomination'] == selected_product].iloc[0]
    colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
    
    # Current stock status
    st.subheader("📊 Current Stock Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Quantity", f"{int(product['quantite_actuelle'])} units")
    with col2:
        st.metric("Total Restocked", f"{int(product['quantite_restockee'])} units")
    with col3:
        st.metric("Initial Stock", f"{int(product['quantite_initiale'])} units")
    
    # Restock controls
    st.subheader("🚀 Restock Actions")
    restock_btn = st.button("✅ Confirm Restock", key="confirm_restock_top")
    
    # Color-specific restocking
    restock_data = {}
    if colors:
        st.subheader("🎨 Color-specific Restocking")
        cols = st.columns(2)
        for idx, color in enumerate(colors):
            with cols[idx % 2]:
                db_color = get_db_color_name(color)
                current = product.get(db_color, 0)
                bg_color = COLOR_STYLES.get(db_color, COLOR_STYLES['default'])
                
                st.markdown(f"""
                <div style="background-color: {bg_color}; 
                            padding: 12px; 
                            border-radius: 8px;
                            margin: 8px 0;
                            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                            border: 1px solid #e0e0e0;">
                    <h4 style="margin:0; color: #2d3436;">
                        {color.replace('_', ' ').title()}
                    </h4>
                    <p style="margin:4px 0 0 0; color: #636e72;">
                        Current: {int(current)} units
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                restock_data[color] = st.number_input(
                    "Quantity to add",
                    min_value=0,
                    value=0,
                    step=1,
                    format="%d",
                    key=f"restock_{color}"
                )
    else:
        st.subheader("📦 General Restocking")
        restock_data['total'] = st.number_input(
            "Quantity to Restock",
            min_value=0,
            value=0,
            step=1,
            format="%d",
            key="restock_total"
        )
    
    # Validation and submission
    if restock_btn:
        try:
            total_restocked = 0
            has_valid_entries = False
            
            for display_color, qty in restock_data.items():
                qty = int(qty)
                if qty > 0:
                    has_valid_entries = True
                    db_color = get_db_color_name(display_color)
                    
                    if db_color not in product:
                        raise ValueError(f"Invalid color '{display_color}' for product {product['reference']}")
                    
                    if restock_product(product['reference'], qty, db_color):
                        total_restocked += qty
            
            if not has_valid_entries:
                st.warning("⚠️ Please enter quantities to restock")
            elif total_restocked > 0:
                record_transaction(
                    None,
                    json.dumps({
                        "type": "restock",
                        "reference": product['reference'],
                        "quantities": restock_data
                    }),
                    "restock",
                    total_restocked,
                    0.0,
                    "N/A",
                    st.session_state['user']['username']
                )
                st.balloons()
                st.success(f"🎉 Successfully restocked {int(total_restocked)} units!")
                get_products.clear()
                st.rerun()
            else:
                st.error("❌ Restock failed - please check database connection")
                
        except Exception as e:
            st.error(f"❌ Restock failed: {str(e)}")

    # Visual separator
    st.markdown("---")
    st.caption("ℹ️ Color gradients are automatically converted to database columns (e.g., 'brown_gradient' → 'brown_deg')")