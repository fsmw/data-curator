Mises Data Viz - Streamlit app

How to run

1. Create a virtualenv and install dependencies:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Run the app:

   streamlit run app_streamlit.py

Notes

- The app reads cleaned CSVs from the directory configured in `config.yaml` (via `src.config.Config`). By default it's `02_Datasets_Limpios` under the project root or the `DATA_ROOT` env var.
- For PNG export of Plotly figures install `kaleido` (already in `requirements.txt`).
- If you need choropleth maps with complex topojsons consider adding `geopandas`/`pycountry`.
