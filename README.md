# Mast3dPlanner

3D building and mast viewer + analyser to help telecoms plan site placements. Built as an entry for the GIC competition.

## Features
- Building footprint ingestion
  - Downloads nearby building geometries (polygons / multipolygons) from OpenStreetMap using OSMnx.
  - Filters non-polygon features so visualisation and distance checks operate on valid footprints.

- Height handling (preserve + simulate)
  - Preserves OSM-provided building heights when available.
  - When OSM height data is missing, assigns simulated heights drawn uniformly from a configurable min/max range (set in the app sidebar).
  - Heights are numeric-coerced so malformed values do not break the app.

- Accurate metric checks (UTM projection)
  - Reprojects building footprints and the selected site point to an appropriate UTM CRS before measuring distances.
  - Ensures setback and proximity checks (e.g., 5 m rule) are computed in metres, not degrees.

- Compliance checks
  - Collision detection: verifies if the chosen site point falls INSIDE any building footprint.
  - Setback / proximity detection: computes the minimum distance to nearby buildings and flags violations (default threshold = 5 m).
  - Returns human-friendly status messages: SAFE, VIOLATION, or COLLISION.

- 3D visualization with pydeck
  - Extruded polygon layers render buildings and the proposed mast in 3D.
  - Interactive tooltips show height values; pickable polygons allow quick inspection.
  - Initial camera/view state centres on the selected coordinate with configurable zoom/pitch.

- Height analytics & warnings
  - Computes the tallest nearby building and compares it against the mast height.
  - Shows Line-of-Sight warnings if surrounding buildings exceed the mast height.

- Export & reproducibility
  - Download building attribute table (CSV) from the app for offline analysis or record keeping.
  - Streamlit caching reduces repeated OSM queries during iterative parameter tweaks.

- Usability & advanced options
  - Sidebar form groups inputs to prevent unnecessary reruns until the user clicks "Generate & Validate".
  - Advanced settings allow control of the simulated height range.
  - Session-state handling avoids a re-run on first page load unless intended.

## Quick start (Windows)
1. Clone the repo:
   git clone <repo-url>
   cd Mast3dPlanner_GIC

2. Create & activate virtual environment:
   python -m venv .venv
   .venv\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

4. Run the app:
   streamlit run main.py

## Recommended Python packages
(If you don't have requirements.txt, install these)
pip install streamlit osmnx geopandas shapely pydeck pandas numpy

Note: osmnx/geopandas may require compiled geospatial libraries (GDAL, PROJ, GEOS). If you hit install issues on Windows, consider using conda:
conda create -n mast3d python=3.10
conda activate mast3d
conda install -c conda-forge geopandas osmnx gdal proj

## Usage
- Open the sidebar in the Streamlit app to set latitude/longitude, search radius and tower height.
- Click "Generate & Validate" to download OSM footprints, assign heights, run compliance checks and visualize the 3D scene.
- Download building data as CSV from the app.

## Notes
- The app queries OSM data — ensure internet access and respect OSM usage policies.
- Existing OSM heights are preserved; random heights are only assigned when OSM height data is missing.

## Contributing
Open issues or PRs. Keep changes small and include a brief description.

## License
MIT
