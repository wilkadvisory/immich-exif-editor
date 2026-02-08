# Google Maps Integration Guide

## Overview

To add an interactive Google Maps widget to the GPS Location tab, we'll use the **tkintermapview** library. This library provides a map widget where you can click to get coordinates.

## Step 1: Get a Google Maps API Key (Optional)

The tkintermapview library works WITHOUT an API key using OpenStreetMap by default, which is completely free! However, if you want to use Google Maps tiles specifically, follow these steps:

### Getting a Google Cloud API Key:

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/

2. **Create a New Project:**
   - Click "Select a Project" at the top
   - Click "New Project"
   - Name it "Immich EXIF Editor"
   - Click "Create"

3. **Enable the Maps JavaScript API:**
   - In the search bar, type "Maps JavaScript API"
   - Click on it
   - Click "Enable"

4. **Create API Key:**
   - Go to "Credentials" in the left menu
   - Click "Create Credentials" → "API Key"
   - Copy the API key shown

5. **Restrict the API Key (Important for Security):**
   - Click on your new API key to edit it
   - Under "Application restrictions", select "None" (for desktop app)
   - Under "API restrictions", select "Restrict key"
   - Select only "Maps JavaScript API"
   - Click "Save"

**Cost:** Google gives you $200 free credit per month. For personal use, you'll never hit this limit.

## Step 2: Install the Library

```cmd
pip install tkintermapview
```

Add to requirements.txt:
```
customtkinter>=5.2.0
Pillow>=10.0.0
pywin32>=306
tkintermapview>=1.29
```

## Step 3: Implementation

I can add the interactive map to your GPS tab with these features:

### Features:
- **Click on map** → Gets latitude/longitude automatically
- **Search box** → Type address and map centers on it
- **Zoom controls** → Mouse wheel or +/- buttons
- **Different map types** → OpenStreetMap (free) or Google (requires API key)
- **Marker** → Shows selected location
- **Coordinates display** → Shows current cursor position

### Code Changes Needed:

The GPS tab would look like this:
```
┌─────────────────────────────┐
│ 📍 GPS Location             │
├─────────────────────────────┤
│ Search: [Perth, Australia ] │
│                             │
│ ┌─────────────────────────┐ │
│ │                         │ │
│ │    Interactive Map      │ │
│ │    (Click to select)    │ │
│ │                         │ │
│ └─────────────────────────┘ │
│                             │
│ Selected Coordinates:       │
│ Lat: -31.9505              │
│ Lon: 115.8605              │
│                             │
│ [✅ Apply GPS Location]     │
└─────────────────────────────┘
```

## Step 4: Using Without API Key (Recommended)

The easiest option is to use OpenStreetMap (completely free, no API key needed):

```python
import tkintermapview

# Create map widget
map_widget = tkintermapview.TkinterMapView(parent, width=800, height=600)
map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)  # OpenStreetMap

# Set initial position (Perth)
map_widget.set_position(-31.9505, 115.8605)
map_widget.set_zoom(12)

# Handle click events
def on_map_click(coords):
    lat, lon = coords
    print(f"Clicked: {lat}, {lon}")
    
map_widget.add_left_click_map_command(on_map_click)
```

## Do You Want Me To Add This?

I can implement the interactive map with these options:

**Option A: OpenStreetMap (FREE - No API key needed)**
- Works immediately
- Good quality maps
- No setup required
- No costs ever

**Option B: Google Maps (Requires API key)**
- Familiar Google Maps interface
- Requires setup steps above
- $200/month free credit

Which would you prefer? I'd recommend **Option A** - it's simpler and works great!

Let me know and I'll add the code! 🗺️
