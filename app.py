import streamlit as st
import pandas as pd
import plotly.express as px

# Set the page to a wide layout for the dashboard
st.set_page_config(page_title="Product Dashboard", layout="wide")

@st.cache_data  # Caches the data for faster re-runs
def load_data(filepath):
    """
    Loads, cleans, and engineers features from the product CSV.
    """
    df = pd.read_csv(filepath)
    
    # --- FIX 1: Clean column names ---
    # This removes any hidden spaces from the start or end of all column names
    df.columns = df.columns.str.strip()
    
    # === 1. Data Cleaning ===
    
    # Clean price columns (e.g., "89.68-99.99" -> 89.68)
    df['discounted_price'] = df['discounted_price'].astype(str).str.split('-').str[0]
    df['original_price'] = df['original_price'].astype(str).str.split('-').str[0]
    
    # Convert prices to numbers, forcing errors (like 'Free') to NaN (Not a Number)
    df['discounted_price'] = pd.to_numeric(df['discounted_price'], errors='coerce')
    df['original_price'] = pd.to_numeric(df['original_price'], errors='coerce')

    # If original_price is missing, assume it's the same as the discounted_price
    df['original_price'].fillna(df['discounted_price'], inplace=True)
    # Drop any rows where we still don't have a valid price
    df.dropna(subset=['discounted_price'], inplace=True)

    # Clean other numeric columns
    df['product_rating'] = pd.to_numeric(df['product_rating'], errors='coerce')
    df['total_reviews'] = pd.to_numeric(df['total_reviews'], errors='coerce')
    df['purchased_last_month'] = pd.to_numeric(df['purchased_last_month'], errors='coerce')

    # --- FIX 2: Fill NaN values to prevent chart errors ---
    # This fixes the 'ValueError' from your screenshot
    df['purchased_last_month'].fillna(0, inplace=True)
    df['total_reviews'].fillna(0, inplace=True)
    # Fill missing ratings with the average rating
    df['product_rating'].fillna(df['product_rating'].mean(), inplace=True)


    # === 2. Feature Engineering (Creating New Columns) ===
    
    # *** IMPORTANT: Change 'product_category' to your actual column name ***
    category_col = 'product_category'  # <-- CHECK AND CHANGE THIS LINE
    
    # Check if the category column exists, otherwise create a dummy one
    if category_col not in df.columns:
        st.error(f"Column '{category_col}' not found. Please update Line 61. Using 'Unknown' for now.")
        df[category_col] = 'Unknown'
    else:
         df[category_col].fillna('Unknown', inplace=True)
        
    # Calculate Estimated Revenue
    df['Est. Revenue (Last Month)'] = df['discounted_price'] * df['purchased_last_month']
    
    # Calculate Discount Percentage
    df['Discount %'] = ((df['original_price'] - df['discounted_price']) / df['original_price']) * 100
    df['Discount %'] = df['Discount %'].fillna(0).clip(0, 100)
    
    
    # --- FIX 3: Use the CORRECT column names from your file ---
    
    actual_columns = df.columns.tolist()

    # Check for 'is_best_seller' (FIXED)
    if 'is_best_seller' not in actual_columns:
        st.error(f"Error: Column 'is_best_seller' not found.")
        df['is_best_seller'] = False # Create a dummy column to prevent crash
    else:
        # Column exists, just make sure it's boolean
        df['is_best_seller'] = df['is_best_seller'].astype(bool)

    # Check for 'has_coupon'
    if 'has_coupon' not in actual_columns:
        st.error(f"Error: Column 'has_coupon' not found.")
        df['has_coupon_bool'] = False # Dummy column
    else:
        df['has_coupon_bool'] = df['has_coupon'].astype(str).str.len() > 3 

    # Check for 'sustainability_tags' (FIXED)
    if 'sustainability_tags' not in actual_columns:
        st.error(f"Error: Column 'sustainability_tags' not found.")
        df['is_sustainable'] = False # Dummy column
    else:
        # If the 'sustainability_tags' column is NOT blank, mark as sustainable
        df['is_sustainable'] = df['sustainability_tags'].notna()
        
    # Check for 'is_sponsored'
    if 'is_sponsored' not in actual_columns:
        st.error(f"Error: Column 'is_sponsored' not found.")
        df['is_sponsored'] = "Unknown" # Dummy column
    else:
        # Fill any blank 'is_sponsored' values
        df['is_sponsored'].fillna(False, inplace=True)
    
    # --- End of Fixes ---

    return df

# === Load the Data ===
try:
    df = load_data('amazon_products_sales_data_cleaned.csv') 
except FileNotFoundError:
    st.error("Error: The file 'amazon_products_sales_data_cleaned.csv' was not found.")
    st.error("Please make sure it's in the **exact same folder** as your 'App.py' file.")
    st.stop() # Stop the app from running further
except Exception as e:
    st.error(f"An error occurred during data loading: {e}")
    st.exception(e) # This will print the full error
    st.stop()

# === Start Building the Dashboard ===

st.title("🛍️ Product Performance Dashboard")
st.write("Analysis of product listings, pricing, and performance.")

# === Sidebar Filters ===
st.sidebar.header("Filters")

# *** IMPORTANT: Use the same category column name as in load_data ***
category_col = 'product_category' #<-- MAKE SURE THIS MATCHES LINE 61
categories = ['All'] + sorted(df[category_col].unique())
selected_category = st.sidebar.selectbox("Select Product Category", categories)

# Filter the dataframe based on selection
if selected_category == 'All':
    filtered_df = df.copy()
else:
    filtered_df = df[df[category_col] == selected_category]

# === KPI Cards (Top-Level Metrics) ===
st.subheader("Key Performance Indicators")

total_revenue = filtered_df['Est. Revenue (Last Month)'].sum()
total_purchased = filtered_df['purchased_last_month'].sum()
avg_rating = filtered_df['product_rating'].mean()
total_best_sellers = filtered_df['is_best_seller'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Est. Monthly Revenue", f"${total_revenue:,.0f}")
col2.metric("Total Units (Last Month)", f"{total_purchased:,.0f}")
col3.metric("Average Rating", f"{avg_rating:.1f} ⭐")
col4.metric("Total 'Best Seller' Items", f"{total_best_sellers}")

# === Performance Analysis ===
st.subheader("Performance Analysis")

col1, col2 = st.columns([2, 1]) # First column is 2x wider

with col1:
    # Chart 1: Top 10 Products by Estimated Revenue
    top_10_products = filtered_df.nlargest(10, 'Est. Revenue (Last Month)')
    fig_revenue = px.bar(
        top_10_products,
        x='Est. Revenue (Last Month)',
        y='product_title',
        orientation='h',
        title='Top 10 Products by Estimated Revenue',
        hover_data=['product_rating', 'total_reviews']
    )
    st.plotly_chart(fig_revenue, use_container_width=True)

with col2:
    # Chart 2: Category Distribution
    if selected_category == 'All':
        category_revenue = df.groupby(category_col)['Est. Revenue (Last Month)'].sum().reset_index()
        fig_pie = px.pie(
            category_revenue,
            names=category_col,
            values='Est. Revenue (Last Month)',
            title='Revenue by Product Category',
            hole=0.4 # This makes it a donut chart
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        # Show top purchased in the selected category
        st.write(f"Top 5 Purchased in {selected_category}:")
        top_purchased = filtered_df.nlargest(5, 'purchased_last_month')
        st.dataframe(top_purchased[['product_title', 'purchased_last_month', 'product_rating']])


# === Pricing, Ratings & Promotions Analysis ===
st.subheader("Pricing, Ratings & Promotions Analysis")
col3, col4 = st.columns(2)

with col3:
    # Chart 3: Rating vs. Total Reviews
    # This chart is now fixed because 'purchased_last_month', 'total_reviews', 
    # and 'product_rating' are all cleaned of NaN values.
    fig_scatter = px.scatter(
        filtered_df,
        x='product_rating',
        y='total_reviews',
        size='purchased_last_month', # Size of dot = units sold
        color='Discount %',          # Color of dot = discount %
        title='Rating vs. Total Reviews (Size = Units Sold)',
        hover_data=['product_title']
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with col4:
    # Chart 4: Sponsored vs. Non-Sponsored Revenue
    sponsor_df = filtered_df.groupby('is_sponsored')['Est. Revenue (Last Month)'].mean().reset_index()
    fig_sponsor = px.bar(
        sponsor_df,
        x='is_sponsored',
        y='Est. Revenue (Last Month)',
        title='Avg. Revenue: Sponsored vs. Non-Sponsored',
        color='is_sponsored'
    )
    st.plotly_chart(fig_sponsor, use_container_width=True)

# === Promotions & Badges Analysis ===
st.subheader("Promotions, Badges & Sustainability Analysis")
col5, col6, col7 = st.columns(3)

with col5:
    # Chart 5: 'Best Seller' Badge Impact
    best_seller_df = filtered_df.groupby('is_best_seller')['purchased_last_month'].mean().reset_index()
    best_seller_df['is_best_seller'] = best_seller_df['is_best_seller'].map({True: 'Best Seller', False: 'No Badge'})
    fig_best_seller = px.bar(
        best_seller_df,
        x='is_best_seller',
        y='purchased_last_month',
        title='Avg. Units Sold: Best Seller vs. No Badge',
        color='is_best_seller'
    )
    st.plotly_chart(fig_best_seller, use_container_width=True)
    
with col6:
    # Chart 6: Coupon Impact
    coupon_df = filtered_df.groupby('has_coupon_bool')['purchased_last_month'].mean().reset_index()
    coupon_df['has_coupon_bool'] = coupon_df['has_coupon_bool'].map({True: 'Has Coupon', False: 'No Coupon'})
    fig_coupon = px.bar(
        coupon_df,
        x='has_coupon_bool',
        y='purchased_last_month',
        title='Avg. Units Sold: With Coupon vs. No Coupon',
        color='has_coupon_bool'
    )
    st.plotly_chart(fig_coupon, use_container_width=True)

with col7:
    # Chart 7: Sustainability Impact (FIXED)
    sustainable_df = filtered_df.groupby('is_sustainable')['product_rating'].mean().reset_index()
    sustainable_df['is_sustainable'] = sustainable_df['is_sustainable'].map({True: 'Sustainable', False: 'Not Sustainable'})
    fig_sustainable = px.bar(
        sustainable_df,
        x='is_sustainable',
        y='product_rating',
        title='Avg. Rating: Sustainable vs. Not Sustainable',
        color='is_sustainable'
    )
    st.plotly_chart(fig_sustainable, use_container_width=True)

# === Raw Data Viewer ===
st.subheader("Raw Data Explorer")
st.write("View the filtered data below.")
st.dataframe(filtered_df)