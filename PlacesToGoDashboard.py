import streamlit as st
import pandas as pd
from notion_client import Client
import base64



def load_icon_as_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

social_icon = load_icon_as_base64(".assets/social_icon.png")
map_icon = load_icon_as_base64(".assets/map_icon.png")

NOTION_TOKEN = st.secrets["NOTION_API_KEY"]
DATABASE_ID = st.secrets["NOTION_DATABASE_ID"]

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
            "Cuisine / Type": get_value(props["Cuisine / Type"], "multi_select"),
            "Cuisine / Type (Str)": ", ".join(get_value(props["Cuisine / Type"], "multi_select")),
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

    st.header("🔀 Sort By")
    sort_option = st.selectbox(
        "Select one of the following options",
        [
            "Default",
            "Rating (High to Low)",
            "Rating (Low to High)",
            "Price Range ($ to $$$)",
            "Price Range ($$$ to $)",
            "Visit Date (Newest)",
            "Visit Date (Oldest)",
            "Visited First",
            "Not Visited First",
        ]
    )
    st.header("🔍 Filters")
    city = st.multiselect("City", df["City"].dropna().unique())
    category = st.multiselect("Category", df["Category"].dropna().unique())
    all_sub_cats = sorted({cat for sublist in df["Sub-Category"].dropna() for cat in sublist})
    sub_category = st.multiselect("Sub-Category", all_sub_cats)
    all_cuisine_types = sorted({c for sublist in df["Cuisine / Type"].dropna() for c in sublist})
    cuisine_type = st.multiselect("Cuisine / Type", all_cuisine_types)
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
if cuisine_type:
    filtered_df = filtered_df[filtered_df["Cuisine / Type"].apply(
        lambda x: any(c in x for c in cuisine_type)
    )]

if sort_option == "Rating (High to Low)":
    filtered_df = filtered_df.sort_values(by="Rating", ascending=False)
elif sort_option == "Rating (Low to High)":
    filtered_df = filtered_df.sort_values(by="Rating", ascending=True)
elif sort_option == "Price Range ($ to $$$)":
    price_order = {"$": 1, "$$": 2, "$$$": 3}
    filtered_df["Price Rank"] = filtered_df["Price Range"].map(price_order)
    filtered_df = filtered_df.sort_values(by="Price Rank", ascending=True)
elif sort_option == "Price Range ($$$ to $)":
    price_order = {"$": 1, "$$": 2, "$$$": 3}
    filtered_df["Price Rank"] = filtered_df["Price Range"].map(price_order)
    filtered_df = filtered_df.sort_values(by="Price Rank", ascending=False)
elif sort_option == "Visit Date (Newest)":
    filtered_df = filtered_df.sort_values(by="Visit Date", ascending=False)
elif sort_option == "Visit Date (Oldest)":
    filtered_df = filtered_df.sort_values(by="Visit Date", ascending=True)
elif sort_option == "Visited First":
    filtered_df = filtered_df.sort_values(by="Visited", ascending=False)
elif sort_option == "Not Visited First":
    filtered_df = filtered_df.sort_values(by="Visited", ascending=True)


left_col, divider_col, right_col = st.columns([1, 0.02, 1])
columns = [left_col, right_col]


with divider_col:
    st.markdown("<div style='height: 100%; border-left: 1px solid #ddd;'></div>", unsafe_allow_html=True)

for idx, row in filtered_df.iterrows():
    col = columns[idx % 2]

    with col:
       
        st.markdown(f"""
        <div style="
            background-color: #f9f9f9;
            border-radius: 18px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
        ">
            <img src="{row['PicURL']}" style="width: 100%; border-radius: 12px;" />
            <h3 style="margin-top: 1em;">{row['Place']}</h3>
            <p><strong>{row['City']}</strong><br>
            {', '.join(row['Sub-Category']) if isinstance(row['Sub-Category'], list) else row['Sub-Category']}<br>
            {', '.join(row['Cuisine / Type']) if isinstance(row['Cuisine / Type'], list) else row['Cuisine / Type']}<br>
            💰 {row['Price Range']} &nbsp;&nbsp; ⭐ {row['Rating'] if pd.notna(row['Rating']) else 'N/A'}<br>
            ✅ <strong>Pros:</strong> {row['Pros']}<br>
            ⚠️ <strong>Cons:</strong> {row['Cons']}<br>
            🧾 <strong>Reservation Required:</strong> {"Yes" if row["Reservation Required"] else "No"}</p>
            <div style="
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 50px;
            margin-top: 16px;
            ">
            {f'<a href="{row["Social"]}" target="_blank"><img src="data:image/png;base64,{social_icon}" width="60" height="60" title="Instagram"/></a>' if row["Social"] else ''}
            {f'<a href="{row["Address"]}" target="_blank"><img src="data:image/png;base64,{map_icon}" width="60" height="60" title="Map Location"/></a>' if row["Address"] else ''}
        </div>
        </div>

        """, unsafe_allow_html=True)



