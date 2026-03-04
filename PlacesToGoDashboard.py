import streamlit as st
import pandas as pd
from notion_client import Client
import base64
from streamlit_scroll_to_top import scroll_to_here

st.set_page_config(layout="wide")

if 'scroll_to_top' not in st.session_state:
    st.session_state.scroll_to_top = False

if st.session_state.scroll_to_top:
    scroll_to_here(0, key='top')
    st.session_state.scroll_to_top = False

def scroll_to_top():
    st.session_state.scroll_to_top = True


@st.cache_data
def load_icon_as_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

social_icon = load_icon_as_base64(".assets/social_icon.png")
map_icon = load_icon_as_base64(".assets/map_icon.png")

NOTION_TOKEN = st.secrets["NOTION_API_KEY"]
DATABASE_ID = st.secrets["NOTION_DATABASE_ID"]

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


@st.cache_data(ttl=3600)
def fetch_and_parse():
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

    data = []
    for page in results:
        props = page['properties']
        row = {
            "Place": get_value(props["Place"], "title"),
            "City": get_value(props["City"], "rich_text"),
            "Category": get_value(props["Category"], "select"),
            "Sub-Category": get_value(props["Sub-Category"], "multi_select"),
            "Visited": get_value(props["Visited"], "checkbox"),
            "Visit Date": get_value(props["Visit Date"], "date"),
            "Notes": get_value(props["Notes"], "rich_text"),
            "Pros": get_value(props["Pros"], "rich_text"),
            "Cons": get_value(props["Cons"], "rich_text"),
            "Reservation Required": get_value(props["Reservation Required"], "checkbox"),
            "Rating": get_value(props["Rating"], "number"),
            "Price Range": get_value(props["Price Range"], "select"),
            "Cuisine / Type": get_value(props["Cuisine / Type"], "multi_select"),
            "Address": get_value(props["Address"], "url"),
            "PicURL": get_value(props["PicURL"], "url"),
            "Social": get_value(props["Social"], "url"),
        }
        data.append(row)
    return pd.DataFrame(data)


@st.cache_data
def get_filter_options(df):
    cities = sorted(df["City"].dropna().unique())
    categories = sorted(df["Category"].dropna().unique())
    sub_cats = sorted({cat for sublist in df["Sub-Category"].dropna() for cat in sublist})
    cuisines = sorted({c for sublist in df["Cuisine / Type"].dropna() for c in sublist})
    prices = sorted(df["Price Range"].dropna().unique(), key=lambda x: len(x))
    return cities, categories, sub_cats, cuisines, prices


def add_place_to_notion(place_name, city, category, sub_cats, cuisines, price_range,
                        rating, visited, visit_date, reservation, pros, cons, notes,
                        pic_url, address, social):
    props = {
        "Place": {"title": [{"text": {"content": place_name}}]},
        "City": {"rich_text": [{"text": {"content": city}}]},
        "Visited": {"checkbox": visited},
        "Reservation Required": {"checkbox": reservation},
    }
    if category:
        props["Category"] = {"select": {"name": category}}
    if sub_cats:
        props["Sub-Category"] = {"multi_select": [{"name": s} for s in sub_cats]}
    if cuisines:
        props["Cuisine / Type"] = {"multi_select": [{"name": c} for c in cuisines]}
    if price_range:
        props["Price Range"] = {"select": {"name": price_range}}
    if rating:
        props["Rating"] = {"number": rating}
    if visited and visit_date:
        props["Visit Date"] = {"date": {"start": str(visit_date)}}
    if pros:
        props["Pros"] = {"rich_text": [{"text": {"content": pros}}]}
    if cons:
        props["Cons"] = {"rich_text": [{"text": {"content": cons}}]}
    if notes:
        props["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
    if pic_url:
        props["PicURL"] = {"url": pic_url}
    if address:
        props["Address"] = {"url": address}
    if social:
        props["Social"] = {"url": social}
    notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties=props
    )


st.title("📍 Places to Visit")

theme = st.get_option("theme.base")
if theme == "dark":
    card_bg = "#1E1E1E"
else:
    card_bg = "#FFFFFF"

with st.spinner("Fetching data from Notion..."):
    df = fetch_and_parse()

cities, categories, sub_cat_options, cuisine_options, price_options = get_filter_options(df)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Add New Place
    with st.expander("➕ Add New Place"):
        with st.form("add_place_form", clear_on_submit=True):
            new_place = st.text_input("Place Name *")
            new_city = st.text_input("City")
            new_category = st.selectbox("Category", [""] + list(categories))
            new_sub_cats = st.multiselect("Sub-Category", sub_cat_options)
            new_cuisines = st.multiselect("Cuisine / Type", cuisine_options)
            new_price = st.selectbox("Price Range", ["", "$", "$$", "$$$"])
            new_rating = st.slider("Rating", 0, 5, 0)
            new_visited = st.checkbox("Visited")
            new_visit_date = st.date_input("Visit Date", value=None)
            new_reservation = st.checkbox("Reservation Required")
            new_pros = st.text_area("Pros")
            new_cons = st.text_area("Cons")
            new_notes = st.text_area("Notes")
            new_pic = st.text_input("Image URL")
            new_address = st.text_input("Map URL")
            new_social = st.text_input("Social URL")
            submitted = st.form_submit_button("Add Place")

            if submitted:
                if not new_place.strip():
                    st.error("Place name is required.")
                else:
                    try:
                        add_place_to_notion(
                            new_place.strip(),
                            new_city.strip(),
                            new_category or None,
                            new_sub_cats,
                            new_cuisines,
                            new_price or None,
                            new_rating if new_rating > 0 else None,
                            new_visited,
                            new_visit_date if new_visited else None,
                            new_reservation,
                            new_pros.strip(),
                            new_cons.strip(),
                            new_notes.strip(),
                            new_pic.strip() or None,
                            new_address.strip() or None,
                            new_social.strip() or None,
                        )
                        st.success(f"✅ '{new_place}' added!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding place: {e}")

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
    search = st.text_input("Search by name or city", placeholder="Type to search...")

    if st.button("✖ Clear All Filters"):
        for key in ["city_f", "cat_f", "sub_f", "cui_f", "vis_f", "res_f", "price_f", "rating_f"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    city = st.multiselect("City", cities, key="city_f")
    category = st.multiselect("Category", categories, key="cat_f")
    sub_category = st.multiselect("Sub-Category", sub_cat_options, key="sub_f")
    cuisine_type = st.multiselect("Cuisine / Type", cuisine_options, key="cui_f")
    visited = st.radio("Visited?", ["All", "Yes", "No"], key="vis_f")
    reservation = st.radio("Reservation Required?", ["All", "Yes", "No"], key="res_f")
    price_range = st.multiselect("Price Range", price_options, key="price_f")
    rating = st.slider("Minimum Rating", 0, 5, 0, key="rating_f")


# ── Filtering ──────────────────────────────────────────────────────────────────
filtered_df = df.copy()

if search:
    mask = (
        df["Place"].str.contains(search, case=False, na=False) |
        df["City"].str.contains(search, case=False, na=False)
    )
    filtered_df = filtered_df[mask]
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
        lambda x: bool(x) and any(cat in x for cat in sub_category)
    )]
if cuisine_type:
    filtered_df = filtered_df[filtered_df["Cuisine / Type"].apply(
        lambda x: bool(x) and any(c in x for c in cuisine_type)
    )]

# ── Sorting ────────────────────────────────────────────────────────────────────
if sort_option == "Rating (High to Low)":
    filtered_df = filtered_df.sort_values(by="Rating", ascending=False)
elif sort_option == "Rating (Low to High)":
    filtered_df = filtered_df.sort_values(by="Rating", ascending=True)
elif sort_option == "Price Range ($ to $$$)":
    price_order = {"$": 1, "$$": 2, "$$$": 3}
    filtered_df = filtered_df.copy()
    filtered_df["_price_rank"] = filtered_df["Price Range"].map(price_order)
    filtered_df = filtered_df.sort_values(by="_price_rank", ascending=True).drop(columns=["_price_rank"])
elif sort_option == "Price Range ($$$ to $)":
    price_order = {"$": 1, "$$": 2, "$$$": 3}
    filtered_df = filtered_df.copy()
    filtered_df["_price_rank"] = filtered_df["Price Range"].map(price_order)
    filtered_df = filtered_df.sort_values(by="_price_rank", ascending=False).drop(columns=["_price_rank"])
elif sort_option == "Visit Date (Newest)":
    filtered_df = filtered_df.sort_values(by="Visit Date", ascending=False)
elif sort_option == "Visit Date (Oldest)":
    filtered_df = filtered_df.sort_values(by="Visit Date", ascending=True)
elif sort_option == "Visited First":
    filtered_df = filtered_df.sort_values(by="Visited", ascending=False)
elif sort_option == "Not Visited First":
    filtered_df = filtered_df.sort_values(by="Visited", ascending=True)


# ── Layout ─────────────────────────────────────────────────────────────────────
left_col, divider_col, right_col = st.columns([1, 0.02, 1])
columns = [left_col, right_col]

with divider_col:
    st.markdown("<div style='height: 100%; border-left: 1px solid #ddd;'></div>", unsafe_allow_html=True)

st.caption(f"Showing **{len(filtered_df)}** of **{len(df)}** places")

# ── Pagination ─────────────────────────────────────────────────────────────────
st.markdown("---")
if "selected_page" not in st.session_state:
    st.session_state.selected_page = 1

pagination_col1, pagination_col2 = st.columns([1, 1])
with pagination_col1:
    items_per_page = st.selectbox("Items per page", [4, 6, 8, 10], index=1)
with pagination_col2:
    total_pages = max(1, (len(filtered_df) - 1) // items_per_page + 1)
    page = st.selectbox("Page", options=list(range(1, total_pages + 1)))

if page != st.session_state.selected_page:
    st.session_state.selected_page = page
    scroll_to_top()
    st.rerun()

start = (page - 1) * items_per_page
end = start + items_per_page
paged_df = filtered_df.iloc[start:end]

# ── Cards ──────────────────────────────────────────────────────────────────────
for card_idx, (_, row) in enumerate(paged_df.iterrows()):
    col = columns[card_idx % 2]
    sub_cats_str = ', '.join(row['Sub-Category']) if isinstance(row['Sub-Category'], list) else (row['Sub-Category'] or '')
    cuisines_str = ', '.join(row['Cuisine / Type']) if isinstance(row['Cuisine / Type'], list) else (row['Cuisine / Type'] or '')
    with col:
        st.markdown(f"""
        <div style="
            background-color: #eeeeee;
            color: #000;
            border-radius: 18px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
        ">
            <img src="{row['PicURL']}" style="width: 100%; border-radius: 12px;" />
            <h3 style="margin-top: 1em;">{row['Place']}</h3>
            <p><strong>{row['City']}</strong><br>
            {sub_cats_str}<br>
            {cuisines_str}<br>
            💰 {row['Price Range']} &nbsp;&nbsp; ⭐ {row['Rating'] if pd.notna(row['Rating']) else 'N/A'}<br>
            ✅ <strong>Pros:</strong> {row['Pros']}<br>
            ⚠️ <strong>Cons:</strong> {row['Cons']}<br>
            🧮 <strong>Reservation Required:</strong> {"Yes" if row["Reservation Required"] else "No"}</p>
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
