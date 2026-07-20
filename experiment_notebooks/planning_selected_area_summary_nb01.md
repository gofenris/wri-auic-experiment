# Notebook: Selected Area Summary — nb01

## Purpose

Given a selected area in Cape Town, produce a plain-language summary of its
key heat-related characteristics. The summary is intended to give a user a
concise overview of an area's conditions before they explore the underlying
map layers in detail.

This is an experiment notebook, not an exploration. There are two concrete
experiment questions:

1. Can we assemble the right structured facts from CCL data for an arbitrary
   polygon — reliably and cheaply?
2. Can an LLM render those facts into a useful, faithful plain-language
   summary?
3. What should the summary object contain, and in what form?

Question 3 is the hardest and will require iteration. The summary object
schema is the critical design artifact of this notebook, not the LLM output.

This notebook is standalone. It does not extend nb4 and should not be read
as doing so.

---

## Section 1 — Area selection

**Target city:** Cape Town (`ZAF-Cape_Town`)

The notebook needs at least one polygon representing a recognisable,
named area in Cape Town to work with.

**Primary approach — public suburb polygons:**
Attempt to fetch the City of Cape Town's "Official Planning Suburbs"
shapefile from the City's Open Data Portal. This is public data and has been
used in other urban analysis work. If it loads cleanly and the polygons are
at a useful granularity, use it. One or more suburbs can be selected as the
target area(s) for the experiment.

**Fallback — hand-drawn polygon:**
If the public shapefile is unavailable or takes significant effort to locate,
define one or more polygons as inline GeoJSON over recognisable areas within
the `business_district` AOI extent (which is the coverage area of the
scenario COGs). This keeps the notebook unblocked. A proper neighbourhood
shapefile layer can be requested from the Cape Town team separately.

**Early check — AOI coverage:**
Scenario COGs (street trees, cool roofs, etc.) cover the `business_district`
AOI only. One `urban_extent` baseline also exists. A check cell early in the
notebook should confirm the selected polygon intersects the
`business_district` extent before proceeding to scenario fact extraction.
This constraint should be noted clearly — it is a data limitation, not a
notebook limitation.

---

## Section 2 — Fact extraction

For the selected polygon, compute zonal statistics over the relevant COGs.

**Baseline UTCI** (three times of day):
- `utci_1200_baseline` — morning peak
- `utci_1500_baseline` — afternoon peak (primary)
- `utci_1800_baseline` — evening

For each: mean, 90th percentile (p90), max.

**Scenario deltas** (cooling potential from each intervention):
- `street_trees` delta
- `cool_roofs` delta
- `park_shade` delta
- `street_trees_cool_roofs` combined delta

For each: mean UTCI reduction within the polygon.

The pattern for reading COGs follows nb2 and nb3: `rasterio.open()` via
`/vsicurl/` on the S3 URL, windowed reads clipped to the polygon bounding
box, masked with `rasterio.mask`. The COG inventory and S3 path structure
are documented in nb3.

**Reference for available facts:**
- nb1 confirms which scalar indicator stems exist in the API per AOI
- nb3 confirms which COG files exist in S3 for Cape Town and their naming
  convention (`data/dev/utci/cog/ZAF-Cape_Town/...`)

---

## Section 3 — Relative context

A number alone is not a characteristic. The summary needs relative framing
so the user understands whether the area is notably hot, average, or cool
relative to the rest of the city.

Two approaches, in increasing cost:

**3a — AOI scalar comparison (free):**
The API's `indicator_values` blob for Cape Town contains pre-aggregated
scalars (e.g. `mean_utci_1500_baseline`) for the `business_district` AOI.
Use these as a reference point: "the selected area's mean afternoon UTCI is
X, compared to the district-wide mean of Y."

**3b — Pixel-percentile placement (cheap):**
Read the baseline COG for the full AOI extent once. Compute the pixel-value
distribution (mean, std, percentiles). Place the selected area's mean and
p90 within that distribution: "hotter than ~85% of pixels in the district."
This requires one additional full-extent read but no polygon iteration.

**Deferred:** "Top X% of neighbourhoods" framing requires having polygon
stats for all neighbourhoods, which depends on having real neighbourhood
polygons. Note this in the notebook but do not implement it in nb01.

---

## Section 4 — Summary object

The summary object is the critical artifact. It is a structured JSON
document that captures everything needed to generate a plain-language
summary, and is saved to file for reproducibility and iteration.

**Schema (starting point — expect iteration):**

```json
{
  "identity": {
    "area_name": "...",
    "city": "ZAF-Cape_Town",
    "area_sqkm": ...,
    "geometry_source": "...",
    "aoi_coverage": "business_district"
  },
  "absolute_stats": {
    "utci_1200": {"mean": ..., "p90": ..., "max": ...},
    "utci_1500": {"mean": ..., "p90": ..., "max": ...},
    "utci_1800": {"mean": ..., "p90": ..., "max": ...}
  },
  "scenario_deltas": {
    "street_trees":            {"mean_reduction": ...},
    "cool_roofs":              {"mean_reduction": ...},
    "park_shade":              {"mean_reduction": ...},
    "street_trees_cool_roofs": {"mean_reduction": ...}
  },
  "relative_context": {
    "district_mean_utci_1500": ...,
    "area_vs_district_delta":  ...,
    "area_pixel_percentile_utci_1500": ...
  },
  "provenance": {
    "cog_urls_used": [...],
    "generated_at": "...",
    "notebook": "selected_area_summary_nb01"
  }
}
```

The schema will evolve as the LLM rendering experiments reveal what
information is actually useful in the prompt context. A notable-factor
field (flagging what is unusual about the area) may be added as a
separate key — whether this is computed by heuristic code or derived
from a first LLM call is an open design question (see Section 5).

**Output location:** `experiment_notebooks/outputs/`
File name: `summary_<area_name>_<YYYYMMDD>.json`
This folder is committed to the repo so summary versions are versioned.

---

## Section 5 — LLM rendering (experimental)

The LLM receives the summary object as context and renders a plain-language
summary. This section is deliberately open-ended — the right prompt
structure and context payload are unknown and will require iteration.

**Model:** Start with `claude-haiku-*`, then `claude-sonnet-*`.
**API key:** `ANTHROPIC_API_KEY` loaded from environment (set in
`mise.local.toml`, not committed).

**Prompt structure (starting point):**
A system prompt establishing the task (city climate analyst, plain-language
summary for a planner), followed by the summary object serialised as JSON
in the user message. The prompt should specify: avoid jargon, cite specific
numbers from the data, highlight what is most notable about the area, keep
it concise.

**Open design questions to explore in the notebook:**
- Is the full stats payload the right context, or should it be pre-filtered
  to notable facts before sending?
- Would a two-stage approach work better: LLM call 1 selects the two or
  three most notable facts from the full stats; LLM call 2 renders the
  narrative from those facts only?
- What is the token cost of the full summary object? Is it acceptable?
- Do heuristics in code (e.g. flag any stat above city p85) improve
  faithfulness by reducing hallucination surface, or do they constrain what
  the LLM notices?

**Outputs:** Save each model's rendered summary as a plain text file in
`experiment_notebooks/outputs/`. File name:
`summary_<area_name>_<model>_<YYYYMMDD>.txt`

Run models one at a time. No side-by-side comparison scaffolding.

---

## Assessment criteria

After generating each LLM output, evaluate qualitatively:

- **Faithfulness** — does the summary cite correct numbers from the summary
  object? Does it introduce any facts not in the data?
- **Usefulness** — does it highlight what is actually notable about the
  area, or does it give a generic tour of all statistics?
- **Length and tone** — is it concise enough to be read before exploring
  the map? Is the language appropriate for a city planner?

---

## Possible cell structure

| Section | Cell type | Content |
| ------- | --------- | ------- |
| 1 | `mo.md` | Purpose and experiment questions |
| 2 | code | Attempt to load public Cape Town suburb polygons; fallback to inline GeoJSON |
| 3 | code | Inspect selected polygon: name, area, map preview |
| 4 | code | AOI coverage check — confirm polygon intersects `business_district` extent |
| 5 | code | Fetch COG metadata for baseline and delta layers (pixel size, CRS, extent) |
| 6 | code | Zonal stats — baseline UTCI (1200, 1500, 1800) |
| 7 | code | Zonal stats — scenario deltas |
| 8 | code | Relative context — AOI scalar from API + pixel percentile from COG |
| 9 | code | Assemble summary object; save to `outputs/` as JSON |
| 10 | `mo.md` | Summary object design notes — what's in it and why; open questions on schema |
| 11 | code | LLM call — Haiku; display output; save to `outputs/` |
| 12 | code | LLM call — Sonnet; display output; save to `outputs/` |
| 13 | `mo.md` | Qualitative assessment — faithfulness, usefulness, tone |
| 14 | `mo.md` | Open questions and next steps |

---

## Dependencies

- `rasterio` — COG reads via `/vsicurl/` (pattern from nb2/nb3)
- `rasterstats` — zonal statistics over polygon/raster pairs
- `geopandas`, `shapely` — polygon handling
- `folium` — map preview of selected area
- `numpy`, `pandas` — standard
- `anthropic` — LLM API calls (new)
- `requests` — API scalar fetch (existing pattern from nb1)
