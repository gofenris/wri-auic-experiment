# /// script
# dependencies = [
#     "folium==0.20.0",
#     "geopandas==1.1.4",
#     "marimo",
#     "requests==2.34.2",
#     "shapely==2.1.2",
# ]
# requires-python = ">=3.13"
# ///

import marimo

__generated_with = "0.23.14"
app = marimo.App(width="columns")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Cape Town - Shapefiles
    """)
    return


@app.cell
def _():
    import marimo as mo


    return (mo,)


@app.cell(hide_code=True)
def _(mo):

    mo.md("""
    ## Cape Town Wards

    **Data source:** [City of Cape Town Wards](https://odp-cctegis.opendata.arcgis.com/datasets/cctegis::wards/about) — Official Planning wards (2000, 2006, 2009, 2011, 2016, 2021), City of Cape Town Open Data Portal. Downloaded as GeoJSON.
    """)
    return


@app.cell
def _():
    import geopandas as gpd
    from pathlib import Path

    wards_path = Path(__file__).parent / "data" / "cape_town" / "Wards.geojson"
    wards_raw = gpd.read_file(wards_path)

    print(f"CRS: {wards_raw.crs}")
    print(f"Number of wards (all years): {len(wards_raw)}")
    print(f"Geometry types: {wards_raw.geom_type.unique()}")
    print(f"Columns: {list(wards_raw.columns)}")
    print(f"Ward years present: {sorted(wards_raw['WARD_YEAR'].unique())}")

    latest_year = wards_raw["WARD_YEAR"].max()
    wards = wards_raw[wards_raw["WARD_YEAR"] == latest_year].reset_index(drop=True)
    print(f"Filtered to latest year {latest_year}: {len(wards)} wards")
    wards.head()
    return gpd, wards


@app.cell
def _(wards):
    import folium
    from shapely.geometry import mapping

    sel_ward_name = "54"

    selected_ward = wards[wards["WARD_NAME"] == sel_ward_name]
    assert len(selected_ward) == 1, f"expected exactly 1 match, got {len(selected_ward)}"

    _geom = selected_ward.iloc[0]["geometry"]
    _minx, _miny, _maxx, _maxy = _geom.bounds
    _center_lat, _center_lon = (_miny + _maxy) / 2, (_minx + _maxx) / 2

    selected_ward_map = folium.Map(
        location=[_center_lat, _center_lon],
        zoom_start=13,
        tiles="CartoDB positron",
        width=600,
        height=500,
    )
    folium.GeoJson(
        {"type": "Feature", "geometry": mapping(_geom), "properties": {"name": f"Ward {sel_ward_name}"}},
        style_function=lambda _x: {
            "fillColor": "#2ca02c", "color": "#333",
            "weight": 2, "fillOpacity": 0.35},
        tooltip=f"Ward {sel_ward_name}",
    ).add_to(selected_ward_map)

    selected_ward_map
    return folium, mapping


@app.cell
def _(mo):
    mo.md("""
    ## Cape Town Suburbs

    **Data source:** [Official Planning Suburbs (February 2019)](https://gis.westerncape.gov.za/server2/rest/services/SpatialDataWarehouse/CoCT_Management_Boundaries/MapServer/23) — City of Cape Town / Western Cape Government ArcGIS REST service. Fetched directly via the REST query endpoint (GeoJSON, EPSG:4326) — 776 suburbs total, sampling a subset for this experiment.
    """)
    return


@app.cell(hide_code=True)
def _(gpd):
    import requests

    suburbs_url = "https://gis.westerncape.gov.za/server2/rest/services/SpatialDataWarehouse/CoCT_Management_Boundaries/MapServer/23/query"
    suburbs_params = {
        "where": "1=1",
        "outFields": "*",
        "f": "geojson",
        "outSR": "4326",
        "resultRecordCount": 20,
    }

    _response = requests.get(suburbs_url, params=suburbs_params, timeout=10)
    suburbs_geojson = _response.json()

    suburbs = gpd.GeoDataFrame.from_features(suburbs_geojson["features"], crs="EPSG:4326")

    print(f"Number of suburbs fetched: {len(suburbs)}")
    print(f"Geometry types: {suburbs.geom_type.unique()}")
    print(f"Columns: {list(suburbs.columns)}")
    suburbs.head()
    return (suburbs,)


@app.cell
def _(suburbs):
    # list the available suburbs 
    suburbs["OFC_SBRB_N"].tolist()[:20]
    return


@app.cell
def _(folium, mapping, suburbs):
    sel_suburb_name = "KHAYELITSHA"

    selected_suburb = suburbs[suburbs["OFC_SBRB_N"] == sel_suburb_name]
    assert len(selected_suburb) == 1, f"expected exactly 1 match, got {len(selected_suburb)}"

    _geom = selected_suburb.iloc[0]["geometry"]
    _minx, _miny, _maxx, _maxy = _geom.bounds
    _center_lat, _center_lon = (_miny + _maxy) / 2, (_minx + _maxx) / 2

    selected_suburb_map = folium.Map(
        location=[_center_lat, _center_lon],
        zoom_start=13,
        tiles="CartoDB positron",
        width=600,
        height=500,
    )
    folium.GeoJson(
        {"type": "Feature", "geometry": mapping(_geom), "properties": {"name": sel_suburb_name}},
        style_function=lambda _x: {
            "fillColor": "#1a7be0", "color": "#333",
            "weight": 2, "fillOpacity": 0.35},
        tooltip=sel_suburb_name,
    ).add_to(selected_suburb_map)

    selected_suburb_map
    return


if __name__ == "__main__":
    app.run()
