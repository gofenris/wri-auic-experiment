Notebook 1: CCL API explorer

The CCL REST API is the primary data interface for the Cool Cities Lab
product. This notebook explores what the API actually contains — which
cities have data, what indicators are available, how they're structured,
and where the gaps are.

Objective: 
* Understand the shape, coverage, and completeness of the API's city and indicator data.

Input: 
* Live HTTP requests to https://cities-data-api.wri.org
* GET `https://cities-data-api.wri.org/cities?application_id=ccl` — returns all cities with full indicator data
* GET `https://cities-data-api.wri.org/cities/{city_id}?application_id=ccl` — single city detail, e.g. ZAF-Cape_Town
* GET `https://cities-data-api.wri.org/layers/{layer_id}/{city_id}` — layer metadata and data, e.g. utci_1500_baseline/ZAF-Cape_Town (note: this endpoint timed out during exploration — availability uncertain)
* GET `https://cities-data-api.wri.org/scenarios/{city_id}/{aoi_id}/{scenario_id}` — scenario data, e.g. ZAF-Cape_Town/business_district/street_trees
* Full API docs at `https://cities-data-api.wri.org/docs`

Credentials: None required.
