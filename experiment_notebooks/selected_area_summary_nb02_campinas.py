# /// script
# dependencies = [
#     "marimo",
#     "pandas==3.0.3",
#     "requests==2.34.2",
# ]
# requires-python = ">=3.13"
# ///

import marimo

__generated_with = "0.23.14"
app = marimo.App(width="columns")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Selected Area Summary — Campinas Investigation (abandoned)

    **This notebook never actually did Campinas-specific work.** All cells below are an unmodified
    copy of `selected_area_summary_nb01_cape_town.py` (Ward 115, `ZAF-Cape_Town`, etc.) — it was
    duplicated to become the Campinas version of the experiment, but before any Campinas code was
    written here, we investigated whether switching cities made sense at all. That investigation
    (done via ad-hoc queries outside this notebook) is summarized in the conclusion cell at the
    bottom of this file.

    **Short version:** the switch didn't pan out. See the conclusion cell for why. The active
    notebook going forward is `selected_area_summary_nb01_cape_town.py`.

    Original goals (carried over from the Cape Town copy, kept for context):
    * Using various available indicators, generate a statistical comparison between a selected neighborhood and the city as a whole.
    * Summarize the statistical comparison
    * Generate an natural language summary
    * Use an LLM model query via API to generate a simple "insight" commensurate with the "selected Area summary" AI feature concept by Usertopia, to fit within the wireframe
    """)
    return


@app.cell
def _():
    import marimo as mo
    import re

    import requests
    import pandas as pd

    return mo, pd, re, requests


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Indicators (Campinas)

    Reference only — see the conclusion cell at the bottom of this notebook. This section shows
    what the Campinas indicator/COG inventory looks like; the rest of the notebook below still
    operates on Cape Town data and was not updated to match.
    """)
    return


@app.cell(hide_code=True)
def _(mo, pd, re, requests):
    CITY_ID = "BRA-Campinas"
    BASE_URL = "https://cities-data-api.wri.org"
    S3_BASE = "https://wri-cities-data-api.s3.us-east-1.amazonaws.com"
    COG_PREFIX = "data/dev/utci/cog/BRA-Campinas"

    # --- Scalar indicators from the API ---
    _resp = requests.get(f"{BASE_URL}/cities?application_id=ccl", timeout=15)
    _all_cities = _resp.json()["cities"]
    campinas = next(c for c in _all_cities if c.get("id") == CITY_ID)

    indicator_values = campinas.get("indicator_values", {})
    aoi_types = list(indicator_values.keys())

    _flat_keys = []
    for _aoi, _vals in indicator_values.items():
        for _k in _vals.keys():
            _flat_keys.append(_k)

    def _extract_stem(indicator_key):
        parts = re.split(r"__BRA-", indicator_key)
        return parts[0]

    indicator_stems = sorted(set(_extract_stem(k) for k in _flat_keys))

    # --- COG inventory from S3 ---
    import xml.etree.ElementTree as ET

    _s3_resp = requests.get(f"{S3_BASE}/?prefix={COG_PREFIX}", timeout=15)
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
        ### Campinas data inventory

        - **{len(_flat_keys)} scalar indicator values** across AOI types: `{"`, `".join(aoi_types)}`
        - **{len(indicator_stems)} unique scalar metric stems**
        - **{len(cog_df)} COG raster files** under `{COG_PREFIX}`
        """),
        mo.md("**Scalar indicator stems:**"),
        mo.ui.table(pd.DataFrame({"stem": indicator_stems}), selection=None, page_size=15),
        mo.md("**COG inventory:**"),
        mo.ui.table(cog_df, selection=None, page_size=15),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Selected Neighborhood — Campinas Investigation Summary

    We looked for a real Campinas neighbourhood polygon that nests **inside** the WRI
    `accelerator_area` AOI (~2.34 km²), so zonal stats could be computed without a partial-coverage
    caveat. Two data sources were tried; neither worked.

    **1. SP state bairros geopackage (`data/campinas/SP_bairros_CD2022.gpkg`)**
    A São Paulo state-wide bairros dataset, 2,235 features across 58 municipalities. **Campinas
    (município code `3509502`) is not one of the 58 municipalities in the file at all** — unusable
    outright, before any containment question even arises.

    **2. Official Campinas UTB/UTR planning units**
    Source: [Prefeitura Municipal de Campinas ArcGIS FeatureServer](https://services5.arcgis.com/dFCi4j751Fk5jtHP/ArcGIS/rest/services/PMC_UTB_UTR/FeatureServer)
    — 93 real, named territorial units: 75 **UTB** (Unidade Territorial Básica — fine-grained, used
    city-wide for census/socioeconomic reporting) + 18 **UTR** (Unidade Territorial de Referência —
    coarser, filling in peripheral/rural zones where UTBs aren't drawn).

    We found the `accelerator_area` AOI sits **100% inside UTB `EU-35` — "Pq. Valença / Pq. Itajaí"**
    (~12.5 km²). That's the wrong containment direction: we need a neighbourhood *smaller than and
    nested inside* the 2.34 km² AOI, not a neighbourhood the AOI is a small piece of. No official
    Campinas planning unit was small enough to fit inside `accelerator_area`.

    **Conclusion:** neither source produced a usable "neighbourhood inside AOI" polygon for Campinas.
    This was one of the findings that led to reverting to Cape Town — see the conclusion cell at the
    bottom of this notebook.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Conclusion — Reverting to Cape Town

    **We explored switching this experiment to Campinas, on the assumption that it had better COG
    indicator coverage than Cape Town. After investigation, that assumption did not hold up, and we
    are reverting to Cape Town.**

    ### What we tried

    1. **Campinas neighbourhood data, attempt 1 — SP state bairros file (`SP_bairros_CD2022.gpkg`).**
       Covers 2,235 bairros across 58 São Paulo municipalities — but **Campinas itself is not one of
       the 58 municipalities in the file**. Unusable.

    2. **Campinas neighbourhood data, attempt 2 — City of Campinas UTB/UTR planning units** (official
       `Prefeitura Municipal de Campinas` ArcGIS FeatureServer, 93 real named units). This data is
       good, but exposed the real problem: the CCL `accelerator_area` AOI (~2.3 km², informally named
       "Jardim Bassoli" in the API) sits **entirely inside one UTB — "Pq. Valença / Pq. Itajaí"
       (12.5 km²)**. No official Campinas planning unit is small enough to nest *inside* the AOI —
       it's the AOI that nests inside the neighbourhood, the wrong direction for computing
       whole-neighbourhood stats without clipping caveats.

    3. **Re-checked Cape Town's containment problem for comparison.** Confirmed that `business_district`
       is **literally identical** (99.9999% IoU) to the official suburb polygon "CAPE TOWN CITY CENTRE"
       — it's not a subset of a suburb, it *is* one, at the finest granularity that dataset offers. So
       Cape Town has the exact same structural problem as Campinas: the data-rich AOI is smaller than
       the finest publicly available administrative/planning unit.

    4. **Corrected the original premise for switching.** Direct inspection of `business_district`'s COG
       inventory shows **62 files** — full baseline (1200/1500/1800) *and* full scenario deltas (street
       trees, cool roofs, park shade, combined, plus masked variants), compared to Campinas'
       `accelerator_area` with only **10 files**, covering a single time of day (1500) with fewer
       scenario variants. Cape Town was never the worse-covered city — that assumption was wrong.

    5. **Checked all 16 cities in the COG bucket** by actual raster footprint (valid-pixel area, not
       just bounding box) to see if any other city solved both problems (data richness + clean
       containment). Excluding two single-file outlier cities (Chengdu, Hermosillo — huge whole-city
       baseline raster, zero scenario data, unusable for this notebook), **Cape Town has both the
       largest useful footprint (571 km² whole-city baseline) and the richest scenario file count (63)
       of any city in the bucket.** Rio de Janeiro came closest to solving containment (`Centro` bairro
       covers 90.8% of the `low_emission_zone` AOI) but still didn't achieve full containment either
       way.

    ### Conclusion

    The neighbourhood-vs-AOI containment mismatch is **not a Cape-Town-specific problem** — it appears
    to be structural across the CCL cities we checked. Cape Town remains the best-covered city in the
    dataset by a wide margin. **We are reverting to `selected_area_summary_nb01_cape_town.py`** and will
    solve the containment problem there directly — either via a finer official geography (e.g. Stats SA
    Small Area Layers) or hand-drawn sub-polygons within `business_district`, per the original nb01 plan.

    This Campinas copy is kept for reference but is not the active notebook going forward.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Appendix — Additional Campinas / cross-city notes (for posterity)

    Supporting detail behind the conclusion above, captured here since it doesn't live anywhere
    else in the repo.

    ### Cross-city COG footprint comparison

    Ranked by largest single-raster valid-pixel footprint (not just bounding box) across all 16
    cities in the `data/dev/utci/cog/` S3 bucket:

    | City               | Max footprint (km²) | Total COG files | Note                                              |
    |--------------------|---------------------:|------------------:|----------------------------------------------------|
    | CHN-Chengdu        | 729.1                | 1                | Single whole-city baseline raster — no scenarios   |
    | **ZAF-Cape_Town**  | **571.1**             | **63**            | Whole-city baseline + full scenario suite           |
    | MEX-Hermosillo     | 146.8                | 1                | Single whole-city baseline raster — no scenarios   |
    | ARG-Buenos_Aires   | 21.3                 | 12               |                                                    |
    | ZAF-Durban         | 16.9                  | 9                |                                                    |
    | BRA-Teresina       | 12.4                  | 14               |                                                    |
    | MEX-Monterrey      | 7.7                   | 57               | Rich scenario data, but AOI itself is small        |
    | BRA-Fortaleza      | 5.8                   | 9                |                                                    |
    | BRA-Florianopolis  | 4.0                   | 10               |                                                    |
    | BRA-Recife         | 3.8                   | 9                |                                                    |
    | BRA-Rio_de_Janeiro | 2.4                   | 46               |                                                    |
    | USA-Boston         | 2.2                   | 3                |                                                    |
    | BRA-Campinas       | 2.2                   | 12               |                                                    |
    | ZAF-Johannesburg   | 1.8                   | 46               |                                                    |
    | IND-Bhopal         | 1.7                   | 21               |                                                    |

    Chengdu and Hermosillo top the raw footprint ranking but each have exactly **1 COG file** — a
    single whole-city baseline raster with no scenario/intervention layers — so they can't support
    this notebook's core need (scenario deltas). Excluding those two, Cape Town is the clear leader
    on both dimensions (footprint and file richness).

    ### Rio de Janeiro — closest near-miss on containment

    Rio's `low_emission_zone` AOI is officially named **"Distrito de Baixa Emissão do Centro"**
    (~2.34 km²). Rio publishes 165 ADM3-level bairros (ADM3 = ~Brazil's neighbourhood level, the
    finest we found in any city's boundary GeoJSON). Checking containment against the AOI:

    | Bairro   | Area (km²) | % of AOI covered | % of bairro inside AOI |
    |----------|-----------:|------------------:|-------------------------:|
    | Centro   | 5.37       | 90.8%             | 39.5%                    |
    | Lapa     | 0.34       | 8.0%              | 54.0%                    |
    | Glória   | 1.14       | 1.2%              | 2.6%                     |

    Centro alone covers 90.8% of the AOI; Centro + Lapa combined ≈ 98.8%. Still not full
    containment either direction, but by far the closest of any city checked. Worth revisiting if
    Cape Town's containment problem turns out to be unsolvable.

    ### Two gotchas from the Campinas UTB/UTR investigation

    - **The "Centro" naming trap:** UTB `EU-26` is literally named "Centro" and it's tempting to
      assume it's the neighbourhood containing `accelerator_area` — it is not. `EU-26`'s bounds are
      centered around 15 km away from `accelerator_area`'s actual location. The correct containing
      unit is `EU-35` — "Pq. Valença / Pq. Itajaí".
    - **API identity mismatch:** the CCL API's own `geo_name` for the `accelerator_area` feature is
      `"Macroarea Jardim Bassoli"` — a third name, distinct from both "Centro" and "Pq. Valença / Pq.
      Itajaí". Anyone cross-referencing the API directly should expect this name, not a UTB name.
    """)
    return


if __name__ == "__main__":
    app.run()
