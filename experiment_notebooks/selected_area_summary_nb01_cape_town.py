# /// script
# dependencies = [
#     "folium==0.20.0",
#     "geopandas==1.1.4",
#     "litellm==1.93.0",
#     "marimo",
#     "numpy==2.5.1",
#     "pandas==3.0.3",
#     "plotly==6.9.0",
#     "rasterio==1.5.0",
#     "rasterstats==0.21.0",
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
    # Selected Area Summary for Cape Town


    Goals
    * Using various available indicators, generate a statistical comparison between a selected neighborhood and the city as a whole.
    * Summarize the statistical comparison
    * Generate an natural language summary
    * Use an LLM model query via API to generate a simple "insight" commensurate with the "selected Area summary" AI feature concept by Usertopia, to fit within the wireframe
    """)
    return


@app.cell
def _():
    import marimo as mo
    import geopandas as gpd
    from pathlib import Path
    import json
    import re

    import requests
    import pandas as pd
    import numpy as np
    import folium
    from shapely.geometry import mapping, box
    import rasterio
    import rasterio.mask
    from rasterstats import zonal_stats


    return (
        Path,
        box,
        folium,
        gpd,
        mapping,
        mo,
        np,
        pd,
        rasterio,
        re,
        requests,
        zonal_stats,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Indicators
    """)
    return


@app.cell(hide_code=True)
def _(mo, pd, re, requests):
    CITY_ID = "ZAF-Cape_Town"
    BASE_URL = "https://cities-data-api.wri.org"
    S3_BASE = "https://wri-cities-data-api.s3.us-east-1.amazonaws.com"
    # NOTE: this is the UTCI-specific COG prefix, not the full data catalog — the
    # `wri-cities-data-api` bucket has 116+ top-level layer families (land surface
    # temperature, tree canopy, population, opportunity indices, etc.), most of
    # which also have real Cape Town data. See
    # experiment_notebooks/wri_ccl_data_layers_findings.md for the full picture;
    # `cog_df` below only covers the utci/ family.
    UTCI_COG_PREFIX = "data/dev/utci/cog/ZAF-Cape"

    # --- Scalar indicators from the API ---
    _resp = requests.get(f"{BASE_URL}/cities?application_id=ccl", timeout=15)
    _all_cities = _resp.json()["cities"]
    cape_town = next(c for c in _all_cities if c.get("id") == CITY_ID)

    indicator_values = cape_town.get("indicator_values", {})
    aoi_types = list(indicator_values.keys())

    _flat_keys = []
    for _aoi, _vals in indicator_values.items():
        for _k in _vals.keys():
            _flat_keys.append(_k)

    def _extract_stem(indicator_key):
        parts = re.split(r"__ZAF-", indicator_key)
        return parts[0]

    indicator_stems = sorted(set(_extract_stem(k) for k in _flat_keys))

    # --- UTCI COG inventory from S3 ---
    import xml.etree.ElementTree as ET

    _s3_resp = requests.get(f"{S3_BASE}/?prefix={UTCI_COG_PREFIX}", timeout=15)
    _s3_root = ET.fromstring(_s3_resp.content)
    _ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    _cog_rows = []
    for _item in _s3_root.findall("s3:Contents", _ns):
        _key = _item.find("s3:Key", _ns).text
        _size_bytes = int(_item.find("s3:Size", _ns).text)
        _fname = _key.split("/")[-1].replace(".tif", "")
        _parts = _fname.split("__")
        _aoi = _parts[1] if len(_parts) > 1 else "?"
        _layer_id = _parts[2] if len(_parts) > 2 else "?"
        _cog_rows.append({
            "aoi": _aoi,
            "layer_id": _layer_id,
            "s3_key": _key,
            "size_mb": round(_size_bytes / 1_048_576, 1),
        })

    cog_df = pd.DataFrame(_cog_rows)

    mo.vstack([
        mo.md(f"""
        ### Cape Town UTCI data inventory

        **Scoped to the `utci/` layer family only** — this is one of 116+ top-level
        layer families in the data bucket, not the full catalog. Real data also
        exists for land surface temperature, tree canopy cover, and population for
        Cape Town; see `experiment_notebooks/wri_ccl_data_layers_findings.md` for
        the full inventory and how to discover other layers.

        - **{len(_flat_keys)} scalar indicator values** across AOI types: `{"`, `".join(aoi_types)}`
        - **{len(indicator_stems)} unique scalar metric stems**
        - **{len(cog_df)} UTCI COG raster files** under `{UTCI_COG_PREFIX}`
        """),
        mo.md("**Scalar indicator stems:**"),
        mo.ui.table(pd.DataFrame({"stem": indicator_stems}), selection=None, page_size=15),
        mo.md("**UTCI COG inventory:**"),
        mo.ui.table(cog_df, selection=None, page_size=15),
    ])

    return BASE_URL, CITY_ID, S3_BASE, cog_df, indicator_values


@app.cell(hide_code=True)
def _(BASE_URL, CITY_ID, gpd, mo, requests):
    # Precise AOI polygons (not just bounding boxes) — needed to visually
    # overlay a selected neighborhood against actual data coverage.
    _city_detail_resp = requests.get(f"{BASE_URL}/cities/{CITY_ID}?application_id=ccl", timeout=15)
    city_detail = _city_detail_resp.json()

    _geojson_url = city_detail["layers_url"]["geojson"]
    _aoi_geojson = requests.get(_geojson_url, timeout=15).json()

    _aoi_gdf = gpd.GeoDataFrame.from_features(_aoi_geojson["features"], crs="EPSG:4326")

    # Identify each AOI by its distinguishing property (no shared `aoi_id` key
    # across features — business_district shows up as the suburb name that
    # happens to match it; urban_extent is tagged via geo_level).
    business_district_geom = _aoi_gdf[_aoi_gdf["OFC_SBRB_N"] == "CAPE TOWN CITY CENTRE"].iloc[0].geometry
    urban_extent_geom = _aoi_gdf[_aoi_gdf["geo_level"] == "urban_extent"].iloc[0].geometry

    aoi_geoms = {
        "business_district": business_district_geom,
        "urban_extent": urban_extent_geom,
    }

    mo.md(f"""
    **AOI polygons loaded** (precise boundaries, not bounding boxes):
    - `business_district` — matches suburb "CAPE TOWN CITY CENTRE", area ≈ {business_district_geom.area:.6f} deg²
    - `urban_extent` — full city extent, area ≈ {urban_extent_geom.area:.4f} deg²
    """)
    return (aoi_geoms,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Key finding:** only one COG covers the full city (`urban_extent`) —
    `utci_1500_baseline`. All other layers (1200, 1800, scenarios) only exist
    for `business_district`, which covers just ~34% of Ward 115.

    **Containment constraint:** for a `business_district`-scoped indicator to
    be a fair "whole neighborhood" summary, the selected neighborhood must be
    **entirely (or near-entirely) contained within `business_district`** — not
    just intersecting it. `rasterio.mask` will happily clip to whatever
    overlaps and return stats without error, but those stats would only
    describe the overlapping portion, silently mislabeled as "the
    neighborhood."

    This is a real constraint, not an edge case: `business_district`'s bbox is
    only ~2.2km × 2.4km (~5 km²) — smaller than Ward 115 alone (12.34 km²).
    **No ward can be fully contained in it.** Wards are too coarse for any
    indicator restricted to `business_district`; only a finer polygon (e.g. a
    suburb, or a hand-drawn AOI) could satisfy full containment.
    """)
    return


@app.cell(hide_code=True)
def _(cog_df, mo):
    _TIME_TOKENS = {"1200", "1500", "1800"}
    _MASK_TOKENS = {
        "pedestrian_areas": "pedestrian",
        "non_buildings": "non-buildings",
        "parks_areas": "parks",
        "shade_structure_areas": "shade structures",
        "urban_extent": "urban extent",
    }
    _INTERVENTION_MAP = {
        "baseline": "Baseline",
        "cool_roofs_achievable": "Cool roofs",
        "cool_roofs": "Cool roofs",
        "street_trees_achievable": "Street trees",
        "street_trees_cool_roofs_achievable": "Street trees + cool roofs",
        "street_trees_cool_roofs": "Street trees + cool roofs",
        "park_shade_achievable": "Park shade",
    }
    _AOI_LABELS = {"urban_extent": "Whole city", "business_district": "CBD"}

    def _parse_classic_layer_id(layer_id):
        lid = layer_id
        time_of_day = next((t for t in _TIME_TOKENS if t in lid), "unknown")

        spatial_mask = "full AOI"
        for token, label in _MASK_TOKENS.items():
            if lid.endswith(token):
                spatial_mask = label
                break

        is_delta = "vs_baseline" in lid

        part = lid.replace("utci_", "")
        for t in _TIME_TOKENS:
            part = part.replace(f"{t}_", "")
        for token in _MASK_TOKENS:
            part = part.replace(f"_{token}", "")
        part = part.replace("_vs_baseline", "")
        part = part.strip("_")

        intervention = _INTERVENTION_MAP.get(part, part)
        output_type = "delta vs baseline" if is_delta else ("baseline" if part == "baseline" else "scenario")
        return time_of_day, intervention, output_type, spatial_mask

    # Only classic-named, non-categorical, non-test COGs are exposed here.
    # Excludes: newer dash-named combo files (utci-1500__...), categorical
    # rasters (utci-cat-*), and one _test artifact — 6 of 63 files total.
    _classic_cogs = cog_df[
        cog_df["layer_id"].str.startswith("utci_")
        & ~cog_df["layer_id"].str.contains("_test")
    ].copy()

    _indicator_options = {}
    for _, _row in _classic_cogs.iterrows():
        _t, _interv, _otype, _mask = _parse_classic_layer_id(_row["layer_id"])
        _label_bits = [f"[{_AOI_LABELS[_row['aoi']]}] UTCI {_t} — {_interv}"]
        if _otype == "delta vs baseline":
            _label_bits.append("(delta)")
        if _mask != "full AOI":
            _label_bits.append(f"[{_mask}]")
        _label = " ".join(_label_bits)
        _indicator_options[_label] = (_row["aoi"], _row["layer_id"])

    indicator_dropdown = mo.ui.dropdown(
        options=_indicator_options,
        value="[CBD] UTCI 1500 — Baseline",
        label="Select an indicator",
    )

    mo.vstack([
        mo.md(f"**{len(_indicator_options)} indicators available** (classic-naming COGs only; 6 of 63 excluded — see note above cell)."),
        indicator_dropdown,
    ])

    return (indicator_dropdown,)


@app.cell
def _(indicator_dropdown):
    print(f"""Selected indicator: {indicator_dropdown.value[1]}\nFor extent: {indicator_dropdown.value[0]}""")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Beyond UTCI: other indicators needed for the wireframe

    The "selected area summary" wireframe concept needs four indicators: thermal
    stress (UTCI, above), land surface temperature, tree canopy cover, and
    vulnerable population. The `utci/` family above is not the whole data
    catalog — see `experiment_notebooks/wri_ccl_data_layers_findings.md` for how
    we found real Cape Town data for the other three outside the narrow prefix
    this notebook originally queried.

    This is deliberately **not** a full registry (that's what exploratory nb2 is
    for) — just pinning down the exact single COG we'll use for each, scoped for
    consistency with the `business_district`-based zone comparisons used
    throughout this notebook:

    - **Land surface temperature** and **tree canopy cover** both have real
      `business_district`-scoped files — same pattern as UTCI: one file, clipped
      to the zone vs. clipped to the whole `business_district` polygon.
    - **Vulnerable population** (elderly, as a % of general population) only
      exists at `urban_extent` scope for Cape Town — no separate
      `business_district` file. Since `urban_extent` covers the whole city (a
      superset of `business_district`), we get a `business_district`-level value
      by zonal-stating the same `urban_extent` raster against the
      `business_district` polygon directly, rather than needing a
      pre-cropped file.
    - Population rasters store **counts per pixel**, not a rate — so "% elderly"
      needs `sum(elderly) / sum(general population)` over an area, not an
      average of per-pixel means. Needs a `sum`-based zonal stat, not the
      mean/p90/max used for UTCI.
    """)
    return


@app.cell(hide_code=True)
def _(mo, pd):
    # One COG each for the 3 new indicators — not a full registry (see
    # wri_ccl_data_layers_findings.md for the full catalog). All confirmed to
    # exist for ZAF-Cape_Town via direct S3 listing.
    LST_COG_KEY = "data/dev/LandSurfaceTemperature/cog/ZAF-Cape_Town__business_district__LandSurfaceTemperature__StartYear_2013_EndYear_2022.tif"
    TREE_COVER_COG_KEY = "data/dev/tree_cover/cog/ZAF-Cape_Town__business_district__tree_cover_baseline__2024.tif"
    WORLDPOP_GENERAL_COG_KEY = "data/dev/WorldPop/cog/ZAF-Cape_Town__urban_extent__WorldPop__StartYear_2020_EndYear_2020.tif"
    WORLDPOP_ELDERLY_COG_KEY = "data/dev/WorldPop__AgesexClasses_ELDERLY/cog/ZAF-Cape_Town__urban_extent__WorldPop__AgesexClasses_ELDERLY__StartYear_2020_EndYear_2020.tif"

    mo.ui.table(
        pd.DataFrame([
            {"indicator": "Land surface temperature", "aoi_scope": "business_district", "s3_key": LST_COG_KEY},
            {"indicator": "Tree canopy cover", "aoi_scope": "business_district", "s3_key": TREE_COVER_COG_KEY},
            {"indicator": "Population (general)", "aoi_scope": "urban_extent (clipped as needed)", "s3_key": WORLDPOP_GENERAL_COG_KEY},
            {"indicator": "Population (elderly)", "aoi_scope": "urban_extent (clipped as needed)", "s3_key": WORLDPOP_ELDERLY_COG_KEY},
        ]),
        selection=None,
    )

    return (
        LST_COG_KEY,
        TREE_COVER_COG_KEY,
        WORLDPOP_ELDERLY_COG_KEY,
        WORLDPOP_GENERAL_COG_KEY,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Available "neighborhoods" from public data and OSM

    Explored the following options for a `business_district`-scoped
    neighborhood (needed for scenario-delta indicators — see coverage
    constraint above):

    * **Wards** (116 total, City of Cape Town): too large — only 13/116 are
      even smaller in area than `business_district` (2.23 km²), and none are
      positioned inside it. Ward 115 (used above) only covers ~80% overlap,
      not full containment.
    * **Official Planning Suburbs** (776 total, Western Cape GIS): the right
      *size* — median suburb is 0.67 km², and 653/776 are smaller than
      `business_district`. But `business_district` **is** the "CAPE TOWN CITY
      CENTRE" suburb polygon itself (99.99996% area match). Checking overlap
      of all 776 suburbs found only 5 others touching it at all (Gardens,
      Foreshore, Bo-Kaap, Green Point, Zonnebloem), each with a
      **fraction-of-a-percent** overlap — i.e. a shared boundary edge, not
      real containment. No suburb usefully subdivides the CBD.
    * **Special Rating Areas / City Improvement Districts** (Western Cape
      GIS, layer 21): partial coverage only. CCID covers 67% of
      `business_district`, Green Point SRA covers another 11% (sliver) — 22%
      of the CBD isn't covered by any SRA. Not a clean subdivision, and only
      2 zones even where it does apply.
    * **Planning/building development districts & service delivery areas**
      (Western Cape GIS, layers 17/18): far too coarse — single polygons
      covering the whole region (112–1,318 km²), not usable at neighborhood
      scale.
    * **Census tracts (Stats SA Small Area Layer)**: not available through
      the City of Cape Town open data portal (checked all 255 datasets —
      none are census/small-area/sub-place layers). Would require sourcing
      directly from Stats SA outside this portal; not attempted here.
    * **OpenStreetMap neighbourhood/suburb polygons**: queried via Overpass
      API for `place=suburb|neighbourhood` within the CBD bounding box.
      OSM's own "City Centre" polygon is, again, essentially
      `business_district` (96.7% coverage, 99.7% contained). The one genuine
      exception is **De Waterkant** — a real, locally-recognized precinct,
      99.98% contained within `business_district`, covering ~12% of it. All
      other named OSM suburbs (Foreshore, Green Point, Gardens, Bo-Kaap,
      District Six, Woodstock, Oranjezicht, Vredehoek, Tamboerskloof, Mouille
      Point, Three Anchor Bay, Walmer Estate, Devil's Peak Estate) either
      barely clip the boundary (<2%) or fall entirely outside it.

    **None of these work as a source of multiple neighborhoods for the
    currently available `business_district` COG files.** The real-world
    administrative and community-recognized geography of the CBD is
    essentially "one area" with a single genuine exception (De Waterkant,
    ~12%) — not 5-6 distinct sub-neighborhoods. This is a property of the
    place (a compact ~2.2 km² city centre), not a gap in our search.

    **Implication:** to get more than one or two `business_district`-scoped
    "neighborhood" summaries, we'll need to hand-draw sub-area polygons
    (as anticipated by the nb01 planning doc's fallback option) rather than
    rely on an existing named-neighborhood dataset. Any hand-drawn zones
    should be labeled as such (e.g. "Zone A/B/C" or informally-named
    sub-areas) rather than presented as official neighborhoods.
    """)

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Aside: Wards exploration
    """)
    return


@app.cell
def _(Path, folium, gpd, mapping, mo):
    WARDS_PATH = Path(__file__).parent / "data" / "cape_town" / "Wards.geojson"
    SELECTED_WARD_NAME = "115"

    _wards_raw = gpd.read_file(WARDS_PATH)
    _latest_year = _wards_raw["WARD_YEAR"].max()
    wards = _wards_raw[_wards_raw["WARD_YEAR"] == _latest_year].reset_index(drop=True)

    selected_ward = wards[wards["WARD_NAME"] == SELECTED_WARD_NAME].reset_index(drop=True)
    assert len(selected_ward) == 1, f"expected exactly 1 match for ward {SELECTED_WARD_NAME}, got {len(selected_ward)}"

    _geom = selected_ward.iloc[0]["geometry"]
    _minx, _miny, _maxx, _maxy = _geom.bounds
    _center_lat, _center_lon = (_miny + _maxy) / 2, (_minx + _maxx) / 2

    # Rough area in sq km (WGS84 degrees -> approx metric via equal-area reprojection)
    _area_sqkm = selected_ward.to_crs("EPSG:32734").geometry.area.iloc[0] / 1e6

    ward_map = folium.Map(
        location=[_center_lat, _center_lon],
        zoom_start=13,
        tiles="CartoDB positron",
        width=600,
        height=500,
    )
    folium.GeoJson(
        {"type": "Feature", "geometry": mapping(_geom), "properties": {"name": f"Ward {SELECTED_WARD_NAME}"}},
        style_function=lambda _x: {
            "fillColor": "#2ca02c", "color": "#333",
            "weight": 2, "fillOpacity": 0.35},
        tooltip=f"Ward {SELECTED_WARD_NAME}",
    ).add_to(ward_map)

    mo.vstack([
        mo.md(f"""
        ### Selected neighborhood: Ward {SELECTED_WARD_NAME}

        - **Ward year:** {_latest_year}
        - **Area:** {_area_sqkm:.2f} sq km
        - **Bounds (WGS84):** ({_minx:.4f}, {_miny:.4f}, {_maxx:.4f}, {_maxy:.4f})
        - Covers ~80% of the `business_district` AOI extent (partial overlap — baseline UTCI
          available city-wide via `urban_extent`, scenario deltas only valid within the AOI portion)
        """),
        ward_map,
    ])
    return SELECTED_WARD_NAME, selected_ward


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Computing Zonal Stats for a Ward
    """)
    return


@app.cell
def _(
    S3_BASE,
    SELECTED_WARD_NAME,
    cog_df,
    mo,
    pd,
    rasterio,
    selected_ward,
    zonal_stats,
):
    GDAL_ENV = dict(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        VSI_CACHE="TRUE",
        GDAL_HTTP_MULTIPLEX="YES",
    )

    def cog_url_for(aoi: str, layer_id: str) -> str:
        _row = cog_df[(cog_df["aoi"] == aoi) & (cog_df["layer_id"] == layer_id)].iloc[0]
        return f"{S3_BASE}/{_row['s3_key']}"

    def zonal_stats_for_geom(geom, aoi: str, layer_id: str) -> dict:
        """Zonal stats for a single geometry against a named COG layer, via /vsicurl/."""
        _url = cog_url_for(aoi, layer_id)
        with rasterio.Env(**GDAL_ENV):
            _result = zonal_stats(
                [geom],
                f"/vsicurl/{_url}",
                stats=["mean", "max", "percentile_90", "count"],
            )[0]
        return _result

    ward_utci_1500_stats = zonal_stats_for_geom(
        selected_ward.iloc[0].geometry, "urban_extent", "utci_1500_baseline"
    )

    mo.vstack([
        mo.md(f"""
        ### Ward {SELECTED_WARD_NAME} — UTCI 1500 baseline (afternoon peak)

        Computed via zonal stats over the `urban_extent` COG (full-city coverage),
        clipped to Ward {SELECTED_WARD_NAME}\'s exact polygon.
        """),
        mo.ui.table(
            pd.DataFrame([{
                "mean_utci": round(ward_utci_1500_stats["mean"], 1),
                "p90_utci": round(ward_utci_1500_stats["percentile_90"], 1),
                "max_utci": round(ward_utci_1500_stats["max"], 1),
                "valid_pixels": ward_utci_1500_stats["count"],
            }]),
            selection=None,
        ),
    ])
    return GDAL_ENV, cog_url_for, zonal_stats_for_geom


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Note — zonal stats performance:** Computing zonal stats for a single
    neighborhood over a full-city COG via `/vsicurl/` is slow. The run above
    (Ward 115, ~11.5M valid pixels) took **~37–42 seconds**. This is COG tile
    fetch latency over the network, not a full-file download — but it adds up
    if we need this per-neighborhood, per-indicator, or interactively. Actual
    time will vary by network conditions and ward size; this is one data point,
    not a guarantee.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Hack custom neighborhoods

    We'll need to use a hack for neighborhoods for now -- we'll subdivide the business district area, where COG data is available for multiple indicators, into 5-6 smaller neighborhoods, and have the user select one of them.
    """)
    return


@app.cell(hide_code=True)
def _(aoi_geoms, box, folium, gpd, mapping, mo):
    def _make_grid_zones(geom_wgs84, crs_m="EPSG:32734", n_cols=3, n_rows=2, min_area_frac=0.03):
        """Subdivide a polygon into a rectangular grid, clipped to its shape.

        This is a deliberate hack: there\'s no real dataset that subdivides
        `business_district` into multiple neighborhoods (see exploration above),
        so we lay a simple grid over its bounding box and clip each cell to the
        actual polygon. Grid cells that only clip a sliver corner (below
        `min_area_frac` of the total area) are dropped.
        """
        _geom_m = gpd.GeoSeries([geom_wgs84], crs="EPSG:4326").to_crs(crs_m).iloc[0]
        _minx, _miny, _maxx, _maxy = _geom_m.bounds
        _dx = (_maxx - _minx) / n_cols
        _dy = (_maxy - _miny) / n_rows
        _total_area = _geom_m.area

        _cells = []
        for _row in range(n_rows):
            for _col in range(n_cols):
                _cell_box = box(
                    _minx + _col * _dx, _miny + _row * _dy,
                    _minx + (_col + 1) * _dx, _miny + (_row + 1) * _dy,
                )
                _clipped = _cell_box.intersection(_geom_m)
                if not _clipped.is_empty and _clipped.area / _total_area >= min_area_frac:
                    _cells.append(_clipped)

        # Order top-to-bottom, left-to-right for stable, intuitive naming.
        _cells.sort(key=lambda g: (-g.centroid.y, g.centroid.x))
        _zone_names = [f"Zone {chr(65 + i)}" for i in range(len(_cells))]
        _zones_m = gpd.GeoDataFrame({"zone_name": _zone_names}, geometry=_cells, crs=crs_m)
        _zones_m["area_sqkm"] = _zones_m.geometry.area / 1e6
        return _zones_m.to_crs("EPSG:4326")


    custom_neighborhoods = _make_grid_zones(aoi_geoms["business_district"], n_cols=3, n_rows=2)

    _zone_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    _minx, _miny, _maxx, _maxy = custom_neighborhoods.total_bounds
    _center_lat, _center_lon = (_miny + _maxy) / 2, (_minx + _maxx) / 2

    zones_map = folium.Map(
        location=[_center_lat, _center_lon],
        tiles="CartoDB positron",
        width=600,
        height=500,
    )
    zones_map.fit_bounds([[_miny, _minx], [_maxy, _maxx]], padding=(20, 20))

    for _i, _row in custom_neighborhoods.iterrows():
        folium.GeoJson(
            {"type": "Feature", "geometry": mapping(_row.geometry), "properties": {}},
            style_function=lambda _x, _c=_zone_colors[_i % len(_zone_colors)]: {
                "fillColor": _c, "color": _c, "weight": 2, "fillOpacity": 0.35,
            },
            tooltip=f"{_row.zone_name} ({_row.area_sqkm:.2f} km²)",
        ).add_to(zones_map)

    mo.vstack([
        mo.md(f"""
        ### Hand-drawn zones: {len(custom_neighborhoods)} sub-areas of `business_district`

        A 3x2 rectangular grid laid over the CBD bounding box, clipped to the
        actual `business_district` polygon; grid cells that only clip a sliver
        corner (< 3% of total area) are dropped. This yields {len(custom_neighborhoods)}
        zones, all **fully contained within `business_district`** — unlike Ward 115,
        these support the complete set of business_district-scoped indicators
        (scenarios, deltas), not just the whole-city baseline.
        """),
        mo.ui.table(
            custom_neighborhoods[["zone_name", "area_sqkm"]].round(2),
            selection=None,
        ),
        zones_map,
    ])

    return (custom_neighborhoods,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Select Neighborhood
    """)
    return


@app.cell(hide_code=True)
def _(custom_neighborhoods, mo):
    neighborhood_dropdown = mo.ui.dropdown(
        options=custom_neighborhoods["zone_name"].tolist(),
        value=custom_neighborhoods["zone_name"].iloc[0],
        label="Select a neighborhood (hand-drawn zone)",
    )
    neighborhood_dropdown

    return (neighborhood_dropdown,)


@app.cell
def _(custom_neighborhoods, neighborhood_dropdown):
    selected_zone = custom_neighborhoods.set_index("zone_name").loc[neighborhood_dropdown.value]

    return (selected_zone,)


@app.cell
def _(selected_zone):
    selected_zone
    return


@app.cell
def _(
    aoi_geoms,
    folium,
    gpd,
    indicator_dropdown,
    mapping,
    mo,
    neighborhood_dropdown,
    selected_zone,
):
    # Visual coverage check: overlay the selected neighborhood (one of our
    # hand-drawn zones) against the precise AOI polygon backing whichever
    # indicator is chosen above.

    _selected_aoi, _selected_layer_id = indicator_dropdown.value
    _neighborhood_geom = selected_zone.geometry
    _aoi_geom_overlay = aoi_geoms[_selected_aoi]

    _neighborhood_gdf_m = gpd.GeoDataFrame(geometry=[_neighborhood_geom], crs="EPSG:4326").to_crs("EPSG:32734")
    _aoi_gdf_m = gpd.GeoDataFrame(geometry=[_aoi_geom_overlay], crs="EPSG:4326").to_crs("EPSG:32734")
    _neighborhood_geom_m = _neighborhood_gdf_m.iloc[0].geometry
    _aoi_geom_m = _aoi_gdf_m.iloc[0].geometry

    _intersection_m = _neighborhood_geom_m.intersection(_aoi_geom_m)
    _pct_covered = _intersection_m.area / _neighborhood_geom_m.area * 100

    # The actual concern: the part of the neighborhood with NO data coverage.
    _uncovered_geom_m = _neighborhood_geom_m.difference(_aoi_geom_m)
    _uncovered_geom = (
        gpd.GeoSeries([_uncovered_geom_m], crs="EPSG:32734").to_crs("EPSG:4326").iloc[0]
        if not _uncovered_geom_m.is_empty
        else None
    )

    # Fit the map to whichever is bigger — the neighborhood or the coverage
    # AOI (business_district is tiny, urban_extent is city-wide) — with padding.
    _combined_bounds = gpd.GeoSeries(
        [_neighborhood_geom, _aoi_geom_overlay], crs="EPSG:4326"
    ).total_bounds  # [minx, miny, maxx, maxy]
    _minx, _miny, _maxx, _maxy = _combined_bounds
    _center_lat, _center_lon = (_miny + _maxy) / 2, (_minx + _maxx) / 2

    coverage_map = folium.Map(
        location=[_center_lat, _center_lon],
        tiles="CartoDB positron",
        width=600,
        height=500,
    )
    coverage_map.fit_bounds([[_miny, _minx], [_maxy, _maxx]], padding=(20, 20))

    folium.GeoJson(
        {"type": "Feature", "geometry": mapping(_aoi_geom_overlay), "properties": {}},
        style_function=lambda _x: {
            "fillColor": "#7f7f7f", "color": "#595959",
            "weight": 1.5, "dashArray": "4 3", "fillOpacity": 0.2,
        },
        tooltip=f"Data coverage: {_selected_aoi}",
    ).add_to(coverage_map)
    folium.GeoJson(
        {"type": "Feature", "geometry": mapping(_neighborhood_geom), "properties": {}},
        style_function=lambda _x: {"fillColor": "#2ca02c", "color": "#2ca02c", "weight": 2, "fillOpacity": 0.25},
        tooltip=f"{neighborhood_dropdown.value} (selected neighborhood)",
    ).add_to(coverage_map)
    if _uncovered_geom is not None:
        folium.GeoJson(
            {"type": "Feature", "geometry": mapping(_uncovered_geom), "properties": {}},
            style_function=lambda _x: {
                "fillColor": "#d62728", "color": "#d62728",
                "weight": 1.5, "fillOpacity": 0.45,
            },
            tooltip="No data coverage for this indicator",
        ).add_to(coverage_map)

    _coverage_note = (
        f"**{_pct_covered:.1f}% of the neighborhood is covered** by data for this indicator."
    )
    if _pct_covered < 99:
        _coverage_note += (
            " Stats computed over the full neighborhood would be **partial** —"
            " only representative of the overlapping area (red area excluded)."
        )

    mo.vstack([
        mo.md(f"""
        ### Coverage check: {indicator_dropdown.selected_key}

        {_coverage_note}

        ⬜ Gray dashed = data coverage area (`{_selected_aoi}`)<br> 
        🟢 Green = selected neighborhood ({neighborhood_dropdown.value}) · 🔴 Red = no data coverage
        """),
        coverage_map,
    ])

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Compute zonal stats for selected neighborhood
    """)
    return


@app.cell
def _(indicator_dropdown):
    _selected_aoi, _selected_layer_id = indicator_dropdown.value
    
    print(f"The Selected indicator is: {_selected_layer_id}")
    return


@app.cell(hide_code=True)
def _(
    GDAL_ENV,
    LST_COG_KEY,
    S3_BASE,
    TREE_COVER_COG_KEY,
    WORLDPOP_ELDERLY_COG_KEY,
    WORLDPOP_GENERAL_COG_KEY,
    mo,
    neighborhood_dropdown,
    pd,
    rasterio,
    selected_zone,
    zonal_stats,
    zonal_stats_for_geom,
):
    def _zonal_stat(geom, s3_key, stat="mean"):
        _url = f"{S3_BASE}/{s3_key}"
        with rasterio.Env(**GDAL_ENV):
            return zonal_stats([geom], f"/vsicurl/{_url}", stats=[stat])[0][stat]

    # Thermal stress: fixed to the primary baseline (afternoon peak),
    # business_district-scoped. This section now reports a fixed set of four
    # indicators for the selected zone, not whichever indicator the exploratory
    # dropdown above happens to have selected.
    _utci_stats = zonal_stats_for_geom(selected_zone.geometry, "business_district", "utci_1500_baseline")

    # Land surface temperature (deg C)
    _lst_mean = _zonal_stat(selected_zone.geometry, LST_COG_KEY)

    # Tree canopy cover (stored as a 0-1 fraction; report as %)
    _tree_cover_pct = _zonal_stat(selected_zone.geometry, TREE_COVER_COG_KEY) * 100

    # Vulnerable population: % elderly = sum(elderly) / sum(general population)
    # over the zone. Population rasters are per-pixel counts, so this needs
    # sums, not an average of per-pixel means.
    _elderly_sum = _zonal_stat(selected_zone.geometry, WORLDPOP_ELDERLY_COG_KEY, stat="sum")
    _general_sum = _zonal_stat(selected_zone.geometry, WORLDPOP_GENERAL_COG_KEY, stat="sum")
    _elderly_pct = (_elderly_sum / _general_sum * 100) if _general_sum else float("nan")

    zone_indicator_stats = {
        "thermal_stress": {
            "mean": _utci_stats["mean"], "p90": _utci_stats["percentile_90"],
            "max": _utci_stats["max"], "units": "UTCI",
        },
        "land_surface_temperature": {"mean": _lst_mean, "units": "deg C"},
        "tree_canopy_cover": {"mean": _tree_cover_pct, "units": "%"},
        "vulnerable_population": {
            "pct_elderly": _elderly_pct, "elderly_count": _elderly_sum,
            "general_count": _general_sum, "units": "% of population (elderly)",
        },
    }

    mo.vstack([
        mo.md(f"""
        ### {neighborhood_dropdown.value} — indicator summary

        Zonal stats for {neighborhood_dropdown.value}\'s exact polygon, across the
        four indicators needed for the selected-area-summary wireframe: thermal
        stress (UTCI 1500 baseline), land surface temperature, tree canopy cover,
        and vulnerable population (% elderly).
        """),
        mo.ui.table(
            pd.DataFrame([
                {"indicator": "Thermal stress (UTCI 1500 baseline)", "zone_value": round(zone_indicator_stats["thermal_stress"]["mean"], 1), "units": "UTCI"},
                {"indicator": "Land surface temperature", "zone_value": round(zone_indicator_stats["land_surface_temperature"]["mean"], 1), "units": "deg C"},
                {"indicator": "Tree canopy cover", "zone_value": round(zone_indicator_stats["tree_canopy_cover"]["mean"], 1), "units": "%"},
                {"indicator": "Vulnerable population (% elderly)", "zone_value": round(zone_indicator_stats["vulnerable_population"]["pct_elderly"], 1), "units": "%"},
            ]),
            selection=None,
        ),
    ])

    return (zone_indicator_stats,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This runs in about 2-3 seconds.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Example: comparing methods for whole-area stats

    Before wiring this into the live indicator selection, here's a comparison
    of the options we tried for getting whole-area stats (mean/p90/max over an
    entire AOI — `urban_extent` or `business_district`): precomputed API
    scalars vs. computing from the COG overview pyramid at different
    decimation levels.

    **This section is fixed** (`urban_extent`, UTCI 1500 baseline) for a clean
    side-by-side comparison — it does not track the indicator picked above. See
    the next section for the live version, driven by whichever indicator is
    currently selected.
    """)

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Precomputed whole city stats

    Unfortunately, this turns out to be too limited.
    * pedestrian mask
    * only mean

    If we want precomputed, we'll have to add more precomputed keys.
    """)
    return


@app.cell
def _(indicator_values, mo):
    # Precomputed scalar from the API — no zonal stats needed, this is
    # already aggregated server-side over the urban_extent AOI.
    _urban_extent_utci_1500_key = (
        "mean_utci_1500_baseline_pedestrian__ZAF-Cape_Town__urban_extent__baseline"
    )
    urban_extent_utci_1500_mean = indicator_values["urban_extent"][_urban_extent_utci_1500_key]

    mo.vstack([
        mo.md(f"""
        **Whole city — UTCI 1500 baseline, pedestrian areas (precomputed):**

        | Stat | Value |
        |---|---|
        | Mean | {urban_extent_utci_1500_mean} |
        | p90 | *not available* |
        | Max | *not available* |

        **Important conclusion:** the `urban_extent` AOI only has 2 precomputed
        scalar keys in the whole API response — this mean, and one shade_cover
        metric. There is no precomputed p90 or max for baseline UTCI at the
        whole-city level (`max_utci_1500_*` only exists for `business_district`,
        and only for scenario/change layers, not baseline). To get p90/max for
        the whole city we\'ll need to compute them ourselves from the COG —
        see below.

        Also note: this scalar is scoped to **pedestrian-accessible areas**
        only. Our ward-level zonal stat used the full raster (no pedestrian
        mask) — so these two numbers are not yet a strict apples-to-apples
        comparison.
        """),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Whole City compute with Sampling

    Computing the indicator stats for the whole city would be very slow, but we can try a sampling approach.

    This is necessary because we need a statistical summary of the selected indicator for the whole city, and this isn't available.
    """)
    return


@app.cell(hide_code=True)
def _(GDAL_ENV, cog_url_for, mo, np, rasterio):
    # Whole-city p90/max are NOT precomputed (see note above), so we compute
    # them ourselves — but reading the full-resolution urban_extent COG
    # (40015x33119 px) is too slow for this notebook. Instead we read a
    # decimated overview (1/32 scale, nearest resampling) directly from the
    # COG\'s built-in overview pyramid. This is fast (COGs store overviews as
    # separate low-res IFDs) but approximate — especially max, since it only
    # samples 1-in-32 pixels in each dimension rather than every pixel.

    _OVERVIEW_DECIMATION = 32

    def overview_stats(aoi: str, layer_id: str, decimation: int = _OVERVIEW_DECIMATION) -> dict:
        _url = cog_url_for(aoi, layer_id)
        with rasterio.Env(**GDAL_ENV):
            with rasterio.open(f"/vsicurl/{_url}") as _src:
                _data = _src.read(
                    1,
                    out_shape=(
                        _src.count,
                        max(1, _src.height // decimation),
                        max(1, _src.width // decimation),
                    ),
                    resampling=rasterio.enums.Resampling.nearest,
                )
                _nodata = _src.nodata
        _valid = _data[_data != _nodata] if _nodata is not None else _data.flatten()
        _valid = _valid[~np.isnan(_valid)]
        return {
            "mean": float(np.mean(_valid)),
            "percentile_90": float(np.percentile(_valid, 90)),
            "max": float(np.max(_valid)),
            "count": int(_valid.size),
        }

    urban_extent_utci_1500_overview_stats = overview_stats("urban_extent", "utci_1500_baseline")

    mo.vstack([
        mo.md(f"""
        **Whole city — UTCI 1500 baseline, computed from COG overview (1/{_OVERVIEW_DECIMATION} scale, approximate):**

        | Stat | Value |
        |---|---|
        | Mean | {urban_extent_utci_1500_overview_stats["mean"]:.1f} |
        | p90 | {urban_extent_utci_1500_overview_stats["percentile_90"]:.1f} |
        | Max | {urban_extent_utci_1500_overview_stats["max"]:.1f} |
        | Sampled pixels | {urban_extent_utci_1500_overview_stats["count"]:,} |

        Caveat: this samples every 32nd pixel (nearest, not averaged), so it
        is fast (near-instant) but approximate — mean and p90 are stable across
        overview levels we tested, but max is a lower-bound estimate since a
        true single-pixel peak could be missed by the sampling. Full-resolution
        zonal stats over this raster (40015x33119 px, no windowing possible
        since it's the whole city) would take much longer — not attempted here.
        """),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    **Note — overview decimation level matters a lot for compute time.**

    When computing whole-city stats from the COG overview pyramid, we tried a
    few decimation levels against the same raster:

    | Decimation | Elapsed | Notes |
    |---|---|---|
    | 1/8 | ~50s | First read of this raster in the session |
    | 1/32 | ~1s | |
    | 1/64 | ~1.6s | |
    | 1/128 | ~0.2s | |

    The 1/8 read was much slower than the coarser levels — partly because it
    requests more output pixels (so GDAL fetches a larger overview IFD), and
    partly because it was the *first* open of this COG in the session, before
    any HTTP range requests or metadata were cached (`VSI_CACHE`). Once the
    file's structure was cached, subsequent reads at coarser levels were
    consistently fast.

    Practical takeaway: for whole-city approximate stats, prefer a coarse
    overview (1/32 or coarser) — it's both faster to request and, after the
    first COG open in a session, benefits from caching on later calls too.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Whole business_district stats for the four indicators

    Same four indicators as the zone stats above, computed for the whole
    `business_district` polygon instead of the selected zone — this is the
    "city" reference value each zone gets compared against. Uses the same exact
    per-polygon zonal stats method as the zone computation (not the COG-overview
    sampling approach compared in the "Example" section above), so zone and city
    values are computed identically and are directly comparable.
    """)

    return


@app.cell(hide_code=True)
def _(
    GDAL_ENV,
    LST_COG_KEY,
    S3_BASE,
    TREE_COVER_COG_KEY,
    WORLDPOP_ELDERLY_COG_KEY,
    WORLDPOP_GENERAL_COG_KEY,
    aoi_geoms,
    mo,
    pd,
    rasterio,
    zonal_stats,
    zonal_stats_for_geom,
):
    def _zonal_stat(geom, s3_key, stat="mean"):
        _url = f"{S3_BASE}/{s3_key}"
        with rasterio.Env(**GDAL_ENV):
            return zonal_stats([geom], f"/vsicurl/{_url}", stats=[stat])[0][stat]

    _business_district_geom = aoi_geoms["business_district"]

    # Thermal stress: same primary baseline as the zone stats above, clipped to
    # the whole business_district polygon instead of the selected zone.
    _utci_city_stats = zonal_stats_for_geom(_business_district_geom, "business_district", "utci_1500_baseline")

    _lst_city_mean = _zonal_stat(_business_district_geom, LST_COG_KEY)
    _tree_cover_city_pct = _zonal_stat(_business_district_geom, TREE_COVER_COG_KEY) * 100

    # Vulnerable population: urban_extent-scoped rasters clipped to the
    # business_district polygon directly (no business_district-specific file
    # exists for these — see "Beyond UTCI" section above).
    _elderly_city_sum = _zonal_stat(_business_district_geom, WORLDPOP_ELDERLY_COG_KEY, stat="sum")
    _general_city_sum = _zonal_stat(_business_district_geom, WORLDPOP_GENERAL_COG_KEY, stat="sum")
    _elderly_city_pct = (_elderly_city_sum / _general_city_sum * 100) if _general_city_sum else float("nan")

    city_indicator_stats = {
        "thermal_stress": {
            "mean": _utci_city_stats["mean"], "p90": _utci_city_stats["percentile_90"],
            "max": _utci_city_stats["max"], "units": "UTCI",
        },
        "land_surface_temperature": {"mean": _lst_city_mean, "units": "deg C"},
        "tree_canopy_cover": {"mean": _tree_cover_city_pct, "units": "%"},
        "vulnerable_population": {
            "pct_elderly": _elderly_city_pct, "elderly_count": _elderly_city_sum,
            "general_count": _general_city_sum, "units": "% of population (elderly)",
        },
    }

    mo.vstack([
        mo.md(f"""
        ### Whole `business_district` — indicator summary
        """),
        mo.ui.table(
            pd.DataFrame([
                {"indicator": "Thermal stress (UTCI 1500 baseline)", "business_district_value": round(city_indicator_stats["thermal_stress"]["mean"], 1), "units": "UTCI"},
                {"indicator": "Land surface temperature", "business_district_value": round(city_indicator_stats["land_surface_temperature"]["mean"], 1), "units": "deg C"},
                {"indicator": "Tree canopy cover", "business_district_value": round(city_indicator_stats["tree_canopy_cover"]["mean"], 1), "units": "%"},
                {"indicator": "Vulnerable population (% elderly)", "business_district_value": round(city_indicator_stats["vulnerable_population"]["pct_elderly"], 1), "units": "%"},
            ]),
            selection=None,
        ),
    ])

    return (city_indicator_stats,)


@app.cell
def _(k):
    k
    return


@app.cell
def _(city_indicator_stats, mo, neighborhood_dropdown, zone_indicator_stats):
    summary_prompt = f"""
    You are a city climate analyst preparing a brief for a city planner who is
    reviewing "{neighborhood_dropdown.value}", a neighborhood in Cape Town.

    Write a short, plain-language summary of this area's heat-related
    characteristics compared to the rest of the city (business_district
    average). Avoid jargon. Cite the specific numbers below. Highlight what is
    most notable about this area — don't just list every statistic evenly.
    Keep it concise (2-4 sentences).

    Data for "{neighborhood_dropdown.value}" vs. the business_district average:

    - Thermal stress (UTCI, afternoon peak): {zone_indicator_stats['thermal_stress']['mean']:.1f} vs. city average {city_indicator_stats['thermal_stress']['mean']:.1f}
    - Land surface temperature (deg C): {zone_indicator_stats['land_surface_temperature']['mean']:.1f} vs. city average {city_indicator_stats['land_surface_temperature']['mean']:.1f}
    - Tree canopy cover (%): {zone_indicator_stats['tree_canopy_cover']['mean']:.1f} vs. city average {city_indicator_stats['tree_canopy_cover']['mean']:.1f}
    - Vulnerable population (% elderly): {zone_indicator_stats['vulnerable_population']['pct_elderly']:.1f} vs. city average {city_indicator_stats['vulnerable_population']['pct_elderly']:.1f}
    """

    mo.md(f"""
    ### Generated LLM prompt

    ```text
    {summary_prompt}
    ```
    """)

    return (summary_prompt,)


@app.cell
def _(mo, summary_prompt):
    prompt_input = mo.ui.text_area(
        value=summary_prompt,
        label="Enter your prompt",
        full_width=True,
    )

    temperature_slider = mo.ui.slider(
        start=0.0, stop=2.0, step=0.1, value=0.2, label="Temperature"
    )

    run_button = mo.ui.run_button(label="Query Models")

    mo.vstack([prompt_input, temperature_slider, run_button])

    return prompt_input, run_button, temperature_slider


@app.cell
def _(mo, prompt_input, run_button, temperature_slider):
    mo.stop(not run_button.value, mo.md("*Click \"Query Models\" to run.*"))

    import litellm

    _response = litellm.completion(
        model="openrouter/qwen/qwen3-32b",
        messages=[{"role": "user", "content": prompt_input.value}],
        temperature=temperature_slider.value,
    )

    response_text = _response.choices[0].message.content

    mo.md(f"""
    ### Model response

    {response_text}
    """)

    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
