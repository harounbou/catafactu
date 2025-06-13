"""
Enhanced dashboard module for the POS system.
Provides an improved dashboard with charts and analytics.
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import json
import os

from .utils import fetch_df_from_db
from .dashboard_charts import (
    generate_sales_chart,
    generate_top_products_chart,
    generate_sales_by_category_chart
)

def enhanced_dashboard_page():
    """
    Render an enhanced dashboard with charts and analytics.
    """
    st.title("📊 Dashboard")
    
    # Load data
    transactions_df = fetch_df_from_db('transactions')
    products_df = fetch_df_from_db('products')
    
    # Create tabs for different dashboard sections
    tab1, tab2, tab3 = st.tabs(["Overview", "Sales Analytics", "Inventory Status"])
    
    # Tab 1: Overview
    with tab1:
        if transactions_df.empty:
            st.info("No transaction data available.")
        else:
            # Key metrics
            col1, col2, col3 = st.columns(3)
            
            # Total sales
            completed_sales = transactions_df[transactions_df['status'] == "completed"]
            total_sales = completed_sales['final_amount'].sum() if not completed_sales.empty else 0
            
            # Today's sales
            today = datetime.now().strftime("%d/%m/%Y")
            today_sales = completed_sales[completed_sales['transaction_date'] == today]
            today_amount = today_sales['final_amount'].sum() if not today_sales.empty else 0
            
            # Till balance
            from .transaction_management import get_till_balance
            till_balance = get_till_balance()
            
            with col1:
                st.metric(
                    label="Total Sales",
                    value=f"{total_sales:,.2f} DZD",
                    delta=f"{today_amount:,.2f} DZD Today"
                )
            
            with col2:
                # Calculate sales trend
                last_week = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
                last_week_sales = completed_sales[completed_sales['transaction_date'] >= last_week]
                last_week_amount = last_week_sales['final_amount'].sum() if not last_week_sales.empty else 0
                
                st.metric(
                    label="Weekly Sales",
                    value=f"{last_week_amount:,.2f} DZD",
                    delta=f"{len(last_week_sales)} Transactions"
                )
            
            with col3:
                st.metric(
                    label="Till Balance",
                    value=f"{till_balance:,.2f} DZD"
                )
            
            # Recent transactions
            st.subheader("Recent Transactions")
            recent_transactions = transactions_df.sort_values('transaction_id', ascending=False).head(5)
            
            if not recent_transactions.empty:
                for _, tx in recent_transactions.iterrows():
                    with st.expander(f"Transaction #{tx['transaction_id']} - {tx['transaction_date']}"):
                        st.write(f"**Status:** {tx['status']}")
                        st.write(f"**Amount:** {tx['final_amount']:,.2f} DZD")
                        st.write(f"**Client ID:** {tx['client_id']}")
                        st.write(f"**Performed by:** {tx['performed_by']}")
            else:
                st.info("No recent transactions found.")
    
    # Tab 2: Sales Analytics
    with tab2:
        if transactions_df.empty:
            st.info("No transaction data available for analytics.")
        else:
            # Time period selector for sales chart
            period = st.selectbox(
                "Time Period",
                ["Day", "Week", "Month", "Year"],
                index=2  # Default to month
            )
            period_map = {"Day": "day", "Week": "week", "Month": "month", "Year": "year"}
            
            # Sales chart
            sales_chart = generate_sales_chart(transactions_df, period_map[period])
            if sales_chart:
                st.altair_chart(sales_chart, use_container_width=True)
            else:
                st.info("Insufficient data to generate sales chart.")
            
            # Create two columns for additional charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Top products chart
                top_n = st.slider("Number of top products to show", 5, 20, 10)
                top_products_chart = generate_top_products_chart(transactions_df, top_n)
                if top_products_chart:
                    st.altair_chart(top_products_chart, use_container_width=True)
                else:
                    st.info("Insufficient data to generate top products chart.")
            
            with col2:
                # Sales by category chart
                category_chart = generate_sales_by_category_chart(transactions_df, products_df)
                if category_chart:
                    st.altair_chart(category_chart, use_container_width=True)
                else:
                    st.info("Insufficient data to generate category chart.")
    
    # Tab 3: Inventory Status
    with tab3:
        if products_df.empty:
            st.info("No product data available.")
        else:
            st.subheader("Inventory Status")
            
            # Low stock warning
            low_stock_threshold = st.slider("Low Stock Threshold", 1, 20, 5)
            low_stock = products_df[products_df['quantite_actuelle'] <= low_stock_threshold]
            
            if not low_stock.empty:
                st.warning(f"{len(low_stock)} products have low stock (≤ {low_stock_threshold} units)")
                st.dataframe(
                    low_stock[['reference', 'denomination', 'quantite_actuelle']],
                    use_container_width=True
                )
            else:
                st.success("All products have sufficient stock levels.")
            
            # Stock distribution chart
            stock_data = products_df[['denomination', 'quantite_actuelle']].sort_values('quantite_actuelle', ascending=False).head(15)
            
            if not stock_data.empty:
                stock_chart = alt.Chart(stock_data).mark_bar().encode(
                    y=alt.Y('denomination:N', sort='-x', title='Product'),
                    x=alt.X('quantite_actuelle:Q', title='Current Stock'),
                    color=alt.condition(
                        alt.datum.quantite_actuelle <= low_stock_threshold,
                        alt.value('red'),
                        alt.value('green')
                    ),
                    tooltip=['denomination', 'quantite_actuelle']
                ).properties(
                    title="Current Stock Levels (Top 15 Products)",
                    width=600,
                    height=400
                ).interactive()
                
                st.altair_chart(stock_chart, use_container_width=True)
            else:
                st.info("No stock data available to display.")