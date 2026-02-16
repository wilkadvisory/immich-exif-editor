"""
Fixed open_interactive_maps method - copy this to replace the existing one in main.py
"""

def open_interactive_maps(self):
    """Open an interactive Google Maps page in browser."""
    # Use triple quotes and avoid f-string issues with JavaScript quotes
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>GPS Coordinate Picker</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        #search-container { margin-bottom: 15px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        #search-box { width: 100%; padding: 12px; font-size: 16px; border: 2px solid #4285F4; border-radius: 4px; box-sizing: border-box; }
        #map { height: 600px; width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
        #coordinates { margin-top: 15px; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        #coord-display { font-size: 24px; font-weight: bold; color: #4285F4; margin: 10px 0; padding: 15px; background: #f8f9fa; border-radius: 4px; font-family: 'Courier New', monospace; }
        .label { font-size: 14px; color: #666; margin-bottom: 5px; }
        .button-row { margin-top: 15px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        button { padding: 15px 30px; font-size: 18px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        #copy-btn { background: #4CAF50; color: white; }
        #copy-btn:hover { background: #45a049; }
        #save-preset-btn { background: #FF9800; color: white; }
        #save-preset-btn:hover { background: #F57C00; }
        select { padding: 12px; font-size: 16px; border: 2px solid #4285F4; border-radius: 4px; background: white; cursor: pointer; }
        input[type="text"].preset-name { padding: 12px; font-size: 16px; border: 2px solid #4285F4; border-radius: 4px; width: 250px; }
        #status { margin-top: 10px; padding: 10px; border-radius: 4px; font-size: 14px; display: none; }
        #status.success { background: #d4edda; color: #155724; display: block; }
    </style>
</head>
<body>
    <div id="search-container">
        <input id="search-box" type="text" placeholder="Search for a location" autofocus>
    </div>
    <div id="map"></div>
    <div id="coordinates">
        <div class="label">Click anywhere on the map:</div>
        <div id="coord-display">Click on the map...</div>
        <div class="button-row" style="display:none;" id="button-row">
            <button id="copy-btn" onclick="copyToApp()">📋 Copy to App</button>
            <input type="text" id="preset-name" class="preset-name" placeholder="Location name (e.g., 🏠 Home)">
            <select id="preset-slot">
                <option value="">Save to...</option>
                <option value="0">Button 1</option>
                <option value="1">Button 2</option>
                <option value="2">Button 3</option>
                <option value="3">Button 4</option>
                <option value="4">Button 5</option>
                <option value="5">Button 6</option>
            </select>
            <button id="save-preset-btn" onclick="savePreset()">💾 Save</button>
        </div>
        <div id="status"></div>
    </div>
    
    <script>
        let map, marker, currentLat = null, currentLng = null;
        
        function initMap() {
            map = new google.maps.Map(document.getElementById('map'), {
                center: {lat: -31.959910, lng: 116.030874},
                zoom: 14,
                mapTypeControl: true,
                streetViewControl: true,
                fullscreenControl: true
            });
            
            const input = document.getElementById('search-box');
            const searchBox = new google.maps.places.SearchBox(input);
            
            map.addListener('bounds_changed', () => searchBox.setBounds(map.getBounds()));
            searchBox.addListener('places_changed', function() {
                const places = searchBox.getPlaces();
                if (places.length == 0) return;
                const place = places[0];
                if (!place.geometry || !place.geometry.location) return;
                map.setCenter(place.geometry.location);
                map.setZoom(15);
                placeMarker(place.geometry.location);
            });
            
            map.addListener('click', e => placeMarker(e.latLng));
        }
        
        function placeMarker(location) {
            if (marker) marker.setMap(null);
            marker = new google.maps.Marker({
                position: location,
                map: map,
                animation: google.maps.Animation.DROP
            });
            
            currentLat = location.lat().toFixed(6);
            currentLng = location.lng().toFixed(6);
            document.getElementById('coord-display').innerHTML = 'Latitude: ' + currentLat + '<br>Longitude: ' + currentLng;
            document.getElementById('button-row').style.display = 'flex';
            copyToApp();
        }
        
        function copyToApp() {
            if (!currentLat || !currentLng) return;
            const data = currentLat + ',' + currentLng;
            if (navigator.clipboard) {
                navigator.clipboard.writeText(data).then(() => showStatus('✓ Copied to clipboard!'));
            }
        }
        
        function savePreset() {
            const slot = document.getElementById('preset-slot').value;
            const name = document.getElementById('preset-name').value.trim();
            
            if (!slot) {
                alert('Please select a button slot');
                return;
            }
            if (!name) {
                alert('Please enter a location name');
                return;
            }
            if (!currentLat || !currentLng) {
                alert('Please select a location on the map first');
                return;
            }
            
            // Create JSON file and download it
            const presetData = {
                slot: parseInt(slot),
                name: name,
                lat: parseFloat(currentLat),
                lon: parseFloat(currentLng)
            };
            
            const blob = new Blob([JSON.stringify(presetData)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'immich_preset_save.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showStatus('✓ File downloaded! Move it to your Downloads folder - the app will detect it.');
            
            // Clear fields
            document.getElementById('preset-name').value = '';
            document.getElementById('preset-slot').value = '';
        }
        
        function showStatus(message) {
            const status = document.getElementById('status');
            status.className = 'success';
            status.textContent = message;
            setTimeout(() => status.style.display = 'none', 8000);
        }
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key=API_KEY_PLACEHOLDER&libraries=places&callback=initMap" async defer></script>
</body>
</html>
"""
    
    # Replace the API key placeholder
    html_content = html_content.replace('API_KEY_PLACEHOLDER', self.GOOGLE_MAPS_API_KEY)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        self.map_html_path = f.name
    
    webbrowser.open('file://' + self.map_html_path)
    self.start_coordinate_polling()
    self.start_preset_save_polling()
