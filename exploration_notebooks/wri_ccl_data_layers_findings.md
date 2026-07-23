# WRI Cool Cities Lab (CCL) — Data Layers Findings

**Date:** 2026-07-22
**Context:** Discovered while working on `experiment_notebooks/selected_area_summary_nb01_cape_town.py`
(the "hack custom neighborhoods" section), when trying to source data for a "selected area summary"
concept needing: land surface temperature, thermal stress, tree canopy cover, vulnerable population,
and days-above-threshold indicators.

## The core finding

**Prior notebooks concluded that population, vulnerability, and tree-canopy raster data were absent
for Cape Town (and implicitly for other cities). That conclusion is wrong.** It was based on querying
only the narrow `data/dev/utci/cog/<CITY_ID>/` S3 prefix. The WRI `wri-cities-data-api` S3 bucket has
**116 top-level data folders** under `data/dev/` — UTCI is just one of them. Real rasters exist for
land surface temperature, tree canopy cover, and population (including age/sex-disaggregated
subgroups), among many other layers.

Notebooks affected (see "Notebooks needing correction" below): `nb3_idea1_cape_town.py` and
`nb2_boundary_files.py`.

## General method: how to discover available layers for any city

The bucket is publicly listable over plain HTTPS (S3 `ListObjectsV2` XML API, no auth needed):

**1. List all top-level layer families:**
```
GET https://wri-cities-data-api.s3.us-east-1.amazonaws.com/?list-type=2&prefix=data/dev/&delimiter=/
```
Returns `<CommonPrefixes>` entries like `data/dev/LandSurfaceTemperature/`, `data/dev/tree_cover/`,
`data/dev/WorldPop/`, etc. (116 as of this writing — see full list in the appendix below).

**2. Check whether a specific city has files in a given family:**
```
GET https://wri-cities-data-api.s3.us-east-1.amazonaws.com/?list-type=2&prefix=data/dev/<LayerFamily>/cog/<CITY_ID>
```
e.g. `prefix=data/dev/LandSurfaceTemperature/cog/ZAF-Cape_Town` — folder existing at the top level
does **not** guarantee a given city has data in it; always check per-city.

**3. File naming pattern** (varies slightly by family/vintage, but generally):
```
<CITY_ID>__<aoi_scope>__<LayerName>__<params>.tif
```
- `aoi_scope` is usually `business_district` or `urban_extent` for Cape Town, but can be an
  admin-boundary code for other cities (e.g. `ADM2union`, `ADM3`, `barrio_20`, `city`).
- `<params>` varies by layer: year ranges (`StartYear_2013_EndYear_2022`), version tags
  (`Version_2`), or just a single year.
- Do not rely on the `/layers/{layer_id}/{city_id}` REST API alone to discover COGs — both nb2 and
  nb3 found it unreliable/incomplete for scenario layers (empty stubs, malformed URLs). The S3 listing
  is the reliable source of truth for "does this COG exist."

**4. Cross-reference human-readable descriptions:**
https://coolcities.wri.org/data-and-methods lists every layer with a plain-language description and
a "Read more details" link per layer. This is useful for disambiguating similarly-named layers — e.g.
it clarifies that `utci_*_achievable` layers are literally **"UTCI (Scenario)"** (a post-intervention
thermal comfort value), not an opportunity/suitability index — see "Known open questions" below.

## Cape Town specifics — what's actually available

Confirmed via direct S3 listing against `ZAF-Cape_Town` on 2026-07-22:

| Indicator concept | Family (S3 folder) | AOI scope found | Example key(s) |
|---|---|---|---|
| Thermal stress (UTCI) | `utci/` | `business_district` (63 files) + `urban_extent` (1 file) | `utci/cog/ZAF-Cape_Town__business_district__utci_1500_baseline__2023.tif` |
| Land surface temperature | `LandSurfaceTemperature/` | `business_district` **and** `urban_extent` | `LandSurfaceTemperature/cog/ZAF-Cape_Town__business_district__LandSurfaceTemperature__StartYear_2013_EndYear_2022.tif` |
| High land surface temperature (index) | `HighLandSurfaceTemperature/` | `urban_extent` only (8 files, multiple date ranges/normalized variants) | `HighLandSurfaceTemperature/cog/ZAF-Cape_Town__urban_extent__HighLandSurfaceTemperatureIndex__2026.tif` |
| Tree canopy cover | `tree_cover/` | `business_district` (baseline + achievable, plain + pedestrian-masked) | `tree_cover/cog/ZAF-Cape_Town__business_district__tree_cover_baseline__2024.tif`, `..._baseline_pedestrian_areas`, `..._achievable`, `..._achievable_pedestrian_areas` |
| Tree canopy cover (alt/older method) | `TreeCanopyCoverMask/` | `urban_extent` only, 2020 vintage | `TreeCanopyCoverMask/cog/ZAF-Cape_Town__urban_extent__TreeCanopyCoverMask__2020.tif` (+ `Index`, `_100m`, `Percent` variants) |
| Population (general) | `WorldPop/` | `business_district` **and** `urban_extent` | `WorldPop/cog/ZAF-Cape_Town__business_district__WorldPop__StartYear_2020_EndYear_2020.tif` |
| Population — elderly | `WorldPop__AgesexClasses_ELDERLY/` | `urban_extent` **only** | `.../ZAF-Cape_Town__urban_extent__WorldPop__AgesexClasses_ELDERLY__StartYear_2020_EndYear_2020.tif` (+ `Version_2`) |
| Population — young children (0-4) | `WorldPop__AgesexClasses_YOUNG_CHILDREN/` | `urban_extent` **only** | `.../ZAF-Cape_Town__urban_extent__WorldPop__AgesexClasses_YOUNG_CHILDREN__Version_2__StartYear_2020_EndYear_2020.tif` |
| Population — children | `WorldPop__AgesexClasses_CHILDREN/` | `urban_extent` **only** | similar pattern |
| Population — female | `WorldPop__AgesexClasses_FEMALE/` | `urban_extent` **only** | similar pattern |
| Population — adult | `WorldPop__AgesexClasses_ADULT/` | **not found for Cape Town** | — |
| Cool roof opportunity (real opportunity index) | `cool_roof_opportunity/` | `business_district` **and** `urban_extent` | `cool_roof_opportunity/cog/ZAF-Cape_Town__business_district__cool_roof_opportunity__2025.tif` |
| Tree opportunity (real opportunity index) | `tree_opportunity/` | `business_district` **and** `urban_extent` | `tree_opportunity/cog/ZAF-Cape_Town__business_district__tree_opportunity__2025.tif` |
| Cool roof opportunity (normalized/all-roofs variant) | `opportunity__cool-roofs__all-roofs/` | `urban_extent` only | `.../ZAF-Cape_Town__urban_extent__opportunity__cool-roofs__all-roofs__2026.tif` |
| Tree opportunity (normalized/all-plantable variant) | `opportunity__trees__all-plantable/` | `urban_extent` only | `.../ZAF-Cape_Town__urban_extent__opportunity__trees__all-plantable__2026.tif` |
| Composite general heat risk index | `HeatRiskIndexGeneral/` | `urban_extent` only | `.../ZAF-Cape_Town__urban_extent__HeatRiskIndexGeneral__2026.tif` (+ `...Cadu` variant) |
| Composite cool-roof heat risk index | `HeatRiskIndexCoolRoof/` | `urban_extent` only | `.../ZAF-Cape_Town__urban_extent__HeatRiskIndexCoolRoof__2026.tif` |
| Composite tree heat risk index | `HeatRiskIndexTree/` | `urban_extent` only | `.../ZAF-Cape_Town__urban_extent__HeatRiskIndexTree__2026.tif` |
| Days above 32°C / year (or any annual threshold count) | — | **confirmed absent** | No "day count," "degree day," or annual-threshold folder anywhere among the 116 top-level families. The underlying data is static/simulated snapshots, not a time series — this metric isn't derivable from this dataset at all. |

**Practical implication:** since `urban_extent` covers the whole city (including the CBD), a
population/heat-risk-index layer only existing at `urban_extent` scope is *still usable* for a small
custom AOI inside `business_district` — just zonal-stat the `urban_extent` COG clipped to the smaller
polygon (same pattern already used for the ward-based / custom-zone UTCI baseline stats elsewhere in
nb01, which also only has one `urban_extent`-scope file).

## Known open questions / anomalies (not resolved — flagging for follow-up)

- **`utci_1500_cool_roofs_achievable` / `utci_1500_street_trees_achievable` pixel value ranges look
  implausible** as straightforward "post-intervention UTCI over the same footprint as baseline":
  baseline business_district UTCI-1500 sampled mean/p90/max ≈ 40.8 / 43.5 / 45.9, while
  `cool_roofs_achievable` sampled mean/p90/max ≈ 24.1 / 26.3 / 26.4 — a much narrower band, ~17
  degrees lower than baseline, which is far more than a cool-roof intervention should plausibly
  produce. The paired `_vs_baseline` delta layer's mean (-0.10) doesn't reconcile with the raw
  difference of the two means either (~-16.7 expected vs. -0.10 actual), suggesting `_vs_baseline` is
  computed against a different/local baseline subset, not the same one we sampled. Bounding boxes for
  all these COGs cover essentially the same `business_district` extent (not a small clipped region),
  so it isn't simply "cropped to a small area" — the discrepancy is still unexplained. This is
  separate from the opportunity-index naming question below.
- Per WRI's own site (coolcities.wri.org/data-and-methods), `utci_*_achievable`-style layers are
  labeled **"UTCI (Scenario)"** — a plain post-intervention thermal comfort value — not an opportunity
  index. The genuine opportunity-index concept exists as separate layers: `cool_roof_opportunity`,
  `tree_opportunity`, `opportunity__cool-roofs__all-roofs`, `opportunity__trees__all-plantable`, and
  the composite `HeatRiskIndex*` layers.
- `nb1_CCL-API-inspect.py` independently flagged other implausible values in this same dataset
  (`achievable_cool_roof_reflectivity` for Recife = 1915, not a plausible 0–100 reflectivity value;
  `tree_cover_progress` for Bhopal = -64%). Worth treating as corroborating evidence that this
  pipeline has known data-quality quirks in its "achievable"/scenario outputs specifically, not just a
  one-off oddity found here.

## Notebooks needing correction

- **`exploration_notebooks/nb3_idea1_cape_town.py`** — Section "3 Assessment: Mapping data
  requirements vs what's available" (the table around line 369, and the priority-mapping cells
  following it) states population, vulnerable-population, and demographic/socioeconomic data are
  "Absent," and that tree canopy is "scalar only" with no COG. Both claims are incorrect per the
  findings above — real rasters exist for all three (population/vulnerability via `WorldPop*`, tree
  canopy via `tree_cover/`), just not visible because only the `utci/` prefix was queried.
- **`exploration_notebooks/nb2_boundary_files.py`** — Section 3 ("COG Data") frames the S3 bucket as
  effectively only containing UTCI COGs ("the third format in the CCL data pipeline — they carry the
  pixel-level UTCI... outputs") and the section 3.1/3.2 discovery process only ever queries
  `data/dev/utci/cog/`. This should be corrected/expanded to reflect the much larger set of layer
  families available in the bucket, using the general discovery method documented above.
- Possibly **`exploration_notebooks/planning_nb4.md`** — references "vulnerable population density"
  as an example of a data gap; worth revisiting in light of the WorldPop findings.

## Appendix: full list of top-level `data/dev/` families (116, as of 2026-07-22)

```
AT-1500__baseline/                                  AT-1500__trees/
AT-change-1500__trees/                               AcagPM2p5/
AccessibleRegion/                                    AirTemperature/
Albedo/                                               AlbedoCloudMaskedIndex/
AlbedoCloudMaskedIndexNormalized/                    AlbedoCloudMaskedIndexPercent/
AlbedoCloudMasked__ZonalStats_median/                AlbedoCloudMasked__ZonalStats_median__NumSeasons_3/
AqueductFlood/                                       CarbonFluxFromTrees/
EsaWorldCover/                                       FractionalVegetationPercent/
FractionalVegetationPercentIndex/                    FractionalVegetationPercentIndexNormalized/
HeatRiskIndexCoolRoof/                               HeatRiskIndexGeneral/
HeatRiskIndexTree/                                   HeightAboveNearestDrainage__RiverHead_1000/
HighLandSurfaceTemperature/                          HighLandSurfaceTemperatureIndex/
HighLandSurfaceTemperatureIndexNormalized/           ImperviousSurface/
LandSurfaceTemperature/                              NaturalAreas/
NdviSentinel2/                                       NdwiSentinel2/
OpenStreetMap/                                       OpenStreetMapAmenityCountIndex/
OpenStreetMapAmenityCountIndexNormalized/            OpenStreetMapAmenityCount__OsmClass_ECONOMIC/
OpenStreetMap__OsmClass_HOSPITAL/                    OpenStreetMap__OsmClass_HOSPITALS/
OpenStreetMap__OsmClass_OPEN_SPACE/                  OpenUrban/
ProtectedAreas/                                      TreeCanopyCoverMask/
TreeCanopyCoverMaskIndex/                            TreeCanopyCoverMaskIndexNormalized/
TreeCanopyHeight/                                    UrbanExtents/
UrbanLandUse/                                        UrbanLandUse__Band_lulc/
WorldPop/                                             WorldPopIndexChildrenNormalized/
WorldPopIndexElderlyNormalized/                      WorldPopIndexNormalized/
WorldPop__AgesexClasses_CHILDREN/                    WorldPop__AgesexClasses_ELDERLY/
WorldPop__AgesexClasses_FEMALE/                      WorldPop__AgesexClasses_YOUNG_CHILDREN/
albedo/                                               aoi/
aqueduct_flood/                                       arthropod_species/
bird_species/                                         boundaries/
buildings/                                            cool_roof_opportunity/
distance_nearest_cooling_centers/                    distance_nearest_medical_facilities/
esa_world_cover_2020/                                esa_world_cover_builtup_areas/
esa_world_cover_natural_areas/                       forest_carbon_flux/
glad_lulc/                                            glad_lulc_2000/
glad_lulc_2020/                                       glad_lulc_habitat_change_2000_2020/
global_hand_1m/                                       imgs/
impervious_surfaces/                                  indicators/
kba/                                                   land_surface_temperature_high/
ndvi/                                                  new-tree-points/
open_space/                                            opportunity__cool-roofs__all-roofs/
opportunity__cool-roofs__all-roofs__normalized/      opportunity__trees__all-plantable/
opportunity__trees__all-plantable__normalized/       parks/
parks__baseline__baseline/                           parks__shade-structures/
parks_shade_structures/                               pedestrian-areas__baseline__baseline/
pedestrian_areas/                                     pedestrian_roads/
plant_species/                                        plantable_areas/
pm25/                                                  riparian/
roads/                                                 shade-distance/
shade/                                                 street_trees_achievable_height/
structures__shade-structures/                        structures__shade-structures__all-parks/
temperature/                                          test_tagging/
tree-canopy_baseline/                                tree-canopy_change/
tree-canopy_scenario/                                tree-cover__baseline__baseline/
tree_cover/                                            tree_opportunity/
tree_opportunity_class/                              utci-1500__baseline__baseline/
utci/                                                  wdpa/
world_pop/
```

Note: several of these are "empty" or near-empty for most cities, or are older/duplicate naming
conventions superseded by newer ones (e.g. `tree-canopy_baseline/` vs. `tree_cover/`, `world_pop/` vs.
`WorldPop/`) — always verify per-city with the discovery method above rather than assuming a folder's
existence means data is present for a given city.
