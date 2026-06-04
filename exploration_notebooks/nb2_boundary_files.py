# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "geopandas==1.1.3",
#     "requests==2.34.2",
#     "pmtiles==3.7.0",
#     "folium==0.20.0",
#     "pyarrow",
#     "mapbox-vector-tile==2.2.0",
#     "mercantile==1.2.1",
#     "pandas==3.0.3",
#     "shapely==2.1.2",
#     "openlayers==0.1.6",
#     "rasterio==1.5.0",
#     "pillow==12.2.0",
#     "numpy==2.4.6",
# ]
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import geopandas as gpd
    import requests
    import json
    import pandas as pd
    import numpy as np

    return gpd, mo, np, pd, requests


@app.cell
def _():

    ## for folium map approach
    import folium
    from folium import GeoJson

    # for OL approach
    import openlayers as ol
    from openlayers.basemaps import CartoBasemapLayer, Carto

    # for operations on the PM TILE
    import mapbox_vector_tile
    import mercantile

    return Carto, CartoBasemapLayer, folium, mapbox_vector_tile, mercantile, ol


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Notebook 2: Geospatial Data — Campinas

    This notebook fetches and inspects the geospatial data for Campinas (BRA-Campinas).

    This consists of
    * GeoJSON (`.geojson` ): Boundaries + scalar indicators for city/districts/AOIs
       * multiple features and geometries, each feature has multiple indicators
       * this notebook fetches BRA-Campinas.geojson from S3
       * inspects feature count, geometry types, AOI IDs
       * visualizes all four geo_levels (city, urban_extent, accelerator_area, 7 districts)
   * PMTiles (`.pmtiles`): Same data tiled for web map rendering (MVT, z0–13)
       * Fetches BRA-Campinas.pmtiles
       * reads the PMTiles header (spec version, file size);
       * builds an interactive OpenLayers map with click interaction to read tile features
    * COG (`.tif`) Raster pixel-level indicator maps
        * Lists all COG files across all CCL cities via S3 ListObjects 
        * fetches 1 or more COG files for Campinas
        * fetches and displays metadata (dimensions, CRS, pixel size, overviews)  
        * renders thumbnail previews

    These files are
    * stored on S3 as GeoJSON and PMTiles.
    * URIs and metadata are available through the CCL API (see notebook 1)

    ## What We're Looking For
    * identify where baselines, model outputs and scenario outputs live
    * explore limits of the scenario outputs
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 1. GeoJSON

    Fetch and explore GeoJSON
    * identify and map the features
    * summarize data on each feature
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 1.1 Fetch GeoJSON and summarize
    """)
    return


@app.cell
def _(requests):
    geojson_url = "https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/dev/boundaries/geojson/BRA-Campinas.geojson"

    # Fetch the GeoJSON
    response = requests.get(geojson_url)
    geojson_data = response.json()
    return geojson_data, geojson_url


@app.cell
def _(geojson_data):
    # Inspect structure
    _feature_count = len(geojson_data["features"])
    geometry_types = set()
    aoi_names = set()

    for _feature in geojson_data["features"]:
        geometry_types.add(_feature["geometry"]["type"])
        if "properties" in _feature and "aoi_id" in _feature["properties"]:
            aoi_names.add(_feature["properties"]["aoi_id"])

    print(f"Feature count: {_feature_count}")
    print(f"Geometry types: {geometry_types}")
    print(f"AOI IDs found: {aoi_names}")
    return


@app.cell
def _(geojson_data, pd):
    # Extract features as a table for inspection
    features_list = []
    for _feature in geojson_data["features"]:
        row = {
            "geometry_type": _feature["geometry"]["type"],
            **_feature.get("properties", {})
        }
        features_list.append(row)

    features_df = pd.DataFrame(features_list)
    features_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 1.2 GeoJSON Map Visualize Boundaries of each feature


    Working with the GeoJSON data:
    * List the features
    * in separate maps, show each feature.
    """)
    return


@app.cell
def _(geojson_data, pd):
    # List GeoJSON features by geo_level
    _rows = []
    for _f in geojson_data["features"]:
        _p = _f["properties"]
        _rows.append({
            "geo_id":    _p.get("geo_id", "?"),
            "geo_level": _p.get("geo_level", "?"),
            "geo_name":  _p.get("geo_name", "?"),
            "geometry":  _f["geometry"]["type"],
        })

    pd.DataFrame(_rows)
    return


@app.cell(hide_code=True)
def _(geojson_data, gpd):
    from shapely.geometry import shape

    # Convert GeoJSON features to GeoDataFrame
    features_geom = []
    for _feature in geojson_data["features"]:
        geom = shape(_feature["geometry"])
        props = _feature.get("properties", {})
        features_geom.append({
            "geometry": geom,
            **props
        })

    gdf = gpd.GeoDataFrame(features_geom, crs="EPSG:4326")

    # Calculate center point for map
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    print(f"GeoDataFrame created with {len(gdf)} features")
    print(f"Bounds: {bounds}")
    print(f"Center: ({center_lat}, {center_lon})")

    gdf
    return center_lat, center_lon, gdf


@app.cell
def _():
    from shapely.geometry import mapping

    return (mapping,)


@app.cell
def _(folium, gdf, mapping, mo):
    def _make_map(rows, zoom=11, color="steelblue"):
        """Render a list of GeoDataFrame rows on a single folium map."""
        _all_bounds = [r["geometry"].bounds for r in rows]
        _minx = min(b[0] for b in _all_bounds)
        _miny = min(b[1] for b in _all_bounds)
        _maxx = max(b[2] for b in _all_bounds)
        _maxy = max(b[3] for b in _all_bounds)
        _lat, _lon = (_miny + _maxy) / 2, (_minx + _maxx) / 2
        _m = folium.Map(location=[_lat, _lon], zoom_start=zoom,
                        tiles="CartoDB positron", width=500, height=400)
        for _r in rows:
            folium.GeoJson(
                {"type": "Feature",
                 "geometry": mapping(_r["geometry"]),
                 "properties": {"name": _r["geo_id"]}},
                style_function=lambda _x, c=color: {
                    "fillColor": c, "color": "#333",
                    "weight": 1.5, "fillOpacity": 0.35},
                tooltip=_r["geo_id"],
            ).add_to(_m)
        return _m

    _groups = {"city": [], "urban_extent": [], "aoi": [], "district": []}
    for _, _row in gdf.iterrows():
        _lvl = _row.get("geo_level", "?")
        if _lvl in _groups:
            _groups[_lvl].append(_row)

    _colors = {"city": "#e05c1a", "urban_extent": "#1a7be0",
               "aoi":  "#2ca02c", "district":     "#9467bd"}
    _zooms  = {"city": 10, "urban_extent": 10, "aoi": 13, "district": 10}
    _labels = {"city": "City", "urban_extent": "Urban Extent",
               "aoi":  "Accelerator Area", "district": "Districts (7)"}

    _maps = []
    for _lvl in ("city", "urban_extent", "aoi", "district"):
        _rows = _groups[_lvl]
        if _rows:
            _maps.append(mo.vstack([
                mo.md(f"**{_labels[_lvl]}** — {len(_rows)} feature(s)"),
                _make_map(_rows, zoom=_zooms[_lvl], color=_colors[_lvl]),
            ]))

    mo.vstack([
        mo.hstack([_maps[0], _maps[1], ]),
        mo.hstack([_maps[2], _maps[3], ]),
    ])
    return


@app.cell
def _():
    import re

    return (re,)


@app.cell
def _(geojson_data, mo, pd, re):
    # Indicators per geo_level
    # The GeoJSON carries two classes of indicators:
    #   - Observed/baseline: current or historical measurements (ImperviousArea, PM2.5, GhgEmissions, etc.)
    #   - Future projections: FutureAnnualMaxTemp, FutureHeatwaveFrequency, FutureExtremePrecipitationDays
    # UTCI scenario outputs are NOT here — they live in COG rasters.

    _GEO_KEYS = {
        "geo_id","geo_name","geo_level","geo_parent_name","geo_version","bbox",
        "aoi_id","city_id","city_name","id","Area","Nome",
        "city_id_large","city_ids","city_name_large","city_names",
        "country_ISO","country_name","reference_idstring","reference_year",
        "region1","region2","year",
    }

    def _parse_key(k):
        _parts = k.split("__")
        _stem  = _parts[0]
        _is_future = _stem.startswith("Future")
        _years = re.findall(r"\d{4}", k)
        return {
            "key":        k,
            "stem":       _stem,
            "category":   "future_projection" if _is_future else "baseline",
            "years":      _years,
        }

    _rows = []
    for _f in geojson_data["features"]:
        _p   = _f["properties"]
        _lvl = _p.get("geo_level", "?")
        _gid = _p.get("geo_id", "?")
        for _k, _v in _p.items():
            if _k in _GEO_KEYS:
                continue
            _parsed = _parse_key(_k)
            _value = _v.get("value") if isinstance(_v, dict) else _v
            _rows.append({
                "geo_level":  _lvl,
                "geo_id":     _gid,
                "category":   _parsed["category"],
                "stem":       _parsed["stem"],
                "indicator":  _k,
                "value":      _value,
            })

    indicators_df = pd.DataFrame(_rows)

    # Pivot — reindex columns to always show all four geo_levels
    _ALL_LEVELS = ["city", "district", "urban_extent", "aoi"]

    _pivot = (
        indicators_df[["geo_level","category","stem"]]
        .drop_duplicates()
        .assign(present=True)
        .pivot_table(index=["category","stem"], columns="geo_level",
                     values="present", aggfunc="any", fill_value=False)
        .reindex(columns=_ALL_LEVELS, fill_value=False)
        .reset_index()
    )

    _LEVEL_LABELS = {
        "city": "City", "district": "District",
        "urban_extent": "Urban Extent", "aoi": "Accelerator Area",
    }

    _display = _pivot.rename(columns=_LEVEL_LABELS).assign(**{
        _LEVEL_LABELS[col]: _pivot[col].map({True: "✓", False: ""})
        for col in _ALL_LEVELS
    })

    mo.vstack([
        mo.md("**Indicator stems by geo_level** — ✓ = present, blank = absent"),
        mo.ui.table(_display, selection=None),
    ])
    return (indicators_df,)


@app.cell
def _(indicators_df, mo):
    # Future projection indicators only
    # Each stem has multiple keys: one per scenario × time-horizon combination
    _ALL_LEVELS = ["city", "district", "urban_extent", "aoi"]
    _LEVEL_LABELS = {
        "city": "City", "district": "District",
        "urban_extent": "Urban Extent", "aoi": "Accelerator Area",
    }

    _future_df = indicators_df[indicators_df["category"] == "future_projection"]

    _pivot_future = (
        _future_df[["geo_level","stem","indicator"]]
        .drop_duplicates()
        .assign(present=True)
        .pivot_table(index="stem", columns="geo_level",
                     values="present", aggfunc="any", fill_value=False)
        .reindex(columns=_ALL_LEVELS, fill_value=False)
        .reset_index()
    )

    # Also count how many keys per stem (i.e. how many scenario/year variants)
    _key_counts = (
        _future_df[["stem","indicator"]]
        .drop_duplicates()
        .groupby("stem").size()
        .rename("n_variants")
        .reset_index()
    )

    _pivot_future = _pivot_future.merge(_key_counts, on="stem")

    _display_future = _pivot_future.rename(columns=_LEVEL_LABELS).assign(**{
        _LEVEL_LABELS[col]: _pivot_future[col].map({True: "✓", False: ""})
        for col in _ALL_LEVELS
    })

    # Show a sample of the actual key names to reveal the scenario/year structure
    _sample_keys = (
        _future_df[["stem","indicator"]]
        .drop_duplicates()
        .sort_values(["stem","indicator"])
    )

    mo.vstack([
        mo.md("**Future projection indicators** — ✓ = present, blank = absent"),
        mo.ui.table(_display_future, selection=None),
        mo.md("**Key name variants** (showing scenario × time-horizon structure)"),
        mo.ui.table(_sample_keys, selection=None),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 1.3 GeoJSON: Unorganized
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. PM Tiles

    PMTile data: `BRA-Campinas.pmtiles`. This is a single file archive containing all four vector layers (city, urban_extent, accelerator_area, district) tiled from z0–13.
    * Fetch and Load the PMTile
    * interactive map to inspect contents
    """)
    return


@app.cell(hide_code=True)
def _(requests):
    pmtiles_url = "https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/dev/boundaries/pmtiles/BRA-Campinas.pmtiles"

    pmtilesresponse = requests.get(pmtiles_url)
    pmtiles_bytes = pmtilesresponse.content

    print(f"PMTiles fetched successfully. Size: {len(pmtiles_bytes)} bytes")
    return pmtiles_bytes, pmtiles_url


@app.cell(hide_code=True)
def _(pmtiles_bytes):
    import struct

    # PMTiles header: first 16 bytes contain magic number and spec version
    # Bytes 0-7: "PMTiles" (magic header)
    magic = pmtiles_bytes[0:7]
    spec_version = pmtiles_bytes[7]

    print(f"Magic header: {magic}")
    print(f"PMTiles Spec Version: {spec_version}")
    print(f"Total file size: {len(pmtiles_bytes)} bytes")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 2.1 PM Tiles data

    The PMTiles gives us
    * Tiled delivery — geometry is pre-sliced into tiles and only fetched for the current viewport. For a large city with many districts this matters, but Campinas has 7 districts, so the full geometry is tiny. No real benefit here.
    * Server-side rendering — the browser fetches only what's visible at the current zoom.
    * The indicator fields — the PMTiles district layer has all 277 indicator fields embedded per tile, so a click/tooltip could read them directly from the tile without a separate data fetch.

    The data in PMTiles is the same as in the GeoJSON.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 3 Interactive Map (PMTiles + GeoJSON)

    Using python openlayer wrapper to render a map of the PMTiles
    * including geoJSON
    """)
    return


@app.cell
def _(geojson_url, ol):
    # This is test only, random geojson dataset 

    geojson_vector_layer = ol.VectorLayer(
            # background="gray",
            source=ol.VectorSource(url=geojson_url),
            fit_bounds=True
        )
    return (geojson_vector_layer,)


@app.cell
def _(center_lat, center_lon, ol, pmtiles_url):
    # Create PMTiles vector layer from the Campinas boundary file
    pmtiles_layer = ol.VectorTileLayer(
        id="campinas-boundaries",
        style=ol.FlatStyle(
            stroke_color="purple",
            stroke_width=2,
            fill_color="rgba(128, 0, 128, 0.2)"
        ),
        source=ol.PMTilesVectorSource(
            url=pmtiles_url,
            attributions=["Campinas Boundary Data - WRI Cities"]
        ),
    )

    # Set view centered on Campinas with appropriate zoom
    view = ol.View(center=(center_lon, center_lat), zoom=13)
    return pmtiles_layer, view


@app.cell
def _(
    Carto,
    CartoBasemapLayer,
    geojson_vector_layer,
    mo,
    ol,
    pmtiles_layer,
    view,
):
    # Create map widget with PMTiles layer
    ol_map = ol.MapWidget(
        view, 
        layers=[
            # base layer
            CartoBasemapLayer(Carto.VOYAGER), 

            # PM Tiles data
            pmtiles_layer,

            # GeoJSON data
            geojson_vector_layer,
        ]
    )

    # this is a very noisy tooltip - enable to view
    #ol_map.add_tooltip()


    ol_map.add_click_interaction()
    ol_map.add_select_interaction()

    widget = mo.ui.anywidget(ol_map)
    widget
    return (widget,)


@app.cell(hide_code=True)
def _(mapbox_vector_tile, mercantile, pmtiles_bytes, widget):
    """
    Click interface for PMTiles (custom)

    How it works:
    * It reads the click coordinate from widget.value["clicked"] (which add_click_interaction provides)
    * Converts that to a tile XYZ using mercantile and looks up the tile in pmtiles_bytes
    * Decodes the MVT tile with mapbox_vector_tile — getting the same data the tooltip renders
    * Prefers district layer → city → accelerator_area → urban_extent in that order
    * Displays geo fields separately from indicator fields

    """

    from pmtiles.reader import zxy_to_tileid, find_tile, deserialize_header, deserialize_directory, Compression
    import gzip

    def _get_tile_features(lon, lat, zoom=13):
        _tile = mercantile.tile(lon, lat, zoom)
        _header = deserialize_header(pmtiles_bytes[0:127])
        _root_dir = pmtiles_bytes[_header["root_offset"]: _header["root_offset"] + _header["root_length"]]
        _entries = deserialize_directory(_root_dir)
        _entry = find_tile(_entries, zxy_to_tileid(zoom, _tile.x, _tile.y))
        if not _entry:
            return {}
        _start = _header["tile_data_offset"] + _entry.offset
        _raw = pmtiles_bytes[_start: _start + _entry.length]
        if _header["tile_compression"] == Compression.GZIP:
            _raw = gzip.decompress(_raw)
        return mapbox_vector_tile.decode(_raw)

    def _format_props(props):
        _geo = {k: v for k, v in props.items() if k.startswith("geo_") or k == "bbox"}
        _indicators = {k: v for k, v in props.items() if k not in _geo and k not in ("geometry",)}
        _text = ""
        if _geo:
            _text += "**Geographic**\n\n"
            for k, v in sorted(_geo.items()):
                _text += f"- **{k}**: {v}\n"
        if _indicators:
            _text += "\n**Indicators**\n\n"
            for k, v in sorted(_indicators.items()):
                _text += f"- `{k}`: {v}\n"
        return _text

    _clicked = widget.value.get("clicked", {})
    _coord = _clicked.get("coordinate")

    if _coord:
        _lon, _lat = _coord[0], _coord[1]
        _zoom = min(max(round(_clicked.get("zoom", 13)), 0), 13)
        _layers = _get_tile_features(_lon, _lat, zoom=_zoom)

        _priority = ["district", "city", "accelerator_area", "urban_extent"]
        _chosen_layer = next((l for l in _priority if l in _layers and _layers[l]["features"]), None)
        if not _chosen_layer and _layers:
            _chosen_layer = next(iter(_layers))

        if _chosen_layer:
            _feats = _layers[_chosen_layer]["features"]
            _props = _feats[0]["properties"] if _feats else {}
            _geo_id = _props.get("geo_id", "unknown")
            print(f"### {_geo_id}\n\n{_format_props(_props)}")
        else:
            print("*No features found at clicked location*")
    else:
        print("*Click on a feature in the map to see its properties*")
    return


@app.cell
def _(widget):
    # Access the map view state from the wrapped widget
    view_state = widget.value["view_state"]
    view_state
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. COG Data

    COG (Cloud Optimized GeoTIFF) rasters are the third format in the CCL data pipeline — they carry
    the pixel-level UTCI (Universal Thermal Climate Index) outputs that do not appear in the GeoJSON or PMTiles.
    The scalar summaries in the GeoJSON reference baseline and future-projection statistics; the underlying
    spatial maps live here, one raster per city × AOI × layer × scenario.

    This section:
    - Discovers which COG layer IDs are available for Campinas via the `/layers` API
    - Retrieves display metadata (colormap, legend, source path hints) for each accessible layer
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.1 Discover available COG layers via the `/layers` API

    Searched the s3 bucket for campinas
    * 10 COG files found for BRA-Campinas in data/dev/utci/cog/
    * All are accelerator_area, surprising!
    * These must be related to 1 or more scenarios
    * I think we have 4 baseline layers and 6 scenario output scenarios
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **FLAG: API metadata vs. S3 doesn't line up**

    The `/layers/{layer_id}/{city_id}` endpoint is the intended catalogue for COG layers,
    but it is unreliable for Campinas scenario data:
    - **`utci_1500_baseline`** — fully registered: returns legend title, colormap, file type, and a valid COG URL.
    - **Scenario layer IDs** (e.g. `utci_1500_cool_roofs_achievable`) — return a record, but it is an empty stub
       - `file_type: null`, `map_styling: {}`, `legend_styling: {}`
       - malformed COG URL (`cog/BRA-Campinas__city__None__.None`). Unusable.

    The API metadata seems to be missing information. If so, we have to use the S3 bucket listing to discover and access scenario COGs.
    """)
    return


@app.cell
def _():
    import xml.etree.ElementTree as ET

    return (ET,)


@app.cell(hide_code=True)
def _(ET, mo, pd, requests):
    # Query the full utci/cog/ prefix to see all cities in the bucket


    _S3_BASE = "https://wri-cities-data-api.s3.us-east-1.amazonaws.com"
    _resp = requests.get(f"{_S3_BASE}/?prefix=data/dev/utci/cog/", timeout=10)
    _root = ET.fromstring(_resp.content)
    _ns   = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    _all_files = _root.findall("s3:Contents", _ns)

    _city_counts = {}
    for _item in _all_files:
        _fname = _item.find("s3:Key", _ns).text.split("/")[-1]
        _city  = _fname.split("__")[0] if "__" in _fname else ""
        _city_counts[_city] = _city_counts.get(_city, 0) + 1

    _city_counts.pop("", None)  # drop malformed entries

    _summary_df = pd.DataFrame(
        sorted(_city_counts.items(), key=lambda x: -x[1]),
        columns=["city_id", "cog_count"],
    )

    mo.vstack([
        mo.md(f"**{len(_all_files)} COG files** across **{len(_city_counts)} cities** in `data/dev/utci/cog/`"),
        mo.ui.table(_summary_df, selection=None),
    ])
    return


@app.cell
def _(ET, mo, pd, requests):
    # List all COG files for BRA-Campinas by querying the public S3 bucket directly.
    # The bucket supports unauthenticated ListObjects — no credentials needed.

    _S3_BASE = "https://wri-cities-data-api.s3.us-east-1.amazonaws.com"
    _PREFIX  = "data/dev/utci/cog/BRA-Campinas"

    _resp = requests.get(f"{_S3_BASE}/?prefix={_PREFIX}", timeout=10)
    _root = ET.fromstring(_resp.content)
    _ns   = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    # A file is a baseline if:
    #   - the layer_id is one of the known baseline stems (with or without hyphens), OR
    #   - "baseline" appears anywhere in the filename (catches version tokens like baseline__baseline)
    _BASELINE_LAYER_STEMS = {
        "utci_1500_baseline",
        "utci-1500",
        "utci-cat-1500",
        "utci-cat-1500-non-building-areas",
    }

    _rows = []
    for _item in _root.findall("s3:Contents", _ns):
        _key   = _item.find("s3:Key", _ns).text
        _size  = int(_item.find("s3:Size", _ns).text)
        _fname = _key.split("/")[-1].replace(".tif", "")
        _parts  = _fname.split("__")
        _layer  = _parts[2] if len(_parts) > 2 else "?"
        _version = "__".join(_parts[3:]) if len(_parts) > 3 else "?"
        _is_baseline_guess = (
            _layer in _BASELINE_LAYER_STEMS
            or "baseline" in _version
        )
        _rows.append({
            "layer_id": _layer,
            "layer_type_GUESS":     "baseline" if _is_baseline_guess else "scenario",
            "version":  _version,
            "size_mb":  round(_size / 1e6, 2),
            "url":      f"{_S3_BASE}/{_key}",
        })

    cog_inventory_df = pd.DataFrame(_rows)

    mo.vstack([
        mo.md(f"**{len(_rows)} COG files** for `BRA-Campinas` — all scoped to `accelerator_area`"),
        mo.ui.table(cog_inventory_df[["layer_id", "layer_type_GUESS", "version", "size_mb"]], selection=None),
    ])
    return (cog_inventory_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### FLAG: Possible Inconsistencies

    * The naming is inconsistent: some use underscores (utci_1500_baseline), others use hyphens (utci-cat-1500), and version tokens vary (2023, 2025, 2023-v2)
    * All 10 files are accelerator_area — no city or urban_extent COGs (the layers API returned city for utci_1500_baseline, which doesn't match)
    * Two files look like they may be duplicates of each other (same size: utci-1500__baseline__baseline__2023 and utci_1500_baseline__2023)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.2 COG naming convention

    All COG files follow the pattern:

    ```
    {city_id}__{aoi_id}__{layer_id}__{version}.tif
    ```

    From the Campinas inventory:

    - **`aoi_id`** — all 10 Campinas COGs are scoped to `accelerator_area`. No `city` or `urban_extent` rasters exist. (The `/layers` API metadata contains an incorrect `city` aoi_id in its URL.)
    - **`layer_id`** — encodes the UTCI time-of-day and scenario. All Campinas files use `1500` (3 p.m.). Layer IDs are not fully consistent: some use underscores (`utci_1500_baseline`), others hyphens (`utci-1500`, `utci-cat-1500`), suggesting files from different generation runs.
    - **`version`** — either a year (`2023`, `2025`) or a year with suffix (`2023-v2`). Not all files carry a version token.
    - **Baseline vs. scenario** — `utci_1500_baseline` is the only baseline raster. The remaining 9 files are scenario outputs: cool roofs and street trees interventions, including delta layers (`vs_baseline`) and area-restricted variants (`non_buildings`).
    - **Scale** — 290 COG files across 13 cities are publicly accessible in this bucket. Campinas (10) is on the smaller end.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.3. Fetch one of the COGs and take a look: Thermal Stress Baseline
    """)
    return


@app.cell
def _(mo, requests):
    # Fetch layer metadata from the API for the one confirmed COG layer for BRA-Campinas
    _r = requests.get(
        "https://cities-data-api.wri.org/layers/utci_1500_baseline/BRA-Campinas",
        timeout=10,
    )
    _d = _r.json()
    _styling  = _d.get("map_styling", {})
    _legend   = _d.get("legend_styling", {})
    _cog_url  = (_d.get("layers_url") or {}).get("cog", "—")

    mo.md(f"""
    | Field | Value |
    |---|---|
    | **layer_id** | `{_d["layer_id"]}` |
    | **file_type** | `{_d["file_type"]}` |
    | **legend title** | {_legend.get("title")} |
    | **colormap** | `{_styling.get("colormap_name")}` ({_styling.get("steps")} steps, reversed) |
    | **COG URL** | `{_cog_url}` |
    """)
    return


@app.cell
def _():
    import rasterio

    return (rasterio,)


@app.cell
def _(mo, rasterio):
    # Fetch layer metadata from the COG file 

    # Use the URL confirmed via S3 inventory (accelerator_area, not city — the /layers API has a wrong aoi_id)
    _cog_url = "https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/dev/utci/cog/BRA-Campinas__accelerator_area__utci_1500_baseline__2023.tif"

    with rasterio.open(f"/vsicurl/{_cog_url}") as _src:
        _t = _src.transform
        cog_meta = {
            "url":       _cog_url,
            "width_px":  _src.width,
            "height_px": _src.height,
            "crs":       str(_src.crs),
            "dtype":     _src.dtypes[0],
            "bands":     _src.count,
            "res_x":     round(_t.a, 6),
            "res_y":     round(abs(_t.e), 6),
            "bounds":    _src.bounds,
            "overviews": _src.overviews(1),
            "nodata":    _src.nodata,
        }

    mo.md(f"""
    | Field | Value |
    |---|---|
    | **URL** | `{cog_meta["url"]}` |
    | **Dimensions** | {cog_meta["width_px"]} × {cog_meta["height_px"]} px |
    | **CRS** | `{cog_meta["crs"]}` |
    | **Pixel size** | {cog_meta["res_x"]} × {cog_meta["res_y"]} (map units) |
    | **Bounds** | `{cog_meta["bounds"]}` |
    | **Dtype / bands** | `{cog_meta["dtype"]}` / {cog_meta["bands"]} |
    | **Overviews** | {cog_meta["overviews"]} |
    | **Nodata** | `{cog_meta["nodata"]}` |
    """)
    return (cog_meta,)


@app.cell
def _():
    from PIL import Image
    import io


    return Image, io


@app.cell
def _(Image, cog_meta, io, mo, np, rasterio):

    # Read the lowest overview (level 4) — only fetches overview tiles, not the full raster
    with rasterio.open(f"/vsicurl/{cog_meta['url']}") as _src:
        _ovr = 4
        _data = _src.read(
            1,
            out_shape=(
                _src.count,
                int(_src.height // _ovr),
                int(_src.width  // _ovr),
            ),
            resampling=rasterio.enums.Resampling.nearest,
        )

    # Mask nodata
    _valid = _data != cog_meta["nodata"]
    _arr   = np.where(_valid, _data, np.nan)

    # Normalize to 0-255 over valid pixels only, fill nodata with 0 before cast
    _lo, _hi = float(np.nanmin(_arr)), float(np.nanmax(_arr))
    _normed  = (_arr - _lo) / (_hi - _lo) * 255
    _normed  = np.where(_valid, _normed, 0)
    _norm    = np.uint8(np.clip(_normed, 0, 255))

    # yiorrd reversed palette: low stress = yellow, high stress = dark red
    _palette_rgb = []
    for _i in range(256):
        _t = _i / 255.0
        if _t < 0.33:
            _s = _t / 0.33
            _r, _g, _b = 255, int(255 - _s * 114), 0
        elif _t < 0.66:
            _s = (_t - 0.33) / 0.33
            _r, _g, _b = 253, int(141 - _s * 141), int(60 - _s * 22)
        else:
            _s = (_t - 0.66) / 0.34
            _r, _g, _b = int(253 - _s * 125), 0, 38
        _palette_rgb += [_r, _g, _b]

    _img_p = Image.fromarray(_norm, mode="P")
    _img_p.putpalette(_palette_rgb)
    _img_rgba = _img_p.convert("RGBA")

    # Make nodata pixels transparent
    _pixels = np.array(_img_rgba)
    _pixels[~_valid] = [0, 0, 0, 0]
    _img_out = Image.fromarray(_pixels, mode="RGBA")

    _buf = io.BytesIO()
    _img_out.save(_buf, format="PNG")
    _buf.seek(0)

    mo.vstack([
        mo.md(f"**UTCI 1500 baseline - accelerator_area** | overview x{_ovr} ({_data.shape[1]}x{_data.shape[0]} px) | range: {_lo:.1f}-{_hi:.1f} deg C UTCI"),
        mo.image(_buf.read(), width=600),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.4. Fetch one of the COGS and take a look : Cool Roofs achievable
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **FLAG**: API endpoint for this layer is missing information
    """)
    return


@app.cell
def _(mo, requests):
    # Fetch layer metadata 
    _r = requests.get(
        "https://cities-data-api.wri.org/layers/utci_1500_cool_roofs_achievable/BRA-Campinas",
        timeout=10,
    )
    _d = _r.json()
    _styling  = _d.get("map_styling", {})
    _legend   = _d.get("legend_styling", {})
    _cog_url  = (_d.get("layers_url") or {}).get("cog", "—")

    mo.md(f"""
    | Field | Value |
    |---|---|
    | **layer_id** | `{_d["layer_id"]}` |
    | **file_type** | `{_d["file_type"]}` |
    | **legend title** | {_legend.get("title")} |
    | **colormap** | `{_styling.get("colormap_name")}` ({_styling.get("steps")} steps, reversed) |
    | **COG URL** | `{_cog_url}` |
    """)
    return


@app.cell(hide_code=True)
def _(cog_inventory_df, mo, rasterio):
    # Inspect metadata for a scenario COG — cool roofs achievable
    _scenario_url = cog_inventory_df.loc[
        cog_inventory_df["layer_id"] == "utci_1500_cool_roofs_achievable", "url"
    ].iloc[0]

    with rasterio.open(f"/vsicurl/{_scenario_url}") as _src:
        _t = _src.transform
        scenario_cog_meta = {
            "url":       _scenario_url,
            "width_px":  _src.width,
            "height_px": _src.height,
            "crs":       str(_src.crs),
            "dtype":     _src.dtypes[0],
            "bands":     _src.count,
            "res_x":     round(_t.a, 6),
            "res_y":     round(abs(_t.e), 6),
            "bounds":    _src.bounds,
            "overviews": _src.overviews(1),
            "nodata":    _src.nodata,
        }

    mo.md(f"""
    | Field | Value |
    |---|---|
    | **URL** | `{scenario_cog_meta["url"]}` |
    | **Dimensions** | {scenario_cog_meta["width_px"]} x {scenario_cog_meta["height_px"]} px |
    | **CRS** | `{scenario_cog_meta["crs"]}` |
    | **Pixel size** | {scenario_cog_meta["res_x"]} x {scenario_cog_meta["res_y"]} (map units) |
    | **Bounds** | `{scenario_cog_meta["bounds"]}` |
    | **Dtype / bands** | `{scenario_cog_meta["dtype"]}` / {scenario_cog_meta["bands"]} |
    | **Overviews** | {scenario_cog_meta["overviews"]} |
    | **Nodata** | `{scenario_cog_meta["nodata"]}` |
    """)
    return (scenario_cog_meta,)


@app.cell(hide_code=True)
def _(Image, io, mo, np, rasterio, scenario_cog_meta):
    with rasterio.open(f"/vsicurl/{scenario_cog_meta['url']}") as _src:
        _ovr = 4
        _data = _src.read(
            1,
            out_shape=(
                _src.count,
                int(_src.height // _ovr),
                int(_src.width  // _ovr),
            ),
            resampling=rasterio.enums.Resampling.nearest,
        )

    _valid = _data != scenario_cog_meta["nodata"]
    _arr   = np.where(_valid, _data, np.nan)

    _lo, _hi = float(np.nanmin(_arr)), float(np.nanmax(_arr))
    _normed  = (_arr - _lo) / (_hi - _lo) * 255
    _normed  = np.where(_valid, _normed, 0)
    _norm    = np.uint8(np.clip(_normed, 0, 255))

    _palette_rgb = []
    for _i in range(256):
        _t = _i / 255.0
        if _t < 0.33:
            _s = _t / 0.33
            _r, _g, _b = 255, int(255 - _s * 114), 0
        elif _t < 0.66:
            _s = (_t - 0.33) / 0.33
            _r, _g, _b = 253, int(141 - _s * 141), int(60 - _s * 22)
        else:
            _s = (_t - 0.66) / 0.34
            _r, _g, _b = int(253 - _s * 125), 0, 38
        _palette_rgb += [_r, _g, _b]

    _img_p = Image.fromarray(_norm, mode="P")
    _img_p.putpalette(_palette_rgb)
    _img_rgba = _img_p.convert("RGBA")

    _pixels = np.array(_img_rgba)
    _pixels[~_valid] = [0, 0, 0, 0]
    _img_out = Image.fromarray(_pixels, mode="RGBA")

    _buf = io.BytesIO()
    _img_out.save(_buf, format="PNG")
    _buf.seek(0)

    mo.vstack([
        mo.md(f"**UTCI 1500 cool roofs achievable (scenario) — accelerator_area** | overview x{_ovr} ({_data.shape[1]}x{_data.shape[0]} px) | range: {_lo:.1f}–{_hi:.1f} deg C UTCI"),
        mo.image(_buf.read(), width=600),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## BONUS. Validation Against API Bounding Boxes

    From the cities API response, we expect:
    - **accelerator_area**: [-47.20522, -22.97095, -47.18831, -22.95275]
    - **urban_extent**: [-47.43644, -23.11143, -46.93697, -22.68857]

    Let's compare these with our GeoJSON boundaries.
    """)
    return


@app.cell(hide_code=True)
def _(gdf, pd):
    # Display summary information
    summary_data = []
    for _, summary_row in gdf.iterrows():
        geom_bounds = summary_row["geometry"].bounds  # (minx, miny, maxx, maxy)
        area_km2 = summary_row["geometry"].area * 111 * 111  # rough approximation

        summary_data.append({
            "AOI ID": summary_row.get("aoi_id", "Unknown"),
            "Geometry Type": summary_row["geometry"].geom_type,
            "Area (approx km²)": f"{area_km2:.2f}",
            "Bounds": f"[{geom_bounds[0]:.5f}, {geom_bounds[1]:.5f}, {geom_bounds[2]:.5f}, {geom_bounds[3]:.5f}]"
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df
    return


@app.cell(hide_code=True)
def _(gdf, pd):
    # API bounding box data from cities endpoint
    _api_bounds_dict = {
        "accelerator_area": [-47.20522, -22.97095, -47.18831, -22.95275],
        "urban_extent": [-47.43644, -23.11143, -46.93697, -22.68857]
    }

    # Compare with extracted bounds
    _validation_list = []
    for _, _item in gdf.iterrows():
        _item_aoi = _item.get("aoi_id", "Unknown")
        _item_bounds = _item["geometry"].bounds
        _item_bbox_list = [_item_bounds[0], _item_bounds[1], _item_bounds[2], _item_bounds[3]]

        _item_api = _api_bounds_dict.get(_item_aoi, None)

        if _item_api:
            _validation_list.append({
                "AOI ID": _item_aoi,
                "GeoJSON bounds": str([f"{x:.5f}" for x in _item_bbox_list]),
                "API bounds": str([f"{x:.5f}" for x in _item_api]),
                "Match": "✓" if abs(_item_bounds[0] - _item_api[0]) < 0.001 else "Different bounds"
            })
        else:
            _validation_list.append({
                "AOI ID": _item_aoi,
                "GeoJSON bounds": str([f"{x:.5f}" for x in _item_bbox_list]),
                "API bounds": "Not found",
                "Match": "?"
            })

    validation_df = pd.DataFrame(_validation_list)
    validation_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 4. Summary of Findings

    ### Public access
    All three data formats — GeoJSON, PMTiles, and COG rasters — are publicly accessible on S3
    without credentials. The S3 bucket also supports unauthenticated `ListObjects`, making it
    possible to enumerate available files directly.

    ### GeoJSON and PMTiles
    Both boundary files contain the same spatial data: geometries for all four geo_levels
    (city, urban_extent, accelerator_area, 7 districts), plus scalar indicators attached as
    feature properties. Baseline indicators and future projections are present; UTCI scenario
    outputs are not — those live in COG rasters. The GeoJSON bounds for `accelerator_area`
    and `urban_extent` match the bounding boxes returned by the cities API.

    ### COG rasters
    - 290 COG files are available across 13 cities in the same bucket.

    For Campinas specifically:
    - **10 COG files** exist for Campinas in `s3://wri-cities-data-api/data/dev/utci/cog/`,
      all scoped to `accelerator_area`. No `city` or `urban_extent` rasters exist.
    - Based on a guess, we think there are **4 baselines** (Thermal heat stress UTCI at 15:00, with naming variants from different generation runs)
      and **6 scenario outputs** (cool roofs and street trees interventions, including delta
      and non-building-area variants).
    - All files are float32, single band, EPSG:4326, ~9×10⁻⁶ degree pixel size (~1 m).
    - COGs are properly structured with overview levels (2–3 levels), enabling efficient
      range-request access without downloading the full raster.

    ### API metadata reliability
    The `/layers` API is only partially useful for COG discovery:
    - `utci_1500_baseline` returns complete metadata (legend title, colormap, valid COG URL).
    - Scenario layer IDs return empty stub records with a malformed COG URL
      (`BRA-Campinas__city__None__.None`) — unusable.
    - The API's COG URL for the baseline layer references `aoi_id=city`, which does not exist
      on S3. The correct `aoi_id` is `accelerator_area`. S3 is the ground truth.

    ### FLAGS

    Naming inconsistency
    * COG filenames are not fully consistent — some use underscores (`utci_1500_baseline`),
    others hyphens (`utci-1500`, `utci-cat-1500`), suggesting files from different generation
    runs. Version tokens vary (`2023`, `2025`, `2023-v2`).
    * See other **FLAGS** in this notebook
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
 
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
