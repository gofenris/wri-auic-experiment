Notebook 2: Boundary files — Campinas

The API references boundary files stored on S3 as pmtiles and geojson. This
notebook fetches both formats for Campinas, inspects their structure, and
visualizes the AOI geometries to understand what spatial data is actually
available and how it relates to the indicator data in the API.

Objective: 
* Understand the boundary file formats, their content, and how AOIs are defined spatially.

Input: 
* Public S3 URLs for Campinas pmtiles and geojson, returned by the city API endpoint.
* GeoJSON: `https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/dev/boundaries/geojson/BRA-Campinas.geojson`
* PMTiles: `https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/dev/boundaries/pmtiles/BRA-Campinas.pmtiles`
* Both URLs are returned by the cities API under layers_url for Campinas — they follow the pattern `s3://wri-cities-data-api/data/dev/boundaries/{format}/{city_id}.{format}`

Credentials: 
* Credentials: unknown — to be verified by attempting an unauthenticated request before building the notebook


--- 

Context

This is notebook 2 of 3 exploring the Cool Cities Lab data infrastructure.
Notebook 1 established that the CCL API is primarily a map configuration
service — the `/cities` endpoint returns aggregated scalar indicators, while
`/layers` and `/scenarios` return display metadata pointing to COG rasters on
S3. The actual spatial data lives in S3.This notebook focuses on one city —
Campinas, Brazil (BRA-Campinas) — and attempts to retrieve, inspect, and
interpret its boundary files and spatial layers.

tips
* Use Altair for all charts (altair==6.1.0, pyarrow==24.0.0). No matplotlib.
* Use mo.ui.altair_chart(chart) to render Altair charts in Marimo.
* Use hide_code=True on all markdown cells.
* Use defaultdict from collections where needed, but prefix all loop variables with _ to avoid Marimo's multiple-definition errors (e.g. _city, _key, _parts). Run uvx marimo check before delivering.
* The notebook should present conclusions, not the process of discovery. Use markdown cells to state what was found; use code cells to produce the evidence. Avoid exploratory "let's try this" framing.
* Put an architecture/context overview and an open questions section at the top, before section 1. Update open questions based on what the notebook actually finds.

Campinas information from the /cities API response for BRA-Campinas:
* AOIs: accelerator_area, urban_extent
* Primary AOI with indicators: accelerator_area only
* Bounding boxes:
    * accelerator_area: [-47.20522, -22.97095, -47.18831, -22.95275]
    * urban_extent: [-47.43644, -23.11143, -46.93697, -22.68857]
* Boundary file URLs (access unknown — may require credentials):
    * GeoJSON: https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/dev/boundaries/geojson/BRA-Campinas.geojson
    * PMTiles: https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/dev/boundaries/pmtiles/BRA-Campinas.pmtiles

S3 path pattern for COG rasters:
* `s3://wri-cities-data-api/data/dev/{dataset}/cog/{city_id}__{aoi_id}__{layer_id}__{version}.tif`
* Simulation date: 19 March 2024
* aoi_area: 2.1 (units unknown — likely km²)

Possible Notebook goals
1. Test boundary file access
Attempt unauthenticated HTTP requests to the GeoJSON and PMTiles URLs. Record status codes. If access is denied (403), note that credentials are required and document what would be needed. If accessible, proceed.
2. Inspect and visualise the GeoJSON
If accessible: load the GeoJSON, inspect its structure (feature count, geometry types, properties), and plot the AOI boundaries. Confirm whether both accelerator_area and urban_extent are present as separate features or layers, and whether the geometry matches the bounding boxes from the API.
3. Inspect the PMTiles file
PMTiles is a single-file archive format for tiled map data. If accessible: fetch the file (or its header — it supports HTTP range requests), inspect the tile metadata (zoom levels, bounds, tile format), and document the structure. The goal is to understand whether PMTiles contains the same boundary data as the GeoJSON or something different.
4. Discover available COG layers for Campinas
Using the layer endpoint pattern established in notebook 1, probe a set of known layer IDs for Campinas to find which layers exist. Known layer ID stems from the indicator keys include: utci_1500_baseline, utci_1200_baseline, utci_1800_baseline, and scenario variants. Try BRA-Campinas as the city ID. Build a table of which layer IDs respond successfully.
5. Fetch and display layer metadata
For each accessible layer, retrieve and display the full metadata response from /layers/{layer_id}/BRA-Campinas — including colormap, legend title, file type, and source layer ID. This establishes the catalogue of available spatial layers and how to interpret them.
6. Document the S3 COG path structure
Based on what layer metadata returns, attempt to reconstruct the expected S3 paths for Campinas COG files. Document the naming pattern and note any version or AOI variants. If the bucket is publicly accessible (test with an unauthenticated request), fetch one COG header using HTTP range requests to confirm file structure without downloading the full raster.

Open Questions: 
* Are we able to access the boundary file S3 URLs? Are we able to access the COG files on S3? 
* Do the GeoJSON and PMTiles contain both AOIs (accelerator_area and urban_extent) or just one?
* What properties are attached to the boundary features — do they carry any metadata beyond geometry?
* What is the full set of layer IDs available for Campinas via the /layers endpoint?
* Are COG files on S3 publicly accessible without AWS credentials?
* What zoom levels and spatial resolution do the PMTiles cover?
