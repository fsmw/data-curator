import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from pathlib import Path
from src.config import Config
from src.cleaning import DataCleaner

st.set_page_config(page_title="Mises Data Viz", layout="wide", initial_sidebar_state="expanded")

# Load CSS
css_path = Path("styles/custom.css")
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Plotly theme
MY_COLORS = ["#3c5bed", "#3eb2ff", "#f94789", "#00bb84", "#ffb800"]
pio.templates["mises_theme"] = pio.templates["plotly_white"].update({
    "layout": {
        "colorway": MY_COLORS,
        "font": {"family": "Manrope, Arial, sans-serif", "color": "#253347"},
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#ffffff",
    }
})

# Config
config = Config()
clean_dir = config.get_directory('clean')
clean_dir = Path(clean_dir)

# Helper functions
@st.cache_data
def list_datasets():
    if not clean_dir.exists():
        return []
    csvs = sorted([p for p in clean_dir.rglob("*.csv")])
    return csvs

@st.cache_data
def load_csv(path: str):
    try:
        df = pd.read_csv(path)
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None

# UI
st.markdown("<div style='display:flex;align-items:center;gap:16px;'>"
            "<div style='width:48px;height:48px'>{}</div>"
            "<h1 style='margin:0'>Mises Data Viz</h1>"
            "</div>".format(Path("assets/icons/logo.svg").read_text() if Path("assets/icons/logo.svg").exists() else ""), unsafe_allow_html=True)

st.sidebar.header("Dataset")
csv_list = list_datasets()
if not csv_list:
    st.sidebar.info("No CSV files found in the clean datasets directory.")

selected = None
if csv_list:
    display_names = [str(p.relative_to(clean_dir)) for p in csv_list]
    choice = st.sidebar.selectbox("Select dataset", options=["-- none --"] + display_names)
    if choice != "-- none --":
        selected = clean_dir / choice

st.sidebar.markdown("---")
st.sidebar.header("Visual options")
show_choropleth = st.sidebar.checkbox("Enable choropleth (ISO3)", value=True)

if selected:
    df = load_csv(str(selected))
    if df is None:
        st.stop()

    cleaner = DataCleaner(config)
    # Show metadata card
    st.sidebar.header("Metadata")
    summary = cleaner.get_data_summary(df)
    st.sidebar.write("Rows:", summary.get('rows'))
    st.sidebar.write("Columns:", summary.get('columns'))
    if 'year_range' in summary:
        st.sidebar.write("Years:", summary.get('year_range'))

    # Heuristics to find columns
    cols = df.columns.tolist()
    year_col = next((c for c in cols if 'year' in c.lower() or 'año' in c.lower() or c.lower()=='time'), None)
    country_col = next((c for c in cols if 'country' in c.lower() or 'pais' in c.lower() or 'iso' in c.lower()), None)
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

    st.markdown(f"**Selected:** {selected.name}")
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)

    with st.expander("Preview (first 100 rows)"):
        st.dataframe(df.head(100))

    st.markdown("</div>", unsafe_allow_html=True)

    # Controls for visualization
    st.markdown("---")
    st.header("Visualizations")
    var = None
    if numeric_cols:
        var = st.selectbox("Variable (numeric)", options=numeric_cols)
    else:
        st.info("No numeric columns detected to plot.")

    countries = []
    if country_col:
        all_countries = sorted([str(x) for x in df[country_col].dropna().unique()])
        countries = st.multiselect("Countries", options=all_countries, default=all_countries[:6])

    # Year slider
    if year_col:
        try:
            years = pd.to_numeric(df[year_col], errors='coerce').dropna().astype(int)
            year_min, year_max = int(years.min()), int(years.max())
            year_range = st.slider("Year range", min_value=year_min, max_value=year_max, value=(year_min, year_max))
        except Exception:
            year_range = None
    else:
        year_range = None

    # Time series
    if var:
        df_plot = df.copy()
        if country_col and countries:
            df_plot = df_plot[df_plot[country_col].isin(countries)]
        if year_col and year_range:
            df_plot = df_plot[pd.to_numeric(df_plot[year_col], errors='coerce').between(year_range[0], year_range[1])]

        # Ensure year col numeric for sorting
        if year_col:
            df_plot[year_col] = pd.to_numeric(df_plot[year_col], errors='coerce')

        if country_col:
            fig = px.line(df_plot, x=year_col, y=var, color=country_col, markers=True, template='plotly_white')
        else:
            fig = px.line(df_plot, x=year_col, y=var, markers=True, template='plotly_white')

        fig.update_layout(colorway=MY_COLORS, plot_bgcolor='white', paper_bgcolor='white', font=dict(family='Manrope, Arial', color='#253347'))
        st.plotly_chart(fig, use_container_width=True)

        # Download filtered CSV
        csv_bytes = df_plot.to_csv(index=False).encode('utf-8')
        st.download_button(label='Download filtered CSV', data=csv_bytes, file_name=f"{selected.stem}_filtered.csv", mime='text/csv')

        # Download figure as PNG
        try:
            img_bytes = fig.to_image(format='png')
            st.download_button(label='Download figure (PNG)', data=img_bytes, file_name=f"{selected.stem}.png", mime='image/png')
        except Exception:
            st.info('To enable PNG export install `kaleido`')

    # Choropleth
    if show_choropleth and country_col and var:
        # try to detect ISO3 in column
        df_ch = df.copy()
        iso_col = None
        for c in df_ch.columns:
            if c.lower() in ['iso3', 'iso', 'iso_a3', 'country_code']:
                iso_col = c
                break
        if iso_col is None:
            # attempt simple mapping using DataCleaner COUNTRY_CODES
            mapping = DataCleaner.COUNTRY_CODES
            df_ch['iso3_tmp'] = df_ch[country_col].map(lambda x: mapping.get(x, None))
            iso_col = 'iso3_tmp'

        # aggregate by country and last year in range
        if year_col and year_range:
            df_ch = df_ch[pd.to_numeric(df_ch[year_col], errors='coerce').between(year_range[0], year_range[1])]
        agg = df_ch.groupby(iso_col)[var].mean().reset_index()
        agg = agg.dropna()
        if not agg.empty:
            try:
                fig_map = px.choropleth(agg, locations=iso_col, color=var if var in agg.columns else var,
                                        color_continuous_scale=MY_COLORS, template='plotly_white')
                fig_map.update_layout(margin=dict(l=0,r=0,t=30,b=0), font=dict(family='Manrope, Arial', color='#253347'))
                st.plotly_chart(fig_map, use_container_width=True)
            except Exception as e:
                st.info(f"Choropleth error: {e}")

    # Heatmap (country x year)
    if country_col and year_col and var:
        df_h = df.copy()
        df_h = df_h[pd.to_numeric(df_h[year_col], errors='coerce').between(year_range[0], year_range[1])]
        df_h[year_col] = pd.to_numeric(df_h[year_col], errors='coerce').astype(int)
        pivot = df_h.pivot_table(index=country_col, columns=year_col, values=var, aggfunc='mean')
        if not pivot.empty:
            fig_h = px.imshow(pivot, aspect='auto', color_continuous_scale=MY_COLORS, origin='lower')
            fig_h.update_layout(font=dict(family='Manrope, Arial', color='#253347'))
            st.plotly_chart(fig_h, use_container_width=True)

else:
    st.write("Select a dataset from the sidebar to begin.")


