import pandas as pd
import dash
from dash import dcc, html
import plotly.express as px

# Load data to DataFrame
df = pd.read_csv("vaccinations.csv", low_memory=False)

# Clean/select data (example assumes columns like County, State, Date, Vaccination_Rate)
df = df[['Date', 'Recip_State', 'Recip_County', 'Series_Complete_Pop_Pct']]
df['Date'] = pd.to_datetime(df['Date'])

# Dash app (Created and creates Title of Tab)
app = dash.Dash(__name__)
app.title = "US Vaccination Dashboard"

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
        title=f"Vaccination Over Time in {selected_state}")
    return fig

if __name__ == "__main__":
    app.run(debug=True)
