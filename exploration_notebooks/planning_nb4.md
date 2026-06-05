# Notebook 4: Algorithmic Feasibility of Idea 1 — Priority Area Search

## Purpose

Idea 1 proposes a system that takes a user's stated goal and surfaces the
highest-priority intervention areas on a map. nb3 confirmed that the data
exists at the right granularity (pixel-level UTCI COGs) for heat-exposure-based
prioritisation. This notebook asks the next question: is the *algorithm*
feasible? Can we show — concretely, with Cape Town's data — that the search
problem is solvable at reasonable computational cost and with interpretable
results?

This is a feasibility notebook, not a prototype. The goal is to show we
*could* build this, not to build it.

---

## Section 1 — The search problem

Idea 1 is not a lookup tool. The user does not select an area and ask what the
data says about it. The flow runs in the opposite direction:

1. User states a priority goal — e.g. "reduce extreme heat exposure" or
   "maximise cooling impact from street trees"
2. System identifies which areas of the city best satisfy that goal
3. System surfaces those areas on the map with a justification

This is a **spatial search and ranking problem** over a continuous raster
surface. The difficulty scales with the number of candidate units, the number
of scoring variables, and whether the user's objectives conflict with each
other.

Algorithmically, the problem has two stages:

**Stage 1 — Define and score candidate spatial units**

Decompose the city into candidate areas, then score each area against the
user's goal using zonal statistics over the relevant COG. This stage is mostly
solved once the decomposition choice is made.

**Stage 2 — Search and select over scored units**

This is where most of the difficulty lives.

- **2a — Combining variables:** If the user's goal involves multiple indicators
  (e.g. heat exposure *and* vulnerable population density), scores must be
  combined — typically via weighted linear combination, with normalisation
  choices that affect results.
- **2b — Ranking and selection:** If candidate units are scored independently
  and the goal is simply to find the top N, this reduces to a sort. No
  optimisation required. This is the happy path and likely sufficient for the
  initial product scope.
- **2c — Conflicting objectives:** If goals genuinely trade off (cool the most
  people vs. cool the hottest spot vs. cheapest intervention), the problem
  becomes multi-objective. The simplest viable approach is Pareto ranking or a
  weighted sum with user-controlled weights. This notebook will frame the
  problem but not implement a solution.

---

## Section 2 — Approach and design choices

### Spatial decomposition

The main families of spatial decomposition are:

- **Fixed grid / fishnet** — regular square cells. Simple, no prior knowledge
  needed. Arbitrary units with no inherent meaning.
- **Hierarchical indexed grids** — H3 hexagons, S2, geohash. Equal-area cells,
  built-in multi-resolution, easy neighbour lookups. "Let the user change
  granularity" falls out for free.
- **Object-based image analysis (OBIA)** — segment the raster into
  contiguous, internally-homogeneous regions, then score the segments. Units
  follow the actual spatial morphology rather than an arbitrary grid. However,
  segmenting on the heat field alone produces units that are not interpretable
  or actionable. The right approach is driver-segmentation: segment on
  underlying morphology (building footprints, land use, land cover) and
  attribute the UTCI outputs onto those objects. This requires additional data
  beyond the CCL COGs.
- **Pre-existing polygons** — districts, census blocks, named neighbourhoods.
  Interpretable and immediately meaningful to city planners. Requires no
  decomposition step.

**Recommended starting point: pre-segmented neighbourhood polygons from public
maps.** Named neighbourhoods (available via OpenStreetMap) sidestep the
decomposition problem entirely and allow the notebook to jump straight to Stage
2. The units mean something — "Woodstock" or "Observatory" — which makes the
justification layer natural. This is the approach this notebook should explore
first.

### Confirming the approach is viable

Before scoring, two empirical checks are needed:

1. **Neighbourhood polygon availability** — confirm that Cape Town has usable
   neighbourhood polygon data in OSM (via `osmnx` or the Overpass API) at an
   appropriate granularity. Too coarse (7 districts) and the ranking is
   uninformative. Too fine (individual parcels) and zonal stats become noisy.

2. **COG resolution check** — confirm that the UTCI COG pixel size is small
   enough relative to the chosen neighbourhood units that zonal statistics are
   meaningful. A neighbourhood containing only a handful of pixels would produce
   unreliable scores. Fetch COG metadata (pixel size, dimensions, CRS, extent)
   and compare against typical Cape Town neighbourhood areas.

### Scoring

For a single goal, scoring is zonal statistics of the relevant COG over each
neighbourhood polygon — mean or 90th percentile UTCI within the polygon.
Switching goals is just swapping the COG and re-running the same pipeline:

- "Reduce extreme heat exposure" → baseline UTCI 1500 COG, score by mean or p90
- "Maximise cooling impact from street trees" → street trees delta COG, score
  by mean UTCI reduction

The notebook should demonstrate both, to show the goal-switching is
structurally trivial once the pipeline exists.

### Selection

For the single-objective case, independent ranking suffices: sort neighbourhoods
by score, take top N. No optimisation needed. The notebook should note where
this breaks down — overlapping budget constraints, minimum contiguous area
requirements, equity side-constraints — and what would be needed to handle
those cases.

### Justification and interpretation

For a top-ranked neighbourhood, the system should be able to produce a
statement like: "This area ranks first because its mean afternoon UTCI is X,
which places it in the top Y% of the city, and the street trees + cool roofs
scenario would reduce it by Z degrees." This is the AI layer — the data
pipeline produces the numbers, an LLM wraps them in a sentence. The notebook
should show what the input to that LLM call would look like (i.e. the
structured data dict for the top result), even if it does not make the LLM
call itself.

---

## Possible cell structure

The following is one way to structure the notebook — treat it as a starting
point, not a requirement.

| Section | Cell type | Content                                                                          |
| ------- | --------- | -------------------------------------------------------------------------------- |
| 1       | `mo.md`   | The search problem — plain language outline                                      |
| 2       | `mo.md`   | Approach overview — decomposition, scoring, selection                            |
| 3       | code      | Fetch Cape Town neighbourhood polygons (OSM via `osmnx` or Overpass)            |
| 4       | code      | Inspect polygon count, size distribution, map preview                            |
| 5       | code      | Fetch COG metadata — pixel size, dimensions, CRS, extent                        |
| 6       | code      | Resolution check — pixels per neighbourhood (median, min)                       |
| 7       | code      | Zonal stats — score each neighbourhood on baseline UTCI                         |
| 8       | code      | Zonal stats — score each neighbourhood on a delta COG                           |
| 9       | code      | Rank and display top N neighbourhoods (table + map)                             |
| 10      | `mo.md`   | What Stage 2b/2c would require — why independent ranking likely suffices here   |
| 11      | `mo.md`   | Interpretation layer — what the structured input to an LLM justification looks like |
| 12      | `mo.md`   | Summary: what this shows about Idea 1 feasibility                               |

## Dependencies

- `osmnx` — fetching OSM neighbourhood polygons (new)
- `rasterstats` — zonal statistics over polygon/raster pairs (new)
- `rasterio` — COG metadata and windowed reads (already in nb2)
- `geopandas`, `shapely` — polygon handling (already in nb2)
- `folium` — map preview of ranked neighbourhoods (already in nb2)
- `numpy`, `pandas` — standard (already present)
