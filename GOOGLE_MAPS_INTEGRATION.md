# Google Maps Integration - Final Steps

## ✅ What's Already Done:
1. ✅ Date picker button (📅 calendar icon)
2. ✅ Time picker button (🕐 clock icon)  
3. ✅ Time format changed to HH:MM (seconds auto-added as :00)
4. ✅ Time parsing updated to handle HH:MM format

## 🗺️ Switching to Google Maps

To use Google Maps instead of OpenStreetMap, you need to modify the GPS tab.

### Step 1: Install Required Library

```cmd
pip install googlemaps
```

### Step 2: Replace the GPS Tab Code

Find the `create_gps_tab` method (around line 559) and replace the map widget creation with an embedded Google Maps iframe OR use the `tkinterweb` library to embed a web browser.

### Option A: Using Embedded HTML with Google Maps JavaScript API (Recommended)

This will create a proper interactive Google Maps widget. You'll need the `tkinterweb` library:

```cmd
pip install tkinterweb
```

Then replace the map creation section with:

```python
# Create embedded Google Maps
from tkinterweb import HtmlFrame

# Your Google Maps API Key
GOOGLE_MAPS_API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual API key

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
        
        function initMap() {{
            map = new google.maps.Map(document.getElementById('map'), {{
                center: {{lat: -31.9505, lng: 115.8605}},
                zoom: 12
            }});
            
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
                    map: map
                }});
            }}
            
            // Send coordinates to Python (via console)
            console.log('COORDS:' + location.lat() + ',' + location.lng());
        }}
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap" async defer></script>
</body>
</html>
"""

self.map_widget = HtmlFrame(map_container)
self.map_widget.grid(row=0, column=0, sticky="nsew")
self.map_widget.load_html(map_html)
```

### Option B: Simple Static Google Maps Link (Easier)

If you don't want to install more libraries, just add a button that opens Google Maps in the browser:

```python
def open_google_maps(self):
    """Open Google Maps in browser for coordinate selection."""
    import webbrowser
    # Default to Perth
    webbrowser.open("https://www.google.com/maps/@-31.9505,115.8605,12z")
    messagebox.showinfo(
        "Google Maps",
        "Click on a location in Google Maps, then:\n\n"
        "1. Right-click the location\n"
        "2. Click the coordinates that appear\n"
        "3. They'll be copied to clipboard\n"
        "4. Paste them into the Latitude/Longitude fields below"
    )
```

Then add a button in the GPS tab:

```python
ctk.CTkButton(
    tab,
    text="🗺️ Open Google Maps",
    command=self.open_google_maps
).grid(row=1, column=0, pady=5, padx=10, sticky="ew")
```

## 📝 My Recommendation

Use **Option B** (open in browser) because:
- ✅ No additional libraries needed
- ✅ Full Google Maps features (Street View, Search, etc.)
- ✅ Familiar interface
- ✅ Easy copy/paste workflow
- ✅ Your API key stays secure (not embedded in Python code)

Would you like me to implement Option B for you? It's the simplest and most user-friendly approach!

## Current Status:

✅ Date/Time pickers - WORKING  
✅ HH:MM time format - WORKING  
⏳ Google Maps - Need your preference (A or B above)
