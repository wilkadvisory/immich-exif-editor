# Recent Updates - Immich EXIF Editor

## ✅ Changes Made

### 1. **Larger Folder Tree Text (20% bigger)**
- Font size increased from default to 11pt (Segoe UI)
- Easier to read folder names

### 2. **Default Directory Changed to Z:\photos**
- App now starts in Z:\photos if it exists
- Falls back to home directory if Z:\photos doesn't exist

### 3. **Select All Checkbox Added**
- New checkbox at top of file list: "Select All Files"
- One click to select/deselect all files
- Works in addition to the existing "Select All" and "Deselect All" buttons

## 📋 Current Features

### File Selection:
- ✅ Click to select single file
- ✅ Ctrl+Click for multi-select (add/remove)
- ✅ Shift+Click for range selection
- ✅ "Select All" button
- ✅ "Deselect All" button
- ✅ "Select All Files" checkbox at top of list

### Date/Time Editing:
- ✅ Date/Time Original (EXIF)
- ✅ Create Date (EXIF)
- ✅ Modify Date (EXIF)
- ✅ GPS Date Stamp (EXIF)
- ✅ File Modified Date (EXIF)
- ✅ **Windows Created Date**
- ✅ **Windows Modified Date**
- ✅ Auto-increment time by filename order

### GPS Location:
- ✅ Manual coordinate entry
- ✅ Applies to all selected files
- ⏳ Interactive map (see GOOGLE_MAPS_GUIDE.md for implementation options)

### Other Features:
- ✅ Folder tree view (Windows Explorer style)
- ✅ Thumbnail previews
- ✅ Sanitise for sharing (removes all EXIF)
- ✅ Dark mode UI

## 🔜 Next: Google Maps Integration

See **GOOGLE_MAPS_GUIDE.md** for:
- How to get a Google Maps API key (if needed)
- Implementation options (FREE OpenStreetMap vs Google Maps)
- Click-to-select coordinates on an interactive map

**Recommended:** Use OpenStreetMap (free, no API key required)

## 🚀 Running the App

```cmd
cd C:\Users\jason\StudioProjects\immich-exif-editor
python src\main.py
```

Or build executable:
```cmd
build_clean.bat
```

## 📦 Requirements

```cmd
pip install -r requirements.txt
```

Currently installed:
- customtkinter
- Pillow
- pywin32 (for Windows timestamp modification)

To add map support:
```cmd
pip install tkintermapview
```
