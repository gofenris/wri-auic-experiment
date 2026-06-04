# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "requests==2.34.2",
#     "pandas==3.0.3",
#     "altair==6.1.0",
#     "pyarrow==24.0.0",
# ]
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import requests
    import pandas as pd
    import altair as alt
    import json
    from collections import defaultdict

    return alt, defaultdict, json, mo, pd, requests


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # CCL API explorer

    Notebook 1 of 3. Explores the public Cool Cities Lab REST API at `https://cities-data-api.wri.org`.

    Topic: Exploration of the public Cool Cities Lab (CCL) REST API at https://cities-data-api.wri.org.

    **Objectives:**
    - Understand which cities have data and what their coverage looks like
    - list endpoints and what they contain
    - Classify indicator keys into data categories: baselines, model outputs, scenario outputs
    - Check whether baseline values are duplicated across scenarios
    - Document what the layer and scenario endpoints actually return

    Key findings: 
        * The API is primarily a map configuration service — actual raster data lives in S3 as COG files; the API only surfaces aggregated scalar indicators and map-styling metadata.
        * No credentials required — the API is public.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## API architecture

    The CCL API has four endpoint types with distinct purposes:

    | Endpoint | Returns |
    |----------|---------|
    | `/cities?application_id=ccl` | All cities with full `indicator_values` scalar blob |
    | `/cities/{city_id}?application_id=ccl` | Same structure, single city |
    | `/layers/{layer_id}/{city_id}` | Display metadata for one map layer (styling, colormap, legend) |
    | `/scenarios/{city_id}/{aoi_id}/{scenario_id}` | Ordered list of layer metadata objects to render for a scenario |

    The API is primarily a **map configuration service**. The `/layers` and `/scenarios` endpoints
    tell a frontend which COG rasters to display and how to style them — they do not return
    raster data or computed values directly. The underlying raster data lives in S3:

    ```
    s3://wri-cities-data-api/data/dev/{dataset}/cog/{city_id}__{aoi_id}__{layer_id}__{version}.tif
    ```

    The scalar `indicator_values` in `/cities` are the only place aggregated numbers are
    surfaced directly via the API.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Possible data gaps — open questions

    These are observations from initial inspection. They may reflect data issues, API design
    choices, or gaps in our understanding — confirmation with the CCL team is needed before
    drawing conclusions.

    | Question | Observation |
    |----------|-------------|
    | Is there population or vulnerability data? | Not found in `/cities` — needed for equity-based prioritisation ideas |
    | Is there land use or public asset data? | Not found — needed for solution opportunity mapping |
    | Is there cost data of any kind? | Not found — cost estimation ideas require fully user-supplied inputs |
    | Why does simulation date vary (2020–2025)? | Different cities simulated at different times — may affect cross-city comparability |
    | Do urban extent AOIs have indicators? | Only primary AOIs appear to have indicator data — urban extent seems excluded |
    | Are there seasonal or multi-day baselines? | All data appears to be a single simulated day per city |
    | Where are the priority opportunity indices? | Not surfaced as scalars — may exist as COG layers only |
    | Are some "baseline" values actually scenario outputs? | Section 4 finds 22 cases where baseline keys differ across scenarios, concentrated in a fourth scenario type (`street_trees_achievable_cool_roofs_all`) not present in most cities — values look implausible as baselines |
    | Are some model output values erroneous? | `achievable_cool_roof_reflectivity` for Recife is 1915 and `achievable_reflectivity` is 772 — neither is a plausible reflectivity value (expected 0–100). `tree_cover_progress` for Bhopal is -64%, which may indicate data below baseline or a calculation error. Most other apparent anomalies (`progress_reflectivity` > 100%) are likely intentional overachievement readings. |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 1. Fetch all cities
    """)
    return


@app.cell
def _(requests):
    BASE_URL = "https://cities-data-api.wri.org"
    response = requests.get(f"{BASE_URL}/cities?application_id=ccl")
    response.raise_for_status()
    cities_raw = response.json()["cities"]
    print(f"Fetched {len(cities_raw)} cities")
    return BASE_URL, cities_raw


@app.cell
def _(cities_raw, pd):
    cities_df = pd.DataFrame([
        {
            "id": c["id"],
            "name": c["name"],
            "country": c["country_name"],
            "aois": ", ".join(c.get("area_of_interests") or []),
            "simulation_date": c.get("utci_simulation_date"),
            "has_indicators": bool(c.get("indicator_values")),
            "n_indicators": sum(
                len(aoi_data)
                for aoi_data in (c.get("indicator_values") or {}).values()
            ),
        }
        for c in cities_raw
    ])
    cities_df
    return (cities_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 2. Coverage summary
    """)
    return


@app.cell
def _(cities_df, mo):
    n_total = len(cities_df)
    n_with_data = int(cities_df["has_indicators"].sum())
    aoi_types = set(
        a.strip()
        for aois in cities_df["aois"]
        for a in aois.split(",")
        if a.strip()
    )
    mo.md(f"""
    | Metric | Value |
    |--------|-------|
    | Total cities | {n_total} |
    | Cities with indicator data | {n_with_data} |
    | Cities without indicator data | {n_total - n_with_data} |
    | Unique AOI types | {len(aoi_types)} |
    | AOI types | {", ".join(sorted(aoi_types))} |
    """)
    return


@app.cell
def _(alt, cities_df, mo):
    cities_sorted = cities_df[cities_df["has_indicators"]].sort_values("n_indicators", ascending=False)
    chart = alt.Chart(cities_sorted).mark_bar(color="#378ADD").encode(
        x=alt.X("n_indicators:Q", title="Number of indicator values"),
        y=alt.Y("name:N", sort="-x", title=None)
    ).properties(
        title="Indicator count per city (cities with data only)",
        width=600,
        height=250
    )
    mo.ui.altair_chart(chart)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 3. Indicator key structure and classification

    Every entry in `indicator_values` follows this pattern:

    ```
    {metric_stem}__{city_id}__{aoi_id}__{scenario_id}
    ```

    Example:
    ```
    mean_utci_1500_baseline_nonbuilding_areas__ARG-Buenos_Aires__barrio_20__cool_roofs_large_buildings
    ```

    The metric stem encodes the data category via keywords (`baseline`, `scenario`, `change`) or
    prefix (`achievable_`, `progress_`, `utci_reduction_`, `air_temp_reduction_`).
    The scenario ID is appended to every key — including baseline metrics — so baseline
    values appear once per scenario. Section 4 checks whether those copies are identical.
    """)
    return


@app.cell
def _(cities_raw, defaultdict):
    MODEL_OUTPUT_PREFIXES = [
        "achievable_",
        "progress_",
        "tree_cover_progress",
        "utci_reduction_",
        "air_temp_reduction_",
    ]

    category_counts = defaultdict(int)
    baseline_stems = set()
    scenario_stems = defaultdict(set)
    model_output_stems = set()
    all_scenario_ids = set()

    for _city in cities_raw:
        for _aoi_data in (_city.get("indicator_values") or {}).values():
            for _key in _aoi_data:
                _parts = _key.split("__")
                _stem = _parts[0]
                if len(_parts) > 3:
                    all_scenario_ids.add(_parts[3])
                if any(_stem.startswith(p) for p in MODEL_OUTPUT_PREFIXES):
                    category_counts["model_output"] += 1
                    model_output_stems.add(_stem)
                elif "_baseline_" in _key or _key.startswith("baseline_"):
                    category_counts["baseline"] += 1
                    baseline_stems.add(_stem)
                elif "_scenario_" in _key or _key.startswith("scenario_"):
                    category_counts["scenario"] += 1
                elif "_change_" in _key or _key.startswith("change_"):
                    category_counts["change_delta"] += 1
                else:
                    category_counts["other"] += 1

    print("Indicator key counts by category:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")
    print(f"\nAll scenario IDs found in data ({len(all_scenario_ids)}):")
    for sid in sorted(all_scenario_ids):
        print(f"  {sid}")
    return (
        all_scenario_ids,
        baseline_stems,
        category_counts,
        model_output_stems,
    )


@app.cell
def _(alt, category_counts, mo, pd):
    cat_df = pd.DataFrame([
        {"category": k, "count": v}
        for k, v in sorted(category_counts.items())
    ])
    cat_chart = alt.Chart(cat_df).mark_bar(color="#378ADD").encode(
        x=alt.X("category:N", title=None),
        y=alt.Y("count:Q", title="Key count")
    ).properties(title="Indicator keys by category", width=400, height=200)
    mo.ui.altair_chart(cat_chart)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 4. Are baseline values identical across scenarios?
    """)
    return


@app.cell
def _(cities_raw, defaultdict, mo):
    mismatches = []
    checked_pairs = 0

    for _city in cities_raw:
        for _aoi, _aoi_data in (_city.get("indicator_values") or {}).items():
            stem_to_entries = defaultdict(dict)
            for _key, _val in _aoi_data.items():
                _parts = _key.split("__")
                _stem = _parts[0]
                _scenario = _parts[3] if len(_parts) > 3 else "unknown"
                if "_baseline_" in _key or _key.startswith("baseline_"):
                    stem_to_entries[_stem][_scenario] = _val

            for _stem, scenario_vals in stem_to_entries.items():
                if len(scenario_vals) > 1:
                    checked_pairs += 1
                    vals = list(scenario_vals.values())
                    if len(set(vals)) > 1:
                        mismatches.append({
                            "city": _city["name"],
                            "aoi": _aoi,
                            "stem": _stem,
                            "values": scenario_vals,
                        })

    result = (
        mo.md(f"**{len(mismatches)} mismatches** found across {checked_pairs} checked pairs — see notes in possible gaps above.")
        if mismatches else
        mo.md(f"**No mismatches** across {checked_pairs} checked pairs — baseline values are identical across scenarios. The duplication is redundant storage only.")
    )
    result
    return (mismatches,)


@app.cell
def _(mismatches, pd):
    mismatch_df = pd.DataFrame([
        {
            "city": m["city"],
            "aoi": m["aoi"],
            "stem": m["stem"],
            "scenarios": ", ".join(m["values"].keys()),
            "values": ", ".join(str(round(v, 3)) if isinstance(v, float) else str(v) for v in m["values"].values()),
        }
        for m in mismatches
    ])
    mismatch_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 5. Baseline metric stems
    """)
    return


@app.cell
def _(baseline_stems, pd):
    def parse_stem(stem):
        time = next((t for t in ["1200", "1500", "1800"] if t in stem), "all")
        area = (
            "pedestrian" if "pedestrian" in stem
            else "park" if "park" in stem
            else "non-building" if "nonbuilding" in stem
            else "area"
        )
        return time, area

    baseline_rows = []
    for _stem in sorted(baseline_stems):
        time, area = parse_stem(_stem)
        baseline_rows.append({"metric_stem": _stem, "time_of_day": time, "area_type": area})

    pd.DataFrame(baseline_rows)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 6. Model output metric stems
    """)
    return


@app.cell
def _(model_output_stems, pd):
    pd.DataFrame([{"metric_stem": s} for s in sorted(model_output_stems)])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 7. Scenario coverage — which cities have which scenarios
    """)
    return


@app.cell
def _(all_scenario_ids, cities_raw, pd):
    scenario_coverage = []
    for _city in cities_raw:
        all_keys = " ".join(
            k
            for _aoi_data in (_city.get("indicator_values") or {}).values()
            for k in _aoi_data
        )
        row = {"city": _city["name"]}
        for _s in sorted(all_scenario_ids):
            row[_s] = "yes" if _s in all_keys else "no"
        scenario_coverage.append(row)

    pd.DataFrame(scenario_coverage)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 8. Layer endpoint

    Returns display metadata for a single named layer — styling, colormap, and legend
    configuration for rendering a COG raster in the map UI. Does not return raster data.
    """)
    return


@app.cell
def _(BASE_URL, json, requests):
    layer_resp = requests.get(
        f"{BASE_URL}/layers/utci_1500_baseline/ZAF-Cape_Town",
        timeout=10
    )
    layer_resp.raise_for_status()
    layer_data = layer_resp.json()
    print(json.dumps(layer_data, indent=2))
    return (layer_data,)


@app.cell
def _(layer_data, mo):
    styling = layer_data.get("map_styling", {})
    legend = layer_data.get("legend_styling", {})
    mo.md(f"""
    | Field | Value |
    |-------|-------|
    | `city_id` | `{layer_data.get("city_id")}` |
    | `layer_id` | `{layer_data.get("layer_id")}` |
    | `file_type` | `{layer_data.get("file_type")}` |
    | `datasets_id` | `{layer_data.get("datasets_id")}` |
    | `source_layer_id` | `{layer_data.get("source_layer_id")}` |
    | `colormap` | `{styling.get("colormap_name")}` ({styling.get("steps")} steps) |
    | `legend title` | {legend.get("title")} |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 9. Scenario endpoint

    Returns an ordered list of layer metadata objects — one per map layer to display
    together for a given scenario. Same metadata structure as the layer endpoint.
    Does not return computed values or raster data.
    """)
    return


@app.cell
def _(BASE_URL, json, requests):
    scenario_resp = requests.get(
        f"{BASE_URL}/scenarios/ZAF-Cape_Town/business_district/street_trees",
        timeout=10
    )
    scenario_resp.raise_for_status()
    scenario_data = scenario_resp.json()
    print(f"Returned {len(scenario_data)} layer objects")
    print(json.dumps(scenario_data[0], indent=2))
    return (scenario_data,)


@app.cell
def _(mo, pd, scenario_data):
    layers_summary = pd.DataFrame([
        {
            "layer_id": layer.get("layer_id"),
            "source_layer_id": layer.get("source_layer_id"),
            "file_type": layer.get("file_type"),
            "legend_title": (layer.get("legend_styling") or {}).get("title"),
        }
        for layer in scenario_data
    ])
    mo.md(f"The scenario endpoint returns **{len(scenario_data)} layer objects** for this scenario.")
    return (layers_summary,)


@app.cell
def _(layers_summary):
    layers_summary
    return


if __name__ == "__main__":
    app.run()
