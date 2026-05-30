# PlacesToGoDashboard

A Streamlit dashboard that pulls place data from a Notion database and displays it as filterable, paginated cards. Browse restaurants, bars, cafes, and attractions you want to visit (or have already visited), complete with ratings, price ranges, and map/social links.

## Features

- Fetches and caches data from a Notion database (auto-refreshes every hour)
- Sidebar filters: city, category, sub-category, cuisine/type, visited status, reservation required, price range, and minimum rating
- Text search by place name or city
- Sortable by rating, price range, visit date, or visited status
- Paginated card layout with images, pros/cons, and quick links to maps and social profiles
- Add new places directly from the sidebar (writes back to Notion)

## Setup

1. Clone the repo and install dependencies:

```bash
pip install -r requirements.txt
```

2. Create `.streamlit/secrets.toml` with your Notion credentials:

```toml
NOTION_API_KEY = "secret_..."
NOTION_DATABASE_ID = "..."
```

You can also use a `.env` file — see `.env.example` for the format.

3. Run the app:

```bash
streamlit run PlacesToGoDashboard.py
```

The app runs on `http://localhost:8501` by default.

## Notion Database Schema

The connected Notion database should have these properties:

| Property | Type |
|----------|------|
| Place | Title |
| City | Rich text |
| Category | Select |
| Sub-Category | Multi-select |
| Visited | Checkbox |
| Visit Date | Date |
| Notes / Pros / Cons | Rich text |
| Reservation Required | Checkbox |
| Rating | Number (0–5) |
| Price Range | Select ($, $$, $$$) |
| Cuisine / Type | Multi-select |
| Address | URL (map link) |
| PicURL | URL (image) |
| Social | URL (Instagram, etc.) |

## Tech Stack

- Python 3.11+
- Streamlit
- Notion API (via `notion-client`)
- Pandas
