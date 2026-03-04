# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A single-page Streamlit dashboard that reads place data from a Notion database and displays it as filterable, paginated cards. The entire app lives in [PlacesToGoDashboard.py](PlacesToGoDashboard.py).

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run PlacesToGoDashboard.py
```

The app runs on port 8501 by default.

## Secrets

The app requires two secrets in `.streamlit/secrets.toml` (not committed):

```toml
NOTION_API_KEY = "secret_..."
NOTION_DATABASE_ID = "..."
```

These are accessed via `st.secrets["NOTION_API_KEY"]` and `st.secrets["NOTION_DATABASE_ID"]`.

## Architecture

The app is a single file with this flow:

1. **Data fetching** — `fetch_and_parse()` queries the Notion database with pagination (100 results per request), maps each page's properties into a flat dict, and returns a `pd.DataFrame`. Cached with `@st.cache_data(ttl=3600)`.

2. **Notion property schema** — The database has these fields: `Place` (title), `City` (rich_text), `Category` (select), `Sub-Category` (multi_select), `Visited` (checkbox), `Visit Date` (date), `Notes`/`Pros`/`Cons` (rich_text), `Reservation Required` (checkbox), `Rating` (number), `Price Range` (select), `Cuisine / Type` (multi_select), `Address` (url), `PicURL` (url), `Social` (url).

3. **Sidebar filters & sort** — City, Category, Sub-Category, Cuisine/Type, Visited, Reservation Required, Price Range, Rating (slider), and sort order are all applied to `filtered_df`.

4. **Pagination** — Items are paginated client-side. Page changes trigger `scroll_to_here()` via session state.

5. **Card rendering** — Cards are rendered in two columns using raw HTML via `st.markdown(..., unsafe_allow_html=True)`. Icons (social/map) are embedded as base64-encoded PNGs from [.assets/](.assets/).

## Known Issue

There is a bug on line 219: `filtered_df = df` overwrites the filtered dataframe before pagination, so filters have no effect on displayed cards. The filtering logic above (lines 150–169) is correct but gets discarded.
