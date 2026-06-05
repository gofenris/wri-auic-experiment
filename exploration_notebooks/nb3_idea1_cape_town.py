# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "requests==2.34.2",
#     "pandas==3.0.3",
#     "pyarrow==24.0.0",
# ]
# ///

import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Idea 1 × Cape Town — Data Feasibility Assessment

    **Idea:** Priority Area Identification & Exploration
    **City:** Cape Town (`ZAF-Cape_Town`)
    **Question:** Does the CCL data exist at a granularity that makes this idea viable?

    ---

    This notebook assesses one workshop idea against one city. It is not a general survey —
    it is a concrete feasibility check grounded in what the API and S3 bucket actually contain
    for Cape Town today.

    **Why granularity matters:**

    Most ideas say "do X for a selected city or AOI." That framing hides the key question:
    at what spatial resolution does the data exist?

    | Granularity | What it enables |
    |---|---|
    | City-level scalar | A single number per city — can summarise, cannot spatially vary |
    | District-level polygon attribute | One value per district — can compare districts, cannot support arbitrary custom AOIs |
    | Pixel-level raster (COG) | Spatially continuous — any custom AOI can be analysed via zonal statistics |

    Only pixel-level data supports freeform AOI workflows. District-level data can compare
    named areas, but a user cannot draw a polygon and get a meaningful result from it.
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import requests
    import pandas as pd
    import xml.etree.ElementTree as ET
    import re
    from pathlib import Path

    return ET, Path, mo, pd, re, requests


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 1.1. Recap of the Idea: Priority Area Identification & Exploration

    > *An interactive map workflow where users describe their goals or priorities, and the system
    > highlights suggested intervention areas on the map. Users can then select an area to explore
    > summaries, recommendations, intervention comparisons, or proposal-related workflows.*

    **Feasibility note from the workshop synthesis:**
    Priority will be determined by existing model outputs plus user-input goals. Goals are mapped
    to existing baseline layers — the example given is "vulnerable population density." The tool
    would generate AOI polygons, apply summaries, compute indices, and provide a natural language
    justification.

    **The crux question:**
    For a user who says "prioritise areas with high heat risk" or "prioritise areas with vulnerable
    populations," does Cape Town have the data to actually find those areas spatially?
    """)
    return


@app.cell
def _(Path, pd):
    CSV_PATH = Path(__file__).parent / "../local_data/Ideation workshop synthesis_temp_20260604.csv"
    ideas_df = pd.read_csv(CSV_PATH)
    idea1 = ideas_df.iloc[0]

    print(f"""
    Description: 
    {idea1["Description"]}, 

    Inputs: 
    {idea1["Inputs"]},

    Canela's Workstreams: 
    {idea1["Workstream"]},
    """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 1.1 What does Idea 1 actually need?

    The workshop synthesis names **"vulnerable population density"** as an example baseline layer that
    goals would be mapped onto. More broadly, to surface priority areas spatially, the idea needs at
    least one of the following:

    | Data need | Why it's needed |
    |---|---|
    | A heat risk or thermal stress layer, pixel-level | To find areas of high heat exposure |
    | A population density or vulnerability layer, pixel-level | To find areas where at-risk people are concentrated |
    | An exposure layer combining heat × population | The direct measure of who is most at risk |

    For any of these to support a custom AOI workflow, the data must exist **as a COG raster** —
    not just as a city-level scalar in the API.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 2. Cape Town

    I selected Cape Town because it is one of the cities with rich data. The sections below check what Cape Town actually has.

    ### 2.1 - Scalar indicator keys for Cape Town
    """)
    return


@app.cell
def _(mo, re, requests):
    CITY_ID = "ZAF-Cape_Town"
    BASE_URL = "https://cities-data-api.wri.org"

    resp = requests.get(f"{BASE_URL}/cities?application_id=ccl", timeout=15)
    all_cities = resp.json()["cities"]

    cape_town = next(c for c in all_cities if c.get("id") == CITY_ID)

    # indicator_values is keyed by AOI type; flatten all keys
    indicator_values = cape_town.get("indicator_values", {})
    aoi_types = list(indicator_values.keys())

    flat_keys = []
    for _aoi, _vals in indicator_values.items():
        for _k in _vals.keys():
            flat_keys.append(_k)

    # Extract the metric stem — the part before the first __ city_id section
    def extract_stem(indicator_key):
        # Keys are structured as: stem__city_id__aoi__scenario (sometimes)
        # The stem is everything before __ZAF-
        parts = re.split(r"__ZAF-", indicator_key)
        return parts[0]

    stems = sorted(set(extract_stem(k) for k in flat_keys))

    mo.vstack([
        mo.md(f"**Cape Town** has **{len(flat_keys)} indicator values** across AOI types: `{'`, `'.join(aoi_types)}`"),
        mo.md(f"**{len(stems)} unique metric stems** found."),
    ])
    return (stems,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 2.2 — Are any scalar indicators related to Idea 1's data needs?
    """)
    return


@app.cell
def _(mo, pd, stems):
    # Terms that would indicate population, vulnerability, or exposure data
    RELEVANCE_TERMS = [
        "pop", "vuln", "expos", "dens", "equit", "health", "income",
        "risk", "socio", "depri", "poverty", "age", "elderly", "disab",
    ]

    relevant_stems = [s for s in stems if any(t in s.lower() for t in RELEVANCE_TERMS)]

    # For context, also show the full stem list grouped by theme
    utci_stems = [s for s in stems if "utci" in s.lower()]
    shade_stems = [s for s in stems if "shade" in s.lower()]
    tree_stems = [s for s in stems if "tree" in s.lower()]
    roof_stems = [s for s in stems if "roof" in s.lower() or "reflectiv" in s.lower()]
    other_stems = [
        s for s in stems
        if s not in utci_stems + shade_stems + tree_stems + roof_stems + relevant_stems
    ]

    theme_df = pd.DataFrame([
        {"Theme": "UTCI thermal stress", "Count": len(utci_stems), "Examples": ", ".join(utci_stems[:3])},
        {"Theme": "Shade cover", "Count": len(shade_stems), "Examples": ", ".join(shade_stems[:3])},
        {"Theme": "Tree cover", "Count": len(tree_stems), "Examples": ", ".join(tree_stems[:3])},
        {"Theme": "Roof / reflectivity", "Count": len(roof_stems), "Examples": ", ".join(roof_stems[:3])},
        {"Theme": "Population / vulnerability / risk (Idea 1 needs)", "Count": len(relevant_stems), "Examples": ", ".join(relevant_stems[:3]) or "— none found —"},
        {"Theme": "Other", "Count": len(other_stems), "Examples": ", ".join(other_stems[:3])},
    ])

    mo.ui.table(theme_df, selection=None)
    return (relevant_stems,)


@app.cell(hide_code=True)
def _(mo, relevant_stems):

    print(relevant_stems)
    mo.md(f"**{len(relevant_stems)} scalar indicator(s) match population/vulnerability terms.** ")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 2.3 — COG raster inventory for Cape Town
    """)
    return


@app.cell
def _(ET, mo, pd, requests):
    S3_BASE = "https://wri-cities-data-api.s3.us-east-1.amazonaws.com"
    PREFIX = "data/dev/utci/cog/ZAF-Cape"

    s3_resp = requests.get(f"{S3_BASE}/?prefix={PREFIX}", timeout=15)
    s3_root = ET.fromstring(s3_resp.content)
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    # Time-of-day tokens that appear in layer_ids
    _TIME_TOKENS = {"1200", "1500", "1800"}

    # Spatial mask suffixes
    _MASK_TOKENS = {
        "pedestrian_areas": "pedestrian",
        "pedestrian-achievable-90pctl": "pedestrian",
        "non_buildings": "non-buildings",
        "non-building-areas": "non-buildings",
        "parks_areas": "parks",
        "shade_structure_areas": "shade structures",
    }

    def _parse_layer_id(layer_id):
        """Decompose a layer_id into time_of_day, data_type, intervention, spatial_mask."""
        lid = layer_id.lower()

        # Time of day
        time_of_day = next((t for t in _TIME_TOKENS if t in lid), "unknown")

        # Spatial mask — check suffixes
        spatial_mask = "full AOI"
        for token, label in _MASK_TOKENS.items():
            if lid.endswith(token) or f"_{token}" in lid or f"-{token}" in lid:
                spatial_mask = label
                break

        # Data type: delta if "vs" or "vs_baseline" or "vs-baseline" in name
        if "vs" in lid:
            data_type = "delta (vs baseline)"
        elif "baseline" in lid and not any(t in lid for t in ["achievable", "trees", "roofs", "shade", "cool"]):
            data_type = "baseline"
        else:
            data_type = "scenario"

        # Intervention — strip time token and mask token to isolate the intervention name
        # Remove utci_, time token, and known mask suffixes
        intervention_part = lid
        intervention_part = intervention_part.replace("utci_", "").replace("utci-", "")
        for t in _TIME_TOKENS:
            intervention_part = intervention_part.replace(f"{t}_", "").replace(f"{t}-", "")
        for token in _MASK_TOKENS:
            intervention_part = intervention_part.replace(f"_{token}", "").replace(f"-{token}", "")
        intervention_part = intervention_part.replace("_vs_baseline", "").replace("-vs-baseline", "")
        intervention_part = intervention_part.replace("_vs-baseline", "").replace("-vs_baseline", "")
        intervention_part = intervention_part.strip("_-")

        # Map to readable names
        _INTERVENTION_MAP = {
            "baseline": "baseline",
            "baseline__baseline": "baseline",
            "cool_roofs_achievable": "cool roofs",
            "cool_roofs": "cool roofs",
            "cool-roofs_trees__all-buildings": "cool roofs + trees",
            "street_trees_achievable": "street trees",
            "street_trees_cool_roofs_achievable": "street trees + cool roofs",
            "street_trees_cool_roofs": "street trees + cool roofs",
            "park_shade_achievable": "park shade",
            "park_shade": "park shade",
            "cool_roofs_large_buildings": "cool roofs (large buildings)",
        }
        intervention = _INTERVENTION_MAP.get(intervention_part, intervention_part)

        return time_of_day, data_type, intervention, spatial_mask

    cog_rows = []
    for _item in s3_root.findall("s3:Contents", ns):
        _key = _item.find("s3:Key", ns).text
        _size_bytes = int(_item.find("s3:Size", ns).text)
        _fname = _key.split("/")[-1].replace(".tif", "")
        _parts = _fname.split("__")
        _aoi = _parts[1] if len(_parts) > 1 else "?"
        _layer_id = _parts[2] if len(_parts) > 2 else "?"
        _time, _dtype, _intervention, _mask = _parse_layer_id(_layer_id)
        cog_rows.append({
            "aoi": _aoi,
            "layer_id": _layer_id,
            "time_of_day": _time,
            "data_type": _dtype,
            "intervention": _intervention,
            "spatial_mask": _mask,
            "size_mb": round(_size_bytes / 1_048_576, 1),
        })

    cog_df = pd.DataFrame(cog_rows)

    mo.vstack([
        mo.md(f"**{len(cog_df)} COG files** found for Cape Town in `data/dev/utci/cog/`"),
        mo.ui.table(cog_df, selection=None),
    ])
    return (cog_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 2.4 — What data themes do the COGs cover?
    """)
    return


@app.cell
def _(cog_df, mo):
    # Summarise the COG inventory along the meaningful dimensions
    by_data_type = cog_df.groupby("data_type").size().reset_index(name="count")
    by_intervention = cog_df.groupby("intervention").size().reset_index(name="count")
    by_time = cog_df.groupby("time_of_day").size().reset_index(name="count")

    # Check for any non-UTCI data themes (population, vulnerability, etc.)
    NON_UTCI_TERMS = ["pop", "vuln", "expos", "dens", "demog", "income", "health", "social"]
    has_non_utci = cog_df["layer_id"].str.lower().apply(
        lambda lid: any(t in lid for t in NON_UTCI_TERMS)
    ).any()

    mo.vstack([
        mo.md("**By data type** (baseline / scenario output / delta vs. baseline):"),
        mo.ui.table(by_data_type, selection=None),
        mo.md("**By intervention:**"),
        mo.ui.table(by_intervention, selection=None),
        mo.md("**By time of day:**"),
        mo.ui.table(by_time, selection=None),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 3 Assessment: Mapping data requirements vs what's available (in Cape Town)

    what exists for Cape Town, and at what granularity

    | Data need for Idea 1 | In scalar API? | As pixel-level COG? | Granularity verdict |
    |---|---|---|---|
    | Heat / thermal stress (UTCI baseline) | Yes — `mean_utci_*` stems | Yes — 63 COGs | **Pixel-level** ✓ |
    | Scenario cooling outcomes | Yes — `mean_utci_*_scenario_*` | Yes — multiple scenarios | **Pixel-level** ✓ |
    | `high_risk_utci_pct` (% area in high heat risk) | Yes — 3 keys | No COG found | **Scalar only** |
    | Population density | No | No | **Absent** |
    | Vulnerable population density | No | No | **Absent** |
    | Demographic / socioeconomic indicators | No | No | **Absent** |
    | Land use / public assets | No | No | **Absent** |

    **What Cape Town has:**
    - A rich set of UTCI thermal stress rasters at pixel resolution (1200, 1500, 1800 time-of-day),
      covering both baseline conditions and multiple intervention scenarios (cool roofs, street trees,
      park shade, combinations).
    - All COGs are for the `business_district` AOI, plus one `urban_extent` baseline.
    - These rasters are sufficient to answer "where in this area is heat stress highest?" and
      "where would intervention X reduce heat the most?"

    **What Cape Town does not have:**
    - Any population, vulnerability, demographic, or socioeconomic data — neither as scalars
      nor as pixel-level rasters.
    - Any land-use data (parks, schools, hospitals, roads).
    - Any "exposure" layer combining heat and population together.
    """)
    return


@app.cell
def _(mo, pd):
    # Priority mapping — hardcoded assessment
    # Section A: the four example priorities from the product concept
    # Section B: additional priorities the available data actually enables

    priorities = [
        # --- Section A: example priorities from the product concept ---
        {
            "section": "A — from product concept",
            "user_priority": "Reduce extreme heat exposure",
            "data_available": "UTCI baseline + scenario delta COGs",
            "granularity": "Pixel",
            "custom_aoi_viable": "Yes",
            "gap": "None",
        },
        {
            "section": "A — from product concept",
            "user_priority": "Protect vulnerable populations",
            "data_available": "high_risk_utci_pct scalar only",
            "granularity": "District",
            "custom_aoi_viable": "No",
            "gap": "Need population/vulnerability raster (e.g. WorldPop)",
        },
        {
            "section": "A — from product concept",
            "user_priority": "Increase tree canopy",
            "data_available": "tree_cover_* scalars only",
            "granularity": "District",
            "custom_aoi_viable": "No",
            "gap": "Need tree canopy raster (e.g. open canopy dataset)",
        },
        {
            "section": "A — from product concept",
            "user_priority": "Maximise impact per budget",
            "data_available": "Scenario delta COGs (impact side only)",
            "granularity": "Pixel (impact only)",
            "custom_aoi_viable": "Partial",
            "gap": "Cost data entirely absent — must be user-supplied",
        },
        # --- Section B: priorities the data actually enables ---
        {
            "section": "B — enabled by available data",
            "user_priority": "Where would street trees cool the most?",
            "data_available": "street_trees COG deltas (1200, 1500, 1800)",
            "granularity": "Pixel",
            "custom_aoi_viable": "Yes",
            "gap": "None",
        },
        {
            "section": "B — enabled by available data",
            "user_priority": "Where would cool roofs have the highest impact?",
            "data_available": "cool_roofs COG deltas (1200, 1500, 1800)",
            "granularity": "Pixel",
            "custom_aoi_viable": "Yes",
            "gap": "None",
        },
        {
            "section": "B — enabled by available data",
            "user_priority": "Where is heat stress worst at peak afternoon?",
            "data_available": "UTCI baseline COG at 1500",
            "granularity": "Pixel",
            "custom_aoi_viable": "Yes",
            "gap": "None",
        },
        {
            "section": "B — enabled by available data",
            "user_priority": "Which intervention cools the most in my selected area?",
            "data_available": "Delta COGs for street trees, cool roofs, park shade, combinations",
            "granularity": "Pixel",
            "custom_aoi_viable": "Yes",
            "gap": "Requires zonal stats over multiple COGs — computationally feasible",
        },
        {
            "section": "B — enabled by available data",
            "user_priority": "How does combined street trees + cool roofs compare to either alone?",
            "data_available": "street_trees_cool_roofs combined delta COGs exist",
            "granularity": "Pixel",
            "custom_aoi_viable": "Yes",
            "gap": "None",
        },
    ]

    priority_df = pd.DataFrame(priorities)

    mo.vstack([
        mo.md("### User priorities × data availability"),
        mo.md(
            "**Section A** maps the four example priorities from the product concept. "
            "**Section B** adds priorities that the available Cape Town data actually enables — "
            "framed as user goals the system could credibly support today."
        ),
        mo.ui.table(priority_df, selection=None),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### 3.2 Feasibility implications for Idea 1

    **The four example user priorities, assessed:**

    - **"Reduce extreme heat exposure"** — fully supported at pixel level. UTCI COGs exist for Cape
      Town. A user can draw any AOI and compute meaningful heat exposure statistics over it.

    - **"Protect vulnerable populations"** — only partially supported. `high_risk_utci_pct` exists
      as a scalar (one number per district), but there is no pixel-level vulnerability layer. The
      system can tell you *that* a district has X% high-risk area, but not *where within it*
      vulnerable people are concentrated. Custom AOI analysis is not meaningful without an
      external population or vulnerability raster (e.g. WorldPop, national census).

    - **"Increase tree canopy"** — scalar indicators exist (`tree_cover_*`) for district-level
      comparison, but no tree canopy COG. A user cannot draw a custom AOI and find where canopy
      is lowest. An external dataset would be needed (e.g. an open urban canopy layer).

    - **"Maximise impact per budget"** — the impact side is well supported: scenario delta COGs
      exist at pixel level for multiple interventions. The cost side is entirely absent from CCL
      — would require fully user-supplied cost assumptions.

    **What the data unlocks beyond the stated examples:**

    Section B of the table above identifies five additional user priorities that Cape Town's COG
    inventory *already* supports — all centred on comparing intervention cooling impacts spatially.
    These are strong candidates for an early prototype, since they require no external data and
    work at pixel resolution for any custom AOI.

    **Bottom line:**

    Idea 1 splits cleanly into two tiers:
    - **Tier 1 (buildable now):** Heat-exposure and intervention-impact prioritisation — fully
      supported by CCL COG data at pixel level.
    - **Tier 2 (needs external data):** Vulnerability- and equity-based prioritisation — requires
      augmenting CCL with population or socioeconomic rasters. Technically feasible with public
      datasets, but not a zero-effort addition.
    """)
    return


if __name__ == "__main__":
    app.run()
