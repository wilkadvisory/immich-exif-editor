"""
Fix the preset save functionality in main.py
This script updates the open_interactive_maps method to properly save presets.
"""

import re
from pathlib import Path

def fix_main_py():
    main_py = Path('src/main.py')
    
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the savePreset function in the HTML
    old_save_preset = r'''function savePreset\(\) \{[^}]+localStorage\.setItem[^}]+\}'''
    
    new_save_preset = '''function savePreset() {
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
            
            // Create preset data and download it
            const presetData = {
                slot: parseInt(slot),
                name: name,
                lat: parseFloat(currentLat),
                lon: parseFloat(currentLng)
            };
            
            // Create download
            const blob = new Blob([JSON.stringify(presetData)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'immich_preset_save.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showStatus(`✓ File downloaded! Save it to your Downloads or temp folder - the app will detect it automatically.`);
            
            // Clear fields
            document.getElementById('preset-name').value = '';
            document.getElementById('preset-slot').value = '';
        }'''
    
    # Replace using regex
    content = re.sub(old_save_preset, new_save_preset, content, flags=re.DOTALL)
    
    # Also need to update the polling to check Downloads folder
    old_polling = '''    def start_preset_save_polling(self):
        """Poll for preset save requests from the browser."""
        def check_preset_save():
            try:
                preset_file = Path(tempfile.gettempdir()) / 'immich_preset_save.json'
                if preset_file.exists():
                    import json
                    with open(preset_file, 'r') as f:
                        data = json.load(f)
                    
                    # Update the preset
                    update_gps_preset(data['slot'], data['name'], data['lat'], data['lon'])
                    
                    # Delete the file
                    preset_file.unlink()
                    
                    # Show confirmation and reload presets
                    messagebox.showinfo(
                        "Preset Saved",
                        f"Saved '{data['name']}' to Button {data['slot'] + 1}!\\n\\nRestart the app to see the changes."
                    )
            except Exception as e:
                print(f"Error checking preset save: {e}")
            
            # Check again in 1 second
            if hasattr(self, '_polling_active') and self._polling_active:
                self.after(1000, check_preset_save)
        
        self._polling_active = True
        self.after(1000, check_preset_save)'''
    
    new_polling = '''    def start_preset_save_polling(self):
        """Poll for preset save requests from the browser."""
        def check_preset_save():
            try:
                # Check both temp folder and Downloads folder
                temp_file = Path(tempfile.gettempdir()) / 'immich_preset_save.json'
                downloads_file = Path.home() / 'Downloads' / 'immich_preset_save.json'
                
                preset_file = None
                if temp_file.exists():
                    preset_file = temp_file
                elif downloads_file.exists():
                    preset_file = downloads_file
                
                if preset_file:
                    import json
                    with open(preset_file, 'r') as f:
                        data = json.load(f)
                    
                    # Update the preset
                    update_gps_preset(data['slot'], data['name'], data['lat'], data['lon'])
                    
                    # Delete the file
                    preset_file.unlink()
                    
                    # Show confirmation
                    messagebox.showinfo(
                        "Preset Saved",
                        f"Saved '{data['name']}' to Button {data['slot'] + 1}!\\n\\nRestart the app to see the changes."
                    )
            except Exception as e:
                print(f"Error checking preset save: {e}")
            
            # Check again in 1 second
            if hasattr(self, '_polling_active') and self._polling_active:
                self.after(1000, check_preset_save)
        
        self._polling_active = True
        self.after(1000, check_preset_save)'''
    
    # Replace the polling function
    content = content.replace(old_polling, new_polling)
    
    # Write back
    with open(main_py, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Fixed preset save functionality!")
    print("\nHow it works now:")
    print("1. Click location on Google Maps")
    print("2. Fill in preset name and select button slot")
    print("3. Click 'Save' - it downloads immich_preset_save.json")
    print("4. The app automatically detects the file in Downloads or temp folder")
    print("5. Preset is saved - restart app to see changes")

if __name__ == '__main__':
    fix_main_py()
