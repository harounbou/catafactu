import pandas as pd
import streamlit as st
from .utils import fetch_df_from_db, save_df_to_db

def load_products():
    df = fetch_df_from_db('products')
    if df.empty:
        st.error("Échec du chargement des produits.")
        return pd.DataFrame(columns=[
            "reference", "denomination", "quantite_actuelle", "prix-super-gros",
            "prix-gros", "prix-détail", "couleurs-dispo-usine", "images", "category"
        ])
    return df

def update_stock(products_df, items):
    for item in items:
        idx = products_df[products_df['reference'] == item['reference']].index[0]
        current_stock = products_df.loc[idx, 'quantite_actuelle']
        color = item.get('Color', '').lower()
        
        if item['Quantity'] > current_stock:
            st.error(f"Stock total insuffisant pour {item['denomination']}")
            return False
        
        if color and color in products_df.columns:
            color_stock = products_df.loc[idx, color]
            if pd.notna(color_stock) and item['Quantity'] > color_stock:
                st.error(f"Stock insuffisant pour {item['denomination']} en {color} (disponible: {color_stock})")
                return False
            products_df.loc[idx, color] -= item['Quantity']
        
        products_df.loc[idx, 'quantite_actuelle'] -= item['Quantity']
        if 'quantite_vendue' in products_df.columns:
            products_df.loc[idx, 'quantite_vendue'] = products_df.loc[idx, 'quantite_vendue'] + item['Quantity']
    
    save_df_to_db(products_df, 'products')
    return True

def restock_product(products_df, reference, quantity, cost):
    idx = products_df[products_df['reference'] == reference].index[0]
    products_df.loc[idx, 'quantite_actuelle'] += quantity
    if 'quantite_restockee' in products_df.columns:
        products_df.loc[idx, 'quantite_restockee'] = products_df.loc[idx, 'quantite_restockee'] + quantity
    save_df_to_db(products_df, 'products')
    return cost * quantity