"""
Dashboard charts module for the POS system.
Provides functions to generate visual charts and graphs for sales data.
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import json
from .utils import fetch_df_from_db

def generate_sales_chart(transactions_df, period='month'):
    """
    Generate a sales chart for the specified period.
    
    Args:
        transactions_df (DataFrame): Transactions data
        period (str): Time period - 'day', 'week', 'month', or 'year'
        
    Returns:
        altair.Chart: Sales chart
    """
    # Filter completed transactions only
    sales_df = transactions_df[transactions_df['status'] == 'completed'].copy()
    
    if sales_df.empty:
        return None
    
    # Convert transaction_date to datetime
    sales_df['date'] = pd.to_datetime(sales_df['transaction_date'], format='%d/%m/%Y', errors='coerce')
    
    # Group by date based on period
    if period == 'day':
        sales_df['period'] = sales_df['date'].dt.date
        title = "Ventes Quotidiennes"
    elif period == 'week':
        sales_df['period'] = sales_df['date'].dt.to_period('W').dt.start_time
        title = "Ventes Hebdomadaires"
    elif period == 'year':
        sales_df['period'] = sales_df['date'].dt.year
        title = "Ventes Annuelles"
    else:  # Default to month
        sales_df['period'] = sales_df['date'].dt.to_period('M').dt.start_time
        title = "Ventes Mensuelles"
    
    # Group by period and sum sales
    sales_by_period = sales_df.groupby('period')['final_amount'].sum().reset_index()
    sales_by_period['period'] = sales_by_period['period'].astype(str)
    
    # Create chart
    chart = alt.Chart(sales_by_period).mark_bar().encode(
        x=alt.X('period:N', title='Période'),
        y=alt.Y('final_amount:Q', title='Montant (DZD)'),
        tooltip=['period', alt.Tooltip('final_amount:Q', format=',.2f')]
    ).properties(
        title=title,
        width=600,
        height=400
    ).interactive()
    
    return chart

def generate_top_products_chart(transactions_df, top_n=10):
    """
    Generate a chart showing top selling products.
    
    Args:
        transactions_df (DataFrame): Transactions data
        top_n (int): Number of top products to show
        
    Returns:
        altair.Chart: Top products chart
    """
    # Filter completed transactions only
    sales_df = transactions_df[transactions_df['status'] == 'completed'].copy()
    
    if sales_df.empty:
        return None
    
    # Extract items from transactions
    all_items = []
    for _, row in sales_df.iterrows():
        items = json.loads(row['items']) if isinstance(row['items'], str) else row['items']
        all_items.extend(items)
    
    if not all_items:
        return None
    
    # Create DataFrame from items
    items_df = pd.DataFrame(all_items)
    
    # Group by product and sum quantities
    product_sales = items_df.groupby(['denomination', 'reference'])['Quantity'].sum().reset_index()
    
    # Get top N products
    top_products = product_sales.sort_values('Quantity', ascending=False).head(top_n)
    
    # Create chart
    chart = alt.Chart(top_products).mark_bar().encode(
        y=alt.Y('denomination:N', sort='-x', title='Produit'),
        x=alt.X('Quantity:Q', title='Quantité Vendue'),
        tooltip=['denomination', 'reference', 'Quantity']
    ).properties(
        title=f"Top {top_n} Produits Vendus",
        width=600,
        height=400
    ).interactive()
    
    return chart

def generate_sales_by_category_chart(transactions_df, products_df):
    """
    Generate a pie chart showing sales by product category.
    
    Args:
        transactions_df (DataFrame): Transactions data
        products_df (DataFrame): Products data
        
    Returns:
        altair.Chart: Sales by category chart
    """
    # Filter completed transactions only
    sales_df = transactions_df[transactions_df['status'] == 'completed'].copy()
    
    if sales_df.empty or products_df.empty:
        return None
    
    # Extract items from transactions
    all_items = []
    for _, row in sales_df.iterrows():
        items = json.loads(row['items']) if isinstance(row['items'], str) else row['items']
        all_items.extend(items)
    
    if not all_items:
        return None
    
    # Create DataFrame from items
    items_df = pd.DataFrame(all_items)
    
    # Merge with products to get categories
    items_df = items_df.merge(
        products_df[['reference', 'category']],
        on='reference',
        how='left'
    )
    
    # Fill missing categories
    items_df['category'] = items_df['category'].fillna('Non catégorisé')
    
    # Calculate sales by category
    category_sales = items_df.groupby('category').apply(
        lambda x: (x['Price'] * x['Quantity']).sum()
    ).reset_index(name='sales')
    
    # Create pie chart
    chart = alt.Chart(category_sales).mark_arc().encode(
        theta=alt.Theta(field="sales", type="quantitative"),
        color=alt.Color(field="category", type="nominal"),
        tooltip=['category', alt.Tooltip('sales:Q', format=',.2f')]
    ).properties(
        title="Ventes par Catégorie",
        width=400,
        height=400
    )
    
    return chart

def display_dashboard_charts():
    """
    Display all dashboard charts in the Streamlit app.
    """
    # Load data
    transactions_df = fetch_df_from_db('transactions')
    products_df = fetch_df_from_db('products')
    
    if transactions_df.empty:
        st.info("Aucune donnée de transaction disponible pour générer des graphiques.")
        return
    
    # Time period selector
    period = st.selectbox(
        "Période",
        ["Jour", "Semaine", "Mois", "Année"],
        index=2  # Default to month
    )
    period_map = {"Jour": "day", "Semaine": "week", "Mois": "month", "Année": "year"}
    
    # Sales chart
    sales_chart = generate_sales_chart(transactions_df, period_map[period])
    if sales_chart:
        st.altair_chart(sales_chart, use_container_width=True)
    else:
        st.info("Données insuffisantes pour générer le graphique des ventes.")
    
    # Create two columns for the remaining charts
    col1, col2 = st.columns(2)
    
    # Top products chart
    with col1:
        top_n = st.slider("Nombre de produits à afficher", 5, 20, 10)
        top_products_chart = generate_top_products_chart(transactions_df, top_n)
        if top_products_chart:
            st.altair_chart(top_products_chart, use_container_width=True)
        else:
            st.info("Données insuffisantes pour générer le graphique des produits.")
    
    # Sales by category chart
    with col2:
        category_chart = generate_sales_by_category_chart(transactions_df, products_df)
        if category_chart:
            st.altair_chart(category_chart, use_container_width=True)
        else:
            st.info("Données insuffisantes pour générer le graphique des catégories.")