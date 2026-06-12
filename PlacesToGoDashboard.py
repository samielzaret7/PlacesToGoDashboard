import base64
import streamlit as st
import pandas as pd
from datetime import datetime
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

# ── Google Sheets backend ────────────────────────────────────────────────────────
# The dashboard reads from a Google Sheet shared as "Anyone with the link → Viewer".
# We pull the `places` tab as CSV via the public gviz endpoint (no credentials).
# Edit places directly in Google Sheets; this dashboard is read-only.
SHEET_ID = st.secrets["SHEET_ID"]
PLACES_TAB = "places"
SHEET_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/gviz/tq?tqx=out:csv&sheet={PLACES_TAB}"
)

# Sheet column (snake_case) → app field name used throughout the UI.
COLUMN_MAP = {
    "place": "Place",
    "city": "City",
    "category": "Category",
    "sub_category": "Sub-Category",
    "cuisine_type": "Cuisine / Type",
    "visited": "Visited",
    "visit_date": "Visit Date",
    "rating": "Rating",
    "price_range": "Price Range",
    "reservation_required": "Reservation Required",
    "notes": "Notes",
    "pros": "Pros",
    "cons": "Cons",
    "address_url": "Address",
    "pic_url": "PicURL",
    "social_url": "Social",
}


def _to_bool(value):
    return str(value).strip().upper() == "TRUE"


def _to_list(value):
    if pd.isna(value) or not str(value).strip():
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


@st.cache_data(ttl=3600)
def fetch_and_parse():
    raw = pd.read_csv(SHEET_CSV_URL, dtype=str)

    # Soft-delete: hide archived rows by default.
    if "archived" in raw.columns:
        raw = raw[raw["archived"].fillna("").str.strip().str.upper() != "TRUE"]

    df = pd.DataFrame()
    for src_col, app_col in COLUMN_MAP.items():
        df[app_col] = raw[src_col] if src_col in raw.columns else None

    # Multi-select fields are comma-separated strings in the Sheet.
    df["Sub-Category"] = df["Sub-Category"].apply(_to_list)
    df["Cuisine / Type"] = df["Cuisine / Type"].apply(_to_list)

    # Checkboxes are TRUE/FALSE text in the Sheet.
    df["Visited"] = df["Visited"].apply(_to_bool)
    df["Reservation Required"] = df["Reservation Required"].apply(_to_bool)

    # Numeric field; keep missing dates as None so truthiness checks work.
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    df["Visit Date"] = df["Visit Date"].where(df["Visit Date"].notna(), None)

    # Text/URL fields: empty cells become "" so they render blank (not "None")
    # and stay falsy for the conditional image/link rendering on the cards.
    for col in ["Place", "City", "Category", "Price Range",
                "Notes", "Pros", "Cons", "Address", "PicURL", "Social"]:
        df[col] = df[col].fillna("")

    return df.reset_index(drop=True)


@st.cache_data
def get_filter_options(df):
    cities = sorted(df["City"].dropna().unique())
    categories = sorted(df["Category"].dropna().unique())
    sub_cats = sorted({cat for sublist in df["Sub-Category"].dropna() for cat in sublist})
    cuisines = sorted({c for sublist in df["Cuisine / Type"].dropna() for c in sublist})
    prices = sorted(df["Price Range"].dropna().unique(), key=lambda x: len(x))
    return cities, categories, sub_cats, cuisines, prices


st.title("📍 Places to Visit")


with st.spinner("Fetching data from Google Sheets..."):
    df = fetch_and_parse()

cities, categories, sub_cat_options, cuisine_options, price_options = get_filter_options(df)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

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

    if row['Visited']:
        if row['Visit Date']:
            date_str = datetime.strptime(row['Visit Date'], "%Y-%m-%d").strftime("%B %d, %Y")
            visited_line = f'✅ <strong>Visited</strong> · {date_str}'
        else:
            visited_line = '✅ <strong>Visited</strong>'
        card_bg = "#e8f5e9"
    else:
        visited_line = '○ Not visited yet'
        card_bg = "#eeeeee"

    img_html = (f'<img src="{row["PicURL"]}" style="width: 100%; border-radius: 12px;" />'
                if row["PicURL"] else '')
    social_html = (f'<a href="{row["Social"]}" target="_blank"><img src="data:image/png;base64,{social_icon}" '
                   f'width="60" height="60" title="Instagram"/></a>' if row["Social"] else '')
    map_html = (f'<a href="{row["Address"]}" target="_blank"><img src="data:image/png;base64,{map_icon}" '
                f'width="60" height="60" title="Map Location"/></a>' if row["Address"] else '')
    rating_str = row['Rating'] if pd.notna(row['Rating']) else 'N/A'
    reservation_str = "Yes" if row["Reservation Required"] else "No"

    # Built as one continuous string (no newlines): a blank line inside an HTML
    # block would terminate it and make Markdown render the rest as a code block.
    card_html = (
        f'<div style="background-color: {card_bg}; color: #000; border-radius: 18px; '
        f'padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 6px rgba(0,0,0,0.06);">'
        f'{img_html}'
        f'<h3 style="margin-top: 1em;">{row["Place"]}</h3>'
        f'<p style="margin: 4px 0 12px 0; color: #555;">{visited_line}</p>'
        f'<p><strong>{row["City"]}</strong><br>{sub_cats_str}<br>{cuisines_str}<br>'
        f'💰 {row["Price Range"]} &nbsp;&nbsp; ⭐ {rating_str}<br>'
        f'✅ <strong>Pros:</strong> {row["Pros"]}<br>'
        f'⚠️ <strong>Cons:</strong> {row["Cons"]}<br>'
        f'🧮 <strong>Reservation Required:</strong> {reservation_str}</p>'
        f'<div style="display: flex; justify-content: center; align-items: center; '
        f'gap: 50px; margin-top: 16px;">'
        f'{social_html}{map_html}'
        f'</div>'
        f'</div>'
    )

    with col:
        st.markdown(card_html, unsafe_allow_html=True)
