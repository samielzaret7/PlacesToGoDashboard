import streamlit as st
import pandas as pd
from notion_client import Client
from dotenv import load_dotenv
import os
from PIL import Image

# Load environment variables
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Notion client
notion = Client(auth=NOTION_TOKEN)


def get_value(prop, prop_type):
    if prop_type == "title":
        return prop['title'][0]['plain_text'] if prop['title'] else ""
    elif prop_type == "rich_text":
        return prop['rich_text'][0]['plain_text'] if prop['rich_text'] else ""
    elif prop_type == "checkbox":
        return prop['checkbox']
    elif prop_type == "select":
        return prop['select']['name'] if prop['select'] else None
    elif prop_type == "multi_select":
        return [t['name'] for t in prop['multi_select']]
    elif prop_type == "date":
        return prop['date']['start'] if prop['date'] else None
    elif prop_type == "number":
        return prop['number']
    elif prop_type == "url":
        return prop['url']
    else:
        return None

# Fetch pages from Notion
def fetch_places():
    results = []
    next_cursor = None
    while True:
        response = notion.databases.query(
            **{
                "database_id": DATABASE_ID,
                "start_cursor": next_cursor,
                "page_size": 100
            }
        )
        results.extend(response['results'])
        if not response.get('has_more'):
            break
        next_cursor = response.get('next_cursor')
    return results

# Parse Notion data
def parse_notion_data(pages):
    data = []
    for page in pages:
        props = page['properties']
        row = {
            "Place": get_value(props["Place"], "title"),
            "City": get_value(props["City"], "rich_text"),
            "Category": get_value(props["Category"], "select"),
            "Sub-Category": get_value(props["Sub-Category"], "multi_select"),
            "Sub-Category Str": ", ".join(get_value(props["Sub-Category"], "multi_select")),
            "Visited": get_value(props["Visited"], "checkbox"),
            "Visit Date": get_value(props["Visit Date"], "date"),
            "Notes": get_value(props["Notes"], "rich_text"),
            "Pros": get_value(props["Pros"], "rich_text"),
            "Cons": get_value(props["Cons"], "rich_text"),
            "Reservation Required": get_value(props["Reservation Required"], "checkbox"),
            "Rating": get_value(props["Rating"], "number"),
            "Price Range": get_value(props["Price Range"], "select"),
            "Cuisine / Type": ", ".join(get_value(props["Cuisine / Type"], "multi_select")),
            "Address": get_value(props["Address"], "url"),
            "PicURL": get_value(props["PicURL"], "url"),
            "Social": get_value(props["Social"], "url"),
        }
        data.append(row)
    return pd.DataFrame(data)


st.title("📍 Places to Visit Dashboard")

with st.spinner("Fetching data from Notion..."):
    notion_pages = fetch_places()
    df = parse_notion_data(notion_pages)

# Filters
with st.sidebar:
    st.header("🔍 Filters")
    city = st.multiselect("City", df["City"].dropna().unique())
    category = st.multiselect("Category", df["Category"].dropna().unique())
    all_sub_cats = sorted({cat for sublist in df["Sub-Category"].dropna() for cat in sublist})
    sub_category = st.multiselect("Sub-Category", all_sub_cats)
    cuisine_type = st.multiselect("Cuisine / Type", df["Cuisine / Type"].dropna().unique())
    visited = st.radio("Visited?", ["All", "Yes", "No"])
    reservation = st.radio("Reservation Required?", ["All", "Yes", "No"])
    price_range = st.multiselect("Price Range", df["Price Range"].dropna().unique())
    rating = st.slider("Minimum Rating", 0, 5, 0)


filtered_df = df.copy()
if city:
    filtered_df = filtered_df[filtered_df["City"].isin(city)]
if category:
    filtered_df = filtered_df[filtered_df["Category"].isin(category)]
if visited != "All":
    filtered_df = filtered_df[filtered_df["Visited"] == (visited == "Yes")]
if reservation != "All":
    filtered_df = filtered_df[filtered_df["Reservation Required"] == (reservation == "Yes")]
if price_range:
    filtered_df = filtered_df[filtered_df["Price Range"].isin(price_range)]
filtered_df = filtered_df[filtered_df["Rating"].fillna(0) >= rating]
if sub_category:
    filtered_df = filtered_df[filtered_df["Sub-Category"].apply(
        lambda x: any(cat in x for cat in sub_category)
    )]



col1, col2 = st.columns(2)
columns = [col1, col2]

for idx, row in filtered_df.iterrows():
    col = columns[idx % 2]

    with col:
        if row["PicURL"]:
            st.image(row["PicURL"], use_column_width=True)

        st.markdown(f"""
        ### {row['Place']}
        **{row['City']}**  
        {row['Category']}, {', '.join(row['Sub-Category']) if isinstance(row['Sub-Category'], list) else row['Sub-Category']}  
        {row['Cuisine / Type']}  
        💰 {row['Price Range']}           ⭐ {row['Rating'] if pd.notna(row['Rating']) else 'N/A'}  

        ✅ **Pros**: {row['Pros']}  
        ⚠️ **Cons**: {row['Cons']}  
        🔖 **Reservation Required**: {"Yes" if row["Reservation Required"] else "No"}  
        """, unsafe_allow_html=True)

      
        cols = st.columns([1, 1])
        with cols[0]:
            if row["Social"]:
                st.markdown(
                    f'<a href="{row["Social"]}" target="_blank"><img src="/Users/zenmaster/Programming/PlacesToGoDashboard/.assets/social_icon.png" width="24"></a>',
                    unsafe_allow_html=True,
                )
        with cols[1]:
            if row["Address"]:
                st.markdown(
                    f'<a href="{row["Address"]}" target="_blank"><img src=".assets/map_icon.png" width="24"></a>',
                    unsafe_allow_html=True,
                )

        st.markdown("---")
