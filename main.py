import streamlit as st
import random
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point
import pydeck as pdk
import numpy as np
import pandas as pd

# --- Page Config ---
st.set_page_config(layout="wide", page_title="3D Telecom Site Compliance Tool")

# --- Logic Class ---
class OSM3DBuilder:
    def __init__(self, poi_coordinates, poi_height=20, building_height_range=(2.73, 14.7)):
        self.poi = poi_coordinates # (Lat, Lon)
        self.poi_height = poi_height
        self.height_range = building_height_range
        self.footprints = None
        self.gdf_poi = None

    def _extract_coordinates(self, geometry):
        """Helper to convert Shapely geometry to a list of coordinates for Pydeck."""
        if geometry.geom_type == 'Polygon':
            return list(geometry.exterior.coords)
        elif geometry.geom_type == 'MultiPolygon':
            return list(max(geometry.geoms, key=lambda a: a.area).exterior.coords)
        return []

    def download_osm_data(self, dist=500):
        """Downloads building footprints."""
        tags = {"building": True, 'leisure': 'park', 'amenity': ['cafe', 'restaurant', 'school', 'hospital']}
        try:
            self.footprints = ox.features_from_point(self.poi, tags=tags, dist=dist).reset_index()
            # Filter to keep only polygons
            self.footprints = self.footprints[self.footprints.geometry.type.isin(['Polygon', 'MultiPolygon'])].copy()
            # Extract coordinates for Pydeck (Visuals)
            self.footprints['coordinates'] = self.footprints['geometry'].apply(self._extract_coordinates)
        except Exception as e:
            # Create empty GDF if fails
            self.footprints = gpd.GeoDataFrame(columns=['geometry', 'height', 'elev_source'], geometry='geometry', crs="EPSG:4326")

        # Prepare POI GeoDataFrame for Visuals
        poi_geometry = Point(self.poi[1], self.poi[0]).buffer(0.00005) 
        self.gdf_poi = gpd.GeoDataFrame([{'geometry': poi_geometry, 'height': self.poi_height}])
        self.gdf_poi['coordinates'] = self.gdf_poi['geometry'].apply(self._extract_coordinates)

    def assign_heights(self):
        """
        Assigns heights. 
        CRITICAL: Only assigns random height if 'height' is NaN/Missing. 
        Existing OSM heights are preserved.
        """
        if self.footprints is None or self.footprints.empty:
            return

        if 'height' not in self.footprints.columns:
            self.footprints['height'] = np.nan

        # Coerce height to numeric (errors='coerce' turns non-numbers to NaN)
        self.footprints['height'] = pd.to_numeric(self.footprints['height'], errors='coerce')

        def height_appender(row):
            # IF height is missing (NaN), generate a random one.
            # ELSE, keep the existing data.
            if pd.isna(row["height"]):
                return round(random.uniform(*self.height_range), 1)
            return row["height"]

        self.footprints['height'] = self.footprints.apply(height_appender, axis=1)

    def get_max_building_height(self):
        """Returns the maximum height of any building in the dataframe."""
        if self.footprints is not None and not self.footprints.empty:
            return self.footprints['height'].max()
        return 0

    def check_compliance(self):
        """
        Checks collision and 5m proximity.
        """
        if self.footprints is None or self.footprints.empty:
            return "SAFE", "No buildings nearby.", 9999

        # 1. PROJECT TO UTM (METERS)
        utm_crs = self.footprints.estimate_utm_crs()
        gdf_buildings_utm = self.footprints.to_crs(utm_crs)
        
        poi_geom = Point(self.poi[1], self.poi[0]) 
        gdf_poi = gpd.GeoDataFrame(geometry=[poi_geom], crs="EPSG:4326")
        gdf_poi_utm = gdf_poi.to_crs(utm_crs)
        poi_point_utm = gdf_poi_utm.geometry.iloc[0]

        # 2. CHECK: COLLISION
        is_inside = gdf_buildings_utm.contains(poi_point_utm).any()
        if is_inside:
            return "COLLISION", "CRITICAL: The selected site falls directly on an existing building structure.", 0

        # 3. CHECK: PROXIMITY
        distances = gdf_buildings_utm.distance(poi_point_utm)
        min_dist = distances.min()
        
        if min_dist <= 5.0:
            return "VIOLATION", f"REGULATORY NOTICE: Site is {min_dist:.2f}m from a building. This violates NCC Setback Regulations (Minimum 5m).", min_dist

        return "SAFE", f"Site is Compliant. Nearest building is {min_dist:.2f}m away.", min_dist

    def get_deck(self, zoom=17, pitch=45):
        layers = []
        # Buildings
        if self.footprints is not None and not self.footprints.empty:
            building_layer = pdk.Layer(
                'PolygonLayer',
                data=self.footprints,
                get_polygon='coordinates',
                extruded=True,
                get_elevation='height',
                get_fill_color=[200, 200, 200, 200],
                pickable=True,
                auto_highlight=True
            )
            layers.append(building_layer)
        # Tower
        if self.gdf_poi is not None:
            poi_layer = pdk.Layer(
                'PolygonLayer',
                data=self.gdf_poi,
                get_polygon='coordinates',
                extruded=True,
                get_elevation='height',
                get_fill_color=[255, 0, 0, 255],
                get_line_color=[255, 0, 0, 255],
                pickable=True
            )
            layers.append(poi_layer)

        view_state = pdk.ViewState(latitude=self.poi[0], longitude=self.poi[1], zoom=zoom, pitch=pitch)
        return pdk.Deck(layers=layers, initial_view_state=view_state, tooltip={"text": "{height}m"})

# --- Streamlit UI ---

st.title("📡 3D Telecom Site Planner & Compliance Check")

with st.sidebar:
    st.header("📍 Site Configuration")
    lat = st.number_input("Latitude", value=6.457211, format="%.6f")
    lon = st.number_input("Longitude", value=3.559664, format="%.6f")
    
    st.header("📏 Parameters")
    radius = st.slider("Search Radius (m)", 100, 800, 300)
    tower_height = st.slider("Tower Height (m)", 10, 100, 30)
    
    # --- HIDDEN/ADVANCED SETTINGS ---
    with st.expander("🛠️ Advanced Settings (Height Simulation)"):
        st.caption("If OSM data lacks height, use random range:")
        min_h = st.number_input("Min Random Height", value=3.0)
        max_h = st.number_input("Max Random Height", value=15.0)

    run_btn = st.button("Generate & Validate", type="primary")

@st.cache_data
def process_site(lat, lon, radius, tower_h, min_h, max_h):
    # Pass the min/max height range to the builder
    builder = OSM3DBuilder((lat, lon), poi_height=tower_h, building_height_range=(min_h, max_h))
    builder.download_osm_data(dist=radius)
    builder.assign_heights()
    status, msg, dist = builder.check_compliance()
    max_b_height = builder.get_max_building_height()
    return builder, status, msg, max_b_height

if run_btn:
    with st.spinner("Analyzing Site Compliance & Heights..."):
        builder_instance, status, msg, max_b_height = process_site(lat, lon, radius, tower_height, min_h, max_h)
        
        # 1. DISPLAY COMPLIANCE ALERTS
        if status == "COLLISION":
            st.error(f"🛑 **SITE REJECTED**: {msg}")
        elif status == "VIOLATION":
            st.warning(f"⚠️ **REGULATORY WARNING**: {msg}")
        else:
            st.success(f"✅ **SITE APPROVED**: {msg}")

        # 2. DISPLAY HEIGHT ANALYSIS
        col1, col2 = st.columns(2)
        col1.metric("Your Tower Height", f"{tower_height}m")
        col2.metric("Tallest Nearby Building", f"{max_b_height}m")

        if max_b_height > tower_height:
             st.info(f"📉 **Line of Sight Warning**: The tallest building in this area ({max_b_height}m) is taller than your mast ({tower_height}m). This may cause signal shadowing.")
        else:
             st.caption("Probe: Your mast clears the tallest building in the immediate vicinity.")

        # 3. RENDER MAP
        if builder_instance.footprints is not None:
            deck = builder_instance.get_deck()
            st.pydeck_chart(deck)
            
            # 4. DOWNLOAD BUTTON
            # Prepare CSV: Drop the Pydeck 'coordinates' list, keep Geometry (WKT) and other cols
            df_export = builder_instance.footprints.drop(columns=['coordinates'], errors='ignore')
            csv = df_export.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Download Building Data (CSV)",
                data=csv,
                file_name=f"site_analysis_{lat}_{lon}.csv",
                mime="text/csv",
            )