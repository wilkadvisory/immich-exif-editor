"""GPS Preset Updater - Helper module to update GPS presets"""

from pathlib import Path
import re


def update_gps_preset(slot, name, lat, lon):
    """Update a specific GPS preset slot.
    
    Args:
        slot: Integer 0-5 for which button to update
        name: Display name for the preset
        lat: Latitude
        lon: Longitude
    """
    preset_file = Path(__file__).parent / 'gps_presets.py'
    
    # Read current file
    with open(preset_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the current presets
    match = re.search(r'GPS_PRESETS\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if not match:
        raise ValueError("Could not parse GPS_PRESETS")
    
    # Build new preset entry
    new_preset = f'{{"name": "{name}", "lat": {lat}, "lon": {lon}}}'
    
    # Split existing presets
    presets_str = match.group(1)
    preset_lines = [line.strip() for line in presets_str.split('},') if line.strip()]
    
    # Ensure we have at least 6 slots
    while len(preset_lines) < 6:
        preset_lines.append('{"name": "Empty", "lat": 0, "lon": 0')
    
    # Update the specified slot
    if 0 <= slot < len(preset_lines):
        preset_lines[slot] = new_preset
    
    # Rebuild the file content
    new_presets_str = ',\n    '.join(preset_lines)
    if not new_presets_str.endswith('}'):
        new_presets_str = new_presets_str + '}'
    
    new_content = f'''"""GPS location presets"""

# Edit these presets to your commonly used locations
# Format: {{"name": "Display Name", "lat": latitude, "lon": longitude}}

GPS_PRESETS = [
    {new_presets_str},
]
'''
    
    # Write back
    with open(preset_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
