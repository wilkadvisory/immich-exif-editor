"""GPS Preset Updater - Helper module to update GPS presets"""

from pathlib import Path


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
        lines = f.readlines()
    
    # Find the GPS_PRESETS array
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if 'GPS_PRESETS = [' in line:
            start_idx = i + 1
        if start_idx and line.strip() == ']':
            end_idx = i
            break
    
    if start_idx is None or end_idx is None:
        raise ValueError("Could not find GPS_PRESETS array")
    
    # Parse existing presets
    presets = []
    for i in range(start_idx, end_idx):
        line = lines[i].strip()
        if line.startswith('{') and 'name' in line:
            presets.append(line.rstrip(','))
    
    # Ensure we have 6 slots
    while len(presets) < 6:
        presets.append('{"name": "Empty", "lat": 0, "lon": 0}')
    
    # Update the specified slot
    if 0 <= slot < 6:
        presets[slot] = f'{{"name": "{name}", "lat": {lat}, "lon": {lon}}}'
    
    # Rebuild file
    new_content = '''"""GPS location presets"""

# Edit these presets to your commonly used locations
# Format: {"name": "Display Name", "lat": latitude, "lon": longitude}

GPS_PRESETS = [
'''
    
    for i, preset in enumerate(presets):
        new_content += f"    {preset},\n"
    
    new_content += "]\n"
    
    # Write back
    with open(preset_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
