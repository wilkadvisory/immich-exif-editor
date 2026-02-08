# Google Maps Integration - Complete Implementation

## ✅ What's Already Done:
1. ✅ Updated requirements.txt with tkinterweb
2. ✅ Updated imports (removed tkintermapview, added HtmlFrame)
3. ✅ Added GOOGLE_MAPS_API_KEY constant to class
4. ✅ Date/Time pickers working
5. ✅ HH:MM time format working

## 🔧 FINAL STEPS:

### Step 1: Add Your Google Maps API Key

Open `src/main.py` and find line ~29:

```python
GOOGLE_MAPS_API_KEY = "YOUR_API_KEY_HERE"  # Replace this with your Google Maps API key
```

Replace `YOUR_API_KEY_HERE` with your actual Google Maps API key.

### Step 2: Replace the GPS Tab Methods

Find the `create_gps_tab` method (around line 595) and replace it with:

```python
def create_gps_tab(self):
    """Create the GPS location tab with Google Maps."""
    tab = self.tabview.add("📍 GPS Location")
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_rowconfigure(2, weight=1)
    
    # Instructions
    ctk.CTkLabel(
        tab,
        text="Click on the map to select GPS coordinates",
        font=ctk.CTkFont(size=14, weight="bold")
    ).grid(row=0, column=0, pady=10, padx=10, sticky="ew")
    
    # Address search bar
    search_frame = ctk.CTkFrame(tab)
    search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
    search_frame.grid_columnconfigure(0, weight=1)
    
    self.address_entry = ctk.CTkEntry(
        search_frame,
        placeholder_text="Enter address (e.g. 3 Stoneham St, Joondanna)"
    )
    self.address_entry.pack(side="left", fill="x", expand=True, padx=5)
    self.address_entry.bind('<Return>', lambda e: self.search_address())
    
    ctk.CTkButton(
        search_frame,
        text="🔍 Search",
        command=self.search_address,
        width=100
    ).pack(side="left", padx=5)
    
    # Map container
    map_container = ctk.CTkFrame(tab)
    map_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
    map_container.grid_columnconfigure(0, weight=1)
    map_container.grid_rowconfigure(0, weight=1)
    
    # Create Google Maps HTML
    map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        #map {{ height: 100%; width: 100%; }}
        html, body {{ height: 100%; margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        let marker;
        let map;
        let geocoder;
        
        function initMap() {{
            map = new google.maps.Map(document.getElementById('map'), {{
                center: {{lat: -31.9505, lng: 115.8605}},
                zoom: 12,
                mapTypeControl: true,
                streetViewControl: true,
                fullscreenControl: true
            }});
            
            geocoder = new google.maps.Geocoder();
            
            map.addListener('click', function(e) {{
                placeMarker(e.latLng);
            }});
        }}
        
        function placeMarker(location) {{
            if (marker) {{
                marker.setPosition(location);
            }} else {{
                marker = new google.maps.Marker({{
                    position: location,
                    map: map,
                    title: 'Selected Location'
                }});
            }}
            
            map.panTo(location);
            
            // Log coordinates for Python to capture
            console.log('COORDS:' + location.lat() + ',' + location.lng());
        }}
        
        function searchAddress(address) {{
            geocoder.geocode({{ 'address': address }}, function(results, status) {{
                if (status === 'OK') {{
                    map.setCenter(results[0].geometry.location);
                    map.setZoom(15);
                    placeMarker(results[0].geometry.location);
                }} else {{
                    console.log('SEARCH_ERROR:' + status);
                }}
            }});
        }}
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key={self.GOOGLE_MAPS_API_KEY}&callback=initMap" async defer></script>
</body>
</html>
"""
    
    # Create embedded map
    self.map_widget = HtmlFrame(map_container)
    self.map_widget.grid(row=0, column=0, sticky="nsew")
    self.map_widget.load_html(map_html)
    
    # Listen for console messages to capture coordinates
    self.map_widget.add_message_listener(self.on_map_message)
    
    # Coordinates display
    coords_display_frame = ctk.CTkFrame(tab)
    coords_display_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
    coords_display_frame.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(
        coords_display_frame,
        text="Selected Location:",
        font=ctk.CTkFont(size=12, weight="bold")
    ).grid(row=0, column=0, padx=5, pady=5, sticky="w")
    
    self.coords_display = ctk.CTkLabel(
        coords_display_frame,
        text="Click on map to select",
        text_color="gray"
    )
    self.coords_display.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    
    # Manual entry frame
    manual_frame = ctk.CTkFrame(tab)
    manual_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
    manual_frame.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(manual_frame, text="Or enter manually:", font=ctk.CTkFont(size=11)).grid(
        row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w"
    )
    
    ctk.CTkLabel(manual_frame, text="Latitude:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
    self.lat_entry = ctk.CTkEntry(manual_frame, placeholder_text="-31.9505", width=150)
    self.lat_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
    
    ctk.CTkLabel(manual_frame, text="Longitude:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
    self.lon_entry = ctk.CTkEntry(manual_frame, placeholder_text="115.8605", width=150)
    self.lon_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")
    
    # Apply button
    ctk.CTkButton(
        tab,
        text="✅ Apply GPS Location to Selected Files",
        command=self.apply_gps,
        fg_color="green",
        hover_color="darkgreen",
        height=40
    ).grid(row=5, column=0, pady=10, padx=10, sticky="ew")
```

### Step 3: Delete the old methods and add new ones

DELETE these methods (they're from OpenStreetMap):
- `on_map_click`
- `on_manual_coords_enter`

ADD these new methods (add them after `create_gps_tab`):

```python
def search_address(self):
    """Search for an address on the map."""
    address = self.address_entry.get().strip()
    if address:
        # Call JavaScript function
        self.map_widget.evaluate_js(f"searchAddress('{address}')")

def on_map_message(self, message):
    """Handle messages from the map (coordinates from clicks)."""
    if message.startswith('COORDS:'):
        coords_str = message.replace('COORDS:', '')
        try:
            lat_str, lon_str = coords_str.split(',')
            lat = float(lat_str)
            lon = float(lon_str)
            
            # Update display
            self.coords_display.configure(
                text=f"Lat: {lat:.6f}, Lon: {lon:.6f}",
                text_color="white"
            )
            
            # Update manual entry fields
            self.lat_entry.delete(0, 'end')
            self.lat_entry.insert(0, f"{lat:.6f}")
            self.lon_entry.delete(0, 'end')
            self.lon_entry.insert(0, f"{lon:.6f}")
        except:
            pass
    elif message.startswith('SEARCH_ERROR:'):
        error = message.replace('SEARCH_ERROR:', '')
        messagebox.showerror("Search Error", f"Could not find address. Status: {error}")
```

### Step 4: Install Dependencies

```cmd
cd C:\Users\jason\StudioProjects\immich-exif-editor
pip install tkinterweb
```

### Step 5: Run It!

```cmd
python src\main.py
```

## Features:
- ✅ Full Google Maps with Street View
- ✅ Address search bar (type "3 Stoneham St, Joondanna" and hit Enter or click Search)
- ✅ Click anywhere on map to select coordinates
- ✅ Red marker shows selection
- ✅ Map controls (zoom, pan, street view, map type)
- ✅ Coordinates auto-update when you click
- ✅ Manual entry still works

The API key line in the code will be around line 29. Just replace "YOUR_API_KEY_HERE" with your actual key!
