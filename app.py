import os
import io
import urllib.request
import urllib.parse
import pandas as pd
import dash
from dash import dcc, html
import plotly.express as px

# ---------------------------
# Data loading (Drive-safe)
# ---------------------------

# Google Drive FILE ID (from the /d/<ID>/ URL)
FILE_ID = "1hfH9rL7Eeee4SNaFKHFkZVy4L4Kji47-"

# Direct download endpoints
PRIMARY_URL   = f"https://drive.usercontent.google.com/download?id={FILE_ID}&export=download&confirm=t"
FALLBACK_URL1 = f"https://drive.google.com/uc?export=download&id={FILE_ID}"
FALLBACK_URL2 = f"https://drive.google.com/uc?id={FILE_ID}"

LOCAL_SAMPLE = "data/sample_vaccinations.csv"  

HTML_PREFIX = b"<!DOCTYPE html"  # quick check to detect if it accidentally downloaded a web page

def read_csv_from_url(url: str) -> pd.DataFrame:
    """Download bytes from a URL and read as CSV. Raises if HTML is returned."""
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    # If Google sends a virus-scan HTML, it starts with <!DOCTYPE html
    if data.strip().lower().startswith(HTML_PREFIX):
        # Print a tiny snippet for debugging
        snippet = data[:200].decode("utf-8", errors="ignore")
        raise ValueError(f"Expected CSV but got HTML from {url!r}.\nSnippet: {snippet}")
    return pd.read_csv(io.BytesIO(data), low_memory=False)

def load_drive_csv_or_sample() -> pd.DataFrame:
    # 1) Prefer a small local sample (fast + works offline)
    if os.path.exists(LOCAL_SAMPLE):
        return pd.read_csv(LOCAL_SAMPLE, low_memory=False)

    # 2) Try usercontent direct download first (best for large files)
    try:
        return read_csv_from_url(PRIMARY_URL)
    except Exception:
        pass

    # 3) Try standard uc?export=download
    try:
        return read_csv_from_url(FALLBACK_URL1)
    except Exception:
        pass

    # 4) Last resort: plain uc?id=...
    return read_csv_from_url(FALLBACK_URL2)

def normalize_to_expected_columns(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Map whatever headers we get to your expected four columns."""
    cols = {c.lower(): c for c in df_raw.columns}

    def pick(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None

    date_col   = pick("date", "report_date", "as_of_date", "Date".lower())
    state_col  = pick("recip_state", "state", "location", "jurisdiction", "Recip_State".lower())
    county_col = pick("recip_county", "county", "county_name", "Recip_County".lower())
    pct_col    = pick(
        "series_complete_pop_pct",
        "percent_fully_vaccinated",
        "people_fully_vaccinated_per_hundred",
        "series_complete_percent",
        "Series_Complete_Pop_Pct".lower()
    )

    if date_col is None or state_col is None or pct_col is None:
        raise KeyError(
            "Could not find required columns in the CSV.\n"
            f"First columns present: {list(df_raw.columns)[:12]} ...\n"
            "Needed: a date column (date/report_date/as_of_date), a state column "
            "(recip_state/state/location), and a percent column "
            "(series_complete_pop_pct / people_fully_vaccinated_per_hundred / etc.)."
        )

    df = pd.DataFrame({
        "Date": pd.to_datetime(df_raw[date_col], errors="coerce"),
        "Recip_State": df_raw[state_col].astype(str),
        # If no county present, reuse state so the color legend still works
        "Recip_County": (
            df_raw[county_col].astype(str) if county_col else df_raw[state_col].astype(str)
        ),
        "Series_Complete_Pop_Pct": pd.to_numeric(df_raw[pct_col], errors="coerce"),
    }).dropna(subset=["Date", "Series_Complete_Pop_Pct"])

    return df

# Loads the data
df_raw = load_drive_csv_or_sample()
df = normalize_to_expected_columns(df_raw)

# Dash app (Created and creates Title of Tab)
app = dash.Dash(__name__)
app.title = "US Vaccination Dashboard"
server = app.server  # useful if you deploy later (e.g., Render)

# Layout (whats on the screen)
app.layout = html.Div([
    html.H1("US County Vaccination Rates"),
    dcc.Dropdown(
        id="state-dropdown",
        options=[{'label': s, 'value': s} for s in sorted(df['Recip_State'].dropna().unique())],
        value="IN",  # Default state
        placeholder="Select a state"
    ),
    dcc.Graph(id="vacc-chart")
])

# Callback
@app.callback(
    dash.dependencies.Output("vacc-chart", "figure"),
    [dash.dependencies.Input("state-dropdown", "value")]
)
def update_chart(selected_state):
    print(f"Selected state: {selected_state}")
    print("Column names:", df.columns)
    print("Unique state:", df['Recip_State'].unique())
    filtered = df[df['Recip_State'] == selected_state]
    fig = px.line(
        filtered, 
        x="Date", 
        y="Series_Complete_Pop_Pct", 
        color="Recip_County",
        labels={
            "Series_Complete_Pop_Pct": "Vaccination Rate (%)",
            "Recip_County": "County" 
        },
        title=f"Vaccination Over Time in {selected_state}"
    )
    return fig

if __name__ == "__main__":
    app.run(debug=True)
