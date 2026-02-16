"""
Immich EXIF Bulk Editor
A modern Windows 11 application for bulk EXIF editing
"""

import sys
import os
import subprocess
import platform
from pathlib import Path
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkcalendar import Calendar, DateEntry
import webbrowser
import tempfile
import pywintypes
import win32file
import win32con
from dotenv import load_dotenv
from version import __version__
from gps_presets import GPS_PRESETS
from gps_preset_updater import update_gps_preset

# Load environment variables
load_dotenv()

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ExifEditor(ctk.CTk):
    # Google Maps API Key - loaded from environment variable
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', 'your_api_key_here')
    
    # Debug: Print API key status on startup
    if not GOOGLE_MAPS_API_KEY or GOOGLE_MAPS_API_KEY == 'your_api_key_here':
        print("WARNING: Google Maps API key not loaded from .env file!")
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title(f"Immich EXIF Bulk Editor v{__version__}")
        
        # Start maximized
        self.state('zoomed')  # Windows maximize
        
        # Lazy loading control
        self.load_executor = ThreadPoolExecutor(max_workers=10)
        self.loaded_files = set()  # Track what's been loaded
        
        # State variables
        # Default to Z:\photos if it exists, otherwise home
        default_path = Path('Z:/photos')
        self.current_directory = default_path if default_path.exists() else Path.home()
        self.selected_files = []
        self.file_widgets = {}  # Store file widgets for selection
        self.last_selected_index = None  # For shift+click
        self.all_files = []  # All files in current directory
        
        # Check for ExifTool
        if not self.check_exiftool():
            messagebox.showerror(
                "ExifTool Required",
                "ExifTool not found!\n\n"
                "Please install ExifTool from https://exiftool.org\n"
                "and add it to your PATH."
            )
            self.quit()
            return
        
        self.create_ui()
    
    def check_exiftool(self):
        """Check if ExifTool is available."""
        try:
            cmd = 'exiftool.exe' if platform.system() == 'Windows' else 'exiftool'
            result = subprocess.run(
                [cmd, '-ver'],
                capture_output=True,
                text=True,
                shell=(platform.system() == 'Windows')
            )
            return result.returncode == 0
        except:
            return False
    
    def show_auto_close_message(self, title, message, timeout=3000):
        """Show a message that auto-closes after timeout milliseconds."""
        popup = tk.Toplevel(self)
        popup.title(title)
        popup.transient(self)
        popup.grab_set()
        
        # Make it look nice
        popup.configure(bg='white')
        
        # Message
        msg_label = tk.Label(
            popup,
            text=message,
            font=('Segoe UI', 12),
            bg='white',
            fg='#2d2d2d',
            padx=30,
            pady=20,
            justify='left'
        )
        msg_label.pack()
        
        # Timer label
        timer_label = tk.Label(
            popup,
            text="",
            font=('Segoe UI', 9),
            bg='white',
            fg='gray'
        )
        timer_label.pack(pady=(0, 10))
        
        # OK button
        ok_btn = tk.Button(
            popup,
            text="OK",
            command=popup.destroy,
            font=('Segoe UI', 11, 'bold'),
            bg='#4285F4',
            fg='white',
            padx=30,
            pady=8,
            relief='flat',
            cursor='hand2'
        )
        ok_btn.pack(pady=(0, 15))
        
        # Centre on main window
        popup.update_idletasks()
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()
        popup_width = popup.winfo_width()
        popup_height = popup.winfo_height()
        
        x = main_x + (main_width // 2) - (popup_width // 2)
        y = main_y + (main_height // 2) - (popup_height // 2)
        popup.geometry(f'+{x}+{y}')
        
        # Auto-close countdown
        seconds_left = [timeout // 1000]  # Use list to allow modification in nested function
        
        def update_timer():
            if seconds_left[0] > 0:
                timer_label.config(text=f"Auto-closing in {seconds_left[0]} seconds...")
                seconds_left[0] -= 1
                popup.after(1000, update_timer)
            else:
                try:
                    popup.destroy()
                except:
                    pass
        
        update_timer()
        
        # Also close on any key press
        popup.bind('<Key>', lambda e: popup.destroy())
    
    def show_progress_dialog(self, title, total_files):
        """Create and return a progress dialog."""
        progress_window = tk.Toplevel(self)
        progress_window.title(title)
        progress_window.geometry("500x200")
        progress_window.transient(self)
        progress_window.grab_set()
        
        # Centre on main window
        self.update_idletasks()
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()
        
        x = main_x + (main_width // 2) - 250
        y = main_y + (main_height // 2) - 100
        progress_window.geometry(f'500x200+{x}+{y}')
        
        # Progress info
        tk.Label(
            progress_window,
            text=f"Processing {total_files} files...",
            font=('Segoe UI', 14, 'bold')
        ).pack(pady=20)
        
        status_label = tk.Label(
            progress_window,
            text="Starting...",
            font=('Segoe UI', 11)
        )
        status_label.pack(pady=5)
        
        # Progress bar
        progress_bar = ttk.Progressbar(
            progress_window,
            length=400,
            mode='determinate',
            maximum=total_files
        )
        progress_bar.pack(pady=20)
        
        # Percentage label
        percent_label = tk.Label(
            progress_window,
            text="0%",
            font=('Segoe UI', 12, 'bold')
        )
        percent_label.pack(pady=5)
        
        # Store references
        progress_window.status_label = status_label
        progress_window.progress_bar = progress_bar
        progress_window.percent_label = percent_label
        
        return progress_window
    
    def update_progress(self, progress_window, completed, total, current_file=""):
        """Update progress dialog (call from main thread)."""
        if not progress_window or not progress_window.winfo_exists():
            return
            
        progress_window.progress_bar['value'] = completed
        percent = int((completed / total) * 100)
        progress_window.percent_label.config(text=f"{percent}%")
        
        if current_file:
            progress_window.status_label.config(
                text=f"Processing: {current_file} ({completed}/{total})"
            )
        else:
            progress_window.status_label.config(text=f"Completed: {completed}/{total}")
    
    def create_ui(self):
        """Create the main user interface."""
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main container
        main_container = ctk.CTkFrame(self)
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # Left panel: File browser
        self.create_file_browser(main_container)
        
        # Right panel: EXIF editor
        self.create_editor_panel(main_container)
    
    def create_file_browser(self, parent):
        """Create the file browser panel with tree view."""
        browser_frame = ctk.CTkFrame(parent)
        browser_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        browser_frame.grid_columnconfigure(0, weight=1)
        browser_frame.grid_rowconfigure(1, weight=1)
        
        # Title and controls
        header_frame = ctk.CTkFrame(browser_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header_frame,
            text="📁 File Browser",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        
        # Selection info in header
        self.selection_label = ctk.CTkLabel(
            header_frame,
            text="No files selected",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.selection_label.grid(row=1, column=0, pady=2, sticky="w")
        
        # Selection buttons
        button_frame = ctk.CTkFrame(header_frame)
        button_frame.grid(row=0, column=1, rowspan=2, sticky="e")
        
        ctk.CTkButton(
            button_frame,
            text="Select All",
            width=100,
            command=self.select_all_files
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            button_frame,
            text="Deselect All",
            width=100,
            command=self.deselect_all_files
        ).pack(side="left", padx=2)
        
        # Tree and file view container
        paned = ttk.PanedWindow(browser_frame, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Configure row to take all available space
        browser_frame.grid_rowconfigure(1, weight=1)
        
        # Left: Folder tree
        tree_frame = ctk.CTkFrame(paned)
        paned.add(tree_frame, weight=1)
        
        ctk.CTkLabel(
            tree_frame,
            text="Folders",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)
        
        # Create dark style for Treeview with larger font
        style = ttk.Style()
        style.theme_use('clam')  # Use clam theme for better dark mode support
        style.configure('Treeview',
            background='#2b2b2b',
            foreground='white',
            fieldbackground='#2b2b2b',
            font=('Segoe UI', 12),
            rowheight=25
        )
        style.configure('Treeview.Heading',
            background='#1e1e1e',
            foreground='white',
            font=('Segoe UI', 12, 'bold')
        )
        style.map('Treeview',
            background=[('selected', '#4285F4')],
            foreground=[('selected', 'white')]
        )
        
        # Add scrollbars
        tree_container = tk.Frame(tree_frame)
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        v_scroll = tk.Scrollbar(tree_container, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.folder_tree = ttk.Treeview(tree_container, show='tree', yscrollcommand=v_scroll.set)
        self.folder_tree.pack(side=tk.LEFT, fill="both", expand=True)
        v_scroll.config(command=self.folder_tree.yview)
        
        self.folder_tree.bind('<<TreeviewSelect>>', self.on_folder_select)
        
        # Right: File list
        file_frame = ctk.CTkFrame(paned)
        paned.add(file_frame, weight=2)
        
        # Path label
        self.path_label = ctk.CTkLabel(
            file_frame,
            text=str(self.current_directory),
            anchor="w",
            font=ctk.CTkFont(size=12)
        )
        self.path_label.pack(pady=5, padx=5, fill="x")
        
        # Select All checkbox at top of file list
        self.select_all_var = tk.BooleanVar(value=False)
        select_all_checkbox = ctk.CTkCheckBox(
            file_frame,
            text="Select All Files",
            variable=self.select_all_var,
            command=self.toggle_select_all
        )
        select_all_checkbox.pack(pady=5, padx=5, anchor="w")
        
        # File list
        self.file_scroll = ctk.CTkScrollableFrame(file_frame)
        self.file_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Load initial directory
        self.populate_folder_tree()
        self.load_directory()
        
        # Expand to Z:\photos if it exists
        if Path('Z:/photos').exists():
            self.expand_to_path(Path('Z:/photos'))
    
    def expand_to_path(self, target_path):
        """Expand tree to show a specific path."""
        target_path = Path(target_path)
        
        # Find the drive node
        drive = str(target_path.drive) + "\\"
        drive_node = None
        
        for item in self.folder_tree.get_children():
            if self.folder_tree.item(item, 'text') == drive:
                drive_node = item
                break
        
        if not drive_node:
            return
        
        # Build path components (excluding drive)
        parts = target_path.relative_to(target_path.drive + "\\").parts
        
        current_node = drive_node
        current_path = Path(drive)
        
        # Expand each level
        for part in parts:
            current_path = current_path / part
            
            # Load children if needed
            children = self.folder_tree.get_children(current_node)
            if len(children) == 1 and self.folder_tree.item(children[0], 'text') == 'Loading...':
                self.folder_tree.delete(children[0])
                self.load_tree_children(current_node)
            
            # Find the matching child
            found = False
            for child in self.folder_tree.get_children(current_node):
                if self.folder_tree.item(child, 'text') == part:
                    current_node = child
                    found = True
                    break
            
            if not found:
                break
        
        # Select and show the final node
        if current_node:
            self.folder_tree.selection_set(current_node)
            self.folder_tree.see(current_node)
            self.folder_tree.event_generate('<<TreeviewSelect>>')
    
    def populate_folder_tree(self):
        """Populate the folder tree with drives and directories."""
        # Clear existing
        for item in self.folder_tree.get_children():
            self.folder_tree.delete(item)
        
        # Add drives (Windows)
        if platform.system() == 'Windows':
            import string
            from ctypes import windll
            
            drives = []
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
            
            for drive in drives:
                drive_path = Path(drive)
                if drive_path.exists():
                    node = self.folder_tree.insert('', 'end', text=drive, values=[str(drive_path)])
                    # Add dummy child to make it expandable
                    self.folder_tree.insert(node, 'end', text='Loading...')
        
        self.folder_tree.bind('<<TreeviewOpen>>', self.on_tree_expand)
    
    def on_tree_expand(self, event):
        """Load subdirectories when tree node is expanded."""
        item = self.folder_tree.focus()
        children = self.folder_tree.get_children(item)
        
        # If dummy child, load real children
        if len(children) == 1:
            dummy = children[0]
            if self.folder_tree.item(dummy, 'text') == 'Loading...':
                self.folder_tree.delete(dummy)
                self.load_tree_children(item)
    
    def load_tree_children(self, parent_item):
        """Load subdirectories for a tree item."""
        parent_path = Path(self.folder_tree.item(parent_item, 'values')[0])
        
        try:
            for item in sorted(parent_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    try:
                        node = self.folder_tree.insert(
                            parent_item, 
                            'end', 
                            text=item.name, 
                            values=[str(item)]
                        )
                        # Add dummy child if directory has subdirectories
                        if any(item.iterdir()):
                            self.folder_tree.insert(node, 'end', text='Loading...')
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
    
    def on_folder_select(self, event):
        """Handle folder selection in tree."""
        selection = self.folder_tree.selection()
        if selection:
            item = selection[0]
            values = self.folder_tree.item(item, 'values')
            if values:
                folder_path = Path(values[0])
                self.current_directory = folder_path
                self.load_directory()
    
    def load_directory(self):
        """Load and display files from current directory."""
        # Update path label
        self.path_label.configure(text=str(self.current_directory))
        
        # Clear existing file widgets
        for widget in self.file_scroll.winfo_children():
            widget.destroy()
        
        self.file_widgets.clear()
        self.selected_files.clear()
        self.all_files.clear()
        self.loaded_files.clear()  # Clear loaded tracking
        
        # Get image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}
        
        try:
            for item in sorted(self.current_directory.iterdir()):
                if item.is_file() and item.suffix.lower() in image_extensions:
                    self.all_files.append(item)
        except PermissionError:
            messagebox.showerror("Error", f"Permission denied: {self.current_directory}")
            return
        
        # Display files
        if not self.all_files:
            ctk.CTkLabel(
                self.file_scroll,
                text="No image files found in this directory",
                text_color="gray"
            ).pack(pady=20)
            return
        
        # Create all file widgets (instant)
        for idx, file_path in enumerate(self.all_files):
            self.create_file_item(file_path, idx, load_immediately=(idx < 15))
        
        self.update_selection_label()
    
    def create_file_item(self, file_path, index, load_immediately=False):
        """Create a file item widget with optional lazy loading."""
        item_frame = ctk.CTkFrame(self.file_scroll, height=90)
        item_frame.pack(pady=1, padx=5, fill="x")
        item_frame.pack_propagate(False)
        
        # Make frame clickable
        item_frame.bind('<Button-1>', lambda e: self.on_file_click(file_path, index, e))
        
        # Checkbox
        var = tk.BooleanVar(value=False)
        checkbox = ctk.CTkCheckBox(
            item_frame,
            text="",
            variable=var,
            width=30,
            command=lambda: self.toggle_file_selection(file_path, var)
        )
        checkbox.pack(side="left", padx=5)
        checkbox.bind('<Button-1>', lambda e: self.on_checkbox_click(file_path, index, e))
        
        # Thumbnail placeholder
        thumb_label = ctk.CTkLabel(item_frame, text="📷", width=80, height=80)
        thumb_label.pack(side="left", padx=5)
        thumb_label.bind('<Button-1>', lambda e: self.on_file_click(file_path, index, e))
        
        # Filename and date container
        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        name_label = ctk.CTkLabel(
            info_frame,
            text=file_path.name,
            anchor="w",
            font=ctk.CTkFont(size=12)
        )
        name_label.pack(anchor="w")
        name_label.bind('<Button-1>', lambda e: self.on_file_click(file_path, index, e))
        
        # Date placeholder
        date_label = ctk.CTkLabel(
            info_frame,
            text="..." if not load_immediately else "Loading...",
            anchor="w",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        date_label.pack(anchor="w")
        date_label.bind('<Button-1>', lambda e: self.on_file_click(file_path, index, e))
        
        # Store reference
        self.file_widgets[file_path] = {
            'frame': item_frame,
            'checkbox': checkbox,
            'var': var,
            'index': index,
            'date_label': date_label,
            'thumb_label': thumb_label
        }
        
        # Load immediately or queue for lazy loading
        if load_immediately:
            # Load first 15 files immediately (unthrottled)
            threading.Thread(
                target=self.load_thumbnail,
                args=(file_path, thumb_label),
                daemon=True
            ).start()
            threading.Thread(
                target=self.load_file_datetime,
                args=(file_path, date_label),
                daemon=True
            ).start()
        else:
            # Queue for throttled background loading
            self.load_executor.submit(self.lazy_load_file_data, file_path)
    
    def lazy_load_file_data(self, file_path):
        """Load thumbnail and date in background (throttled via executor)."""
        if file_path in self.loaded_files:
            return
        
        self.loaded_files.add(file_path)
        
        widget = self.file_widgets.get(file_path)
        if not widget:
            return
        
        # Load thumbnail
        try:
            img = Image.open(file_path)
            img.thumbnail((80, 80))
            photo = ImageTk.PhotoImage(img)
            self.after(0, lambda: self.update_thumbnail(widget['thumb_label'], photo))
        except:
            pass
        
        # Load EXIF date
        try:
            cmd = 'exiftool.exe' if platform.system() == 'Windows' else 'exiftool'
            args = [cmd, '-DateTimeOriginal', '-s3', str(file_path)]
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                shell=(platform.system() == 'Windows')
            )
            
            if result.returncode == 0 and result.stdout.strip():
                dt_str = result.stdout.strip()
                dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                display_text = dt.strftime("%d/%m/%Y %H:%M")
            else:
                display_text = "No date"
            
            self.after(0, lambda: widget['date_label'].configure(text=display_text))
        except:
            self.after(0, lambda: widget['date_label'].configure(text="No date"))
    
    
    def on_checkbox_click(self, file_path, index, event):
        """Handle checkbox click with modifier keys."""
        # Capture modifier state immediately before it gets lost in after_idle
        ctrl_pressed = bool(event.state & 0x0004)
        shift_pressed = bool(event.state & 0x0001)
        
        if ctrl_pressed or shift_pressed:
            # Modifiers present - handle selection immediately
            self.handle_selection(file_path, index, event)
            return "break"
        else:
            # No modifiers - use after_idle to let checkbox toggle normally first
            event.widget.after_idle(lambda: self.handle_selection(file_path, index, event))
            return "break"
    
    def on_file_click(self, file_path, index, event):
        """Handle file item click with modifier keys."""
        self.handle_selection(file_path, index, event)
    
    def handle_selection(self, file_path, index, event):
        """Handle selection with Ctrl and Shift modifiers."""
        ctrl_pressed = event.state & 0x0004  # Ctrl key
        shift_pressed = event.state & 0x0001  # Shift key
        
        if shift_pressed and self.last_selected_index is not None:
            # Range selection
            start = min(self.last_selected_index, index)
            end = max(self.last_selected_index, index)
            
            for i in range(start, end + 1):
                if i < len(self.all_files):
                    f = self.all_files[i]
                    if f in self.file_widgets:
                        self.file_widgets[f]['var'].set(True)
                        if f not in self.selected_files:
                            self.selected_files.append(f)
        
        elif ctrl_pressed:
            # Toggle individual
            widget = self.file_widgets[file_path]
            current_state = widget['var'].get()
            widget['var'].set(not current_state)
            
            if not current_state:
                if file_path not in self.selected_files:
                    self.selected_files.append(file_path)
            else:
                if file_path in self.selected_files:
                    self.selected_files.remove(file_path)
            
            self.last_selected_index = index
        
        else:
            # Single selection (deselect others)
            for f, widget in self.file_widgets.items():
                if f == file_path:
                    widget['var'].set(True)
                    if f not in self.selected_files:
                        self.selected_files.append(f)
                else:
                    widget['var'].set(False)
                    if f in self.selected_files:
                        self.selected_files.remove(f)
            
            self.last_selected_index = index
        
        self.update_selection_label()
    
    def toggle_file_selection(self, file_path, var):
        """Toggle file selection from checkbox."""
        if var.get():
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
        else:
            if file_path in self.selected_files:
                self.selected_files.remove(file_path)
        
        self.update_selection_label()
    
    def toggle_select_all(self):
        """Toggle select/deselect all files from checkbox."""
        if self.select_all_var.get():
            self.select_all_files()
        else:
            self.deselect_all_files()
    
    def select_all_files(self):
        """Select all files in current directory."""
        for file_path, widget in self.file_widgets.items():
            widget['var'].set(True)
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
        
        self.select_all_var.set(True)
        self.update_selection_label()
    
    def deselect_all_files(self):
        """Deselect all files."""
        for file_path, widget in self.file_widgets.items():
            widget['var'].set(False)
        
        self.selected_files.clear()
        self.select_all_var.set(False)
        self.update_selection_label()
    
    def load_thumbnail(self, file_path, label):
        """Load thumbnail image in background."""
        try:
            img = Image.open(file_path)
            img.thumbnail((80, 80))  # Bigger thumbnails
            photo = ImageTk.PhotoImage(img)
            self.after(0, lambda: self.update_thumbnail(label, photo))
        except Exception as e:
            pass
    
    def load_file_datetime(self, file_path, label):
        """Load DateTimeOriginal from file in background."""
        try:
            cmd = 'exiftool.exe' if platform.system() == 'Windows' else 'exiftool'
            args = [cmd, '-DateTimeOriginal', '-s3', str(file_path)]
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                shell=(platform.system() == 'Windows')
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse the datetime (format: 2024:01:17 14:30:25)
                dt_str = result.stdout.strip()
                dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                display_text = dt.strftime("%d/%m/%Y %H:%M")
            else:
                display_text = "No date set"
            
            # Update label on main thread
            self.after(0, lambda: label.configure(text=display_text))
        except Exception as e:
            self.after(0, lambda: label.configure(text="No date set"))
    
    def update_thumbnail(self, label, photo):
        """Update thumbnail label with image."""
        label.configure(image=photo, text="")
        label.image = photo
    
    def update_selection_label(self):
        """Update the selection count label."""
        count = len(self.selected_files)
        if count == 0:
            text = "No files selected"
        elif count == 1:
            text = "1 file selected"
        else:
            text = f"{count} files selected"
        
        self.selection_label.configure(text=text)
    
    def create_editor_panel(self, parent):
        """Create the EXIF editor panel."""
        editor_frame = ctk.CTkFrame(parent)
        editor_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(1, weight=1)  # Make tabview expand
        
        # Title
        ctk.CTkLabel(
            editor_frame,
            text="✏️ EXIF Editor",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, pady=10, sticky="w", padx=10)
        
        # Tabview for different operations
        self.tabview = ctk.CTkTabview(editor_frame)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Date/Time Tab
        self.create_datetime_tab()
        
        # GPS Location Tab
        self.create_gps_tab()
        
        # Sanitise Tab
        self.create_sanitise_tab()
    
    def create_datetime_tab(self):
        """Create the date/time editing tab."""
        tab = self.tabview.add("📅 Date/Time")
        tab.grid_columnconfigure(0, weight=1)
        
        # Instructions
        ctk.CTkLabel(
            tab,
            text="Set date for selected files\nTime will auto-increment by filename order",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(pady=10, padx=10)
        
        # Date input
        date_frame = ctk.CTkFrame(tab)
        date_frame.pack(pady=10, padx=10, fill="x")
        
        # Date input with picker
        ctk.CTkLabel(date_frame, text="Date:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.date_entry = ctk.CTkEntry(date_frame, placeholder_text="DD/MM/YYYY")
        self.date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(
            date_frame,
            text="📅",
            width=40,
            command=self.show_date_picker
        ).grid(row=0, column=2, padx=5, pady=5)
        date_frame.grid_columnconfigure(1, weight=1)
        
        # Time input with picker
        ctk.CTkLabel(date_frame, text="Start Time:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.time_entry = ctk.CTkEntry(date_frame, placeholder_text="HH:MM")
        self.time_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(
            date_frame,
            text="🕐",
            width=40,
            command=self.show_time_picker
        ).grid(row=1, column=2, padx=5, pady=5)
        
        # Increment input
        ctk.CTkLabel(date_frame, text="Increment (sec):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.increment_entry = ctk.CTkEntry(date_frame, placeholder_text="1")
        self.increment_entry.insert(0, "1")
        self.increment_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        # Set today button
        button_frame = ctk.CTkFrame(tab)
        button_frame.pack(pady=5, padx=10, fill="x")
        
        ctk.CTkButton(
            button_frame,
            text="📆 Use Today's Date",
            command=self.set_today,
            width=200
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="📝 Use File's Date/Time",
            command=self.use_file_datetime,
            width=200,
            fg_color="#2196F3",
            hover_color="#1976D2"
        ).pack(side="left", padx=5)
        
        # Fields to update
        fields_frame = ctk.CTkFrame(tab)
        fields_frame.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(
            fields_frame,
            text="Fields to update:",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.field_vars = {}
        fields = [
            ("DateTimeOriginal", "Date/Time Original (EXIF)"),
            ("CreateDate", "Create Date (EXIF)"),
            ("ModifyDate", "Modify Date (EXIF)"),
            ("GPSDateStamp", "GPS Date Stamp (EXIF)"),
            ("FileModifyDate", "File Modified Date (EXIF)"),
            ("WindowsCreated", "Windows Created Date"),
            ("WindowsModified", "Windows Modified Date")
        ]
        
        for field, label in fields:
            var = tk.BooleanVar(value=True)
            self.field_vars[field] = var
            ctk.CTkCheckBox(fields_frame, text=label, variable=var).pack(pady=2, padx=10, anchor="w")
        
        # Apply button
        ctk.CTkButton(
            tab,
            text="✅ Apply Date/Time",
            command=self.apply_datetime,
            fg_color="green",
            hover_color="darkgreen",
            height=40
        ).pack(pady=20, padx=10, fill="x")
    
    def create_gps_tab(self):
        """Create the GPS location tab."""
        tab = self.tabview.add("📍 GPS Location")
        tab.grid_columnconfigure(0, weight=1)
        
        # Instructions
        ctk.CTkLabel(
            tab,
            text="Interactive Google Maps Coordinate Picker",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=15, padx=10)
        
        # Google Maps button
        ctk.CTkButton(
            tab,
            text="🗺️ Open Interactive Google Maps",
            command=self.open_interactive_maps,
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4285F4",
            hover_color="#357AE8"
        ).pack(pady=10, padx=20, fill="x")
        
        # Instructions frame
        instructions_frame = ctk.CTkFrame(tab)
        instructions_frame.pack(pady=15, padx=20, fill="x")
        
        ctk.CTkLabel(
            instructions_frame,
            text="How it works:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        ).pack(pady=5, padx=10, anchor="w")
        
        instructions = [
            "1. Click 'Open Interactive Google Maps' button above",
            "2. Search for a location in the search box that appears",
            "3. Click anywhere on the map to drop a pin",
            "4. Coordinates will be shown below the map",
            "5. Copy the coordinates and paste them below",
            "6. Click 'Apply GPS Location' to update your photos"
        ]
        
        for instruction in instructions:
            ctk.CTkLabel(
                instructions_frame,
                text=instruction,
                anchor="w",
                text_color="gray",
                font=ctk.CTkFont(size=11)
            ).pack(pady=2, padx=20, anchor="w")
        
        # Manual entry frame
        manual_frame = ctk.CTkFrame(tab)
        manual_frame.pack(pady=15, padx=20, fill="x")
        manual_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            manual_frame,
            text="Paste Coordinates Here:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(manual_frame, text="Latitude:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, padx=10, pady=8, sticky="w"
        )
        self.lat_entry = ctk.CTkEntry(
            manual_frame,
            placeholder_text="e.g., -31.959910",
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self.lat_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        self.lat_entry.insert(0, "-31.959910")  # Default home location
        
        ctk.CTkLabel(manual_frame, text="Longitude:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, padx=10, pady=8, sticky="w"
        )
        self.lon_entry = ctk.CTkEntry(
            manual_frame,
            placeholder_text="e.g., 116.030874",
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self.lon_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
        self.lon_entry.insert(0, "116.030874")  # Default home location
        
        # Quick Location Presets
        presets_frame = ctk.CTkFrame(tab)
        presets_frame.pack(pady=15, padx=20, fill="x")
        
        ctk.CTkLabel(
            presets_frame,
            text="Quick Locations:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=5, anchor="w", padx=10)
        
        # Create preset buttons
        buttons_container = ctk.CTkFrame(presets_frame, fg_color="transparent")
        buttons_container.pack(fill="x", padx=10, pady=5)
        
        for preset in GPS_PRESETS:
            ctk.CTkButton(
                buttons_container,
                text=preset["name"],
                command=lambda p=preset: self.apply_gps_preset(p),
                height=35,
                font=ctk.CTkFont(size=12)
            ).pack(side="left", padx=5, pady=5)
        
        # Edit presets button
        ctk.CTkButton(
            buttons_container,
            text="⚙️ Edit Presets",
            command=self.edit_gps_presets,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color="gray40",
            hover_color="gray30"
        ).pack(side="left", padx=5, pady=5)
        
        # Apply button
        ctk.CTkButton(
            tab,
            text="✅ Apply GPS Location to Selected Files",
            command=self.apply_gps,
            fg_color="green",
            hover_color="darkgreen",
            height=50,
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=20, padx=20, fill="x")

    def open_interactive_maps(self):
        """Open an interactive Google Maps page in browser."""
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
    
    def start_preset_save_polling(self):
        """Poll for preset save requests from the browser."""
        def check_preset_save():
            try:
                # Check both Downloads and temp folders
                downloads_file = Path.home() / 'Downloads' / 'immich_preset_save.json'
                temp_file = Path(tempfile.gettempdir()) / 'immich_preset_save.json'
                
                preset_file = None
                if downloads_file.exists():
                    preset_file = downloads_file
                elif temp_file.exists():
                    preset_file = temp_file
                
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
                        f"Saved '{data['name']}' to Button {data['slot'] + 1}!\n\nRestart the app to see the changes."
                    )
            except Exception as e:
                print(f"Error checking preset save: {e}")
            
            # Check again in 1 second
            if hasattr(self, '_polling_active') and self._polling_active:
                self.after(1000, check_preset_save)
        
        self._polling_active = True
        self.after(1000, check_preset_save)
    
    def start_coordinate_polling(self):
        """Poll for new coordinates from the browser."""
        def check_clipboard():
            try:
                clipboard = self.clipboard_get()
                if ',' in clipboard:
                    parts = clipboard.split(',')
                    if len(parts) == 2:
                        try:
                            lat = float(parts[0].strip())
                            lon = float(parts[1].strip())
                            
                            current_lat = self.lat_entry.get().strip()
                            current_lon = self.lon_entry.get().strip()
                            
                            if parts[0].strip() != current_lat or parts[1].strip() != current_lon:
                                self.lat_entry.delete(0, 'end')
                                self.lat_entry.insert(0, parts[0].strip())
                                self.lon_entry.delete(0, 'end')
                                self.lon_entry.insert(0, parts[1].strip())
                                
                                self.lat_entry.configure(border_color="green")
                                self.lon_entry.configure(border_color="green")
                                self.after(1000, lambda: self.lat_entry.configure(border_color=""))
                                self.after(1000, lambda: self.lon_entry.configure(border_color=""))
                        except ValueError:
                            pass
            except:
                pass
            
            if hasattr(self, '_polling_active') and self._polling_active:
                self.after(500, check_clipboard)
        
        self._polling_active = True
        self.after(500, check_clipboard)

    def start_preset_save_polling(self):
        """Poll for preset save requests from the browser."""
        def check_preset_save():
            try:
                downloads_file = Path.home() / 'Downloads' / 'immich_preset_save.json'
                
                if downloads_file.exists():
                    import json
                    with open(downloads_file, 'r') as f:
                        data = json.load(f)
                    
                    update_gps_preset(data['slot'], data['name'], data['lat'], data['lon'])
                    
                    downloads_file.unlink()
                    
                    messagebox.showinfo(
                        "Preset Saved",
                        f"Saved '{data['name']}' to Button {data['slot'] + 1}!\n\nRestart the app to see the changes."
                    )
            except Exception as e:
                print(f"Error checking preset save: {e}")
            
            if hasattr(self, '_polling_active') and self._polling_active:
                self.after(1000, check_preset_save)
        
        self._polling_active = True
        self.after(1000, check_preset_save)
    
    def create_sanitise_tab(self):
        """Create the sanitise for sharing tab."""
        tab = self.tabview.add("🧹 Sanitise")
        tab.grid_columnconfigure(0, weight=1)
        
        # Instructions
        ctk.CTkLabel(
            tab,
            text="Remove sensitive EXIF data before sharing",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=20, padx=10)
        
        # What will be removed
        info_frame = ctk.CTkFrame(tab)
        info_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        ctk.CTkLabel(
            info_frame,
            text="This will remove:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(pady=10, padx=10, anchor="w")
        
        items_to_remove = [
            "• All GPS location data",
            "• Camera make and model",
            "• Camera serial number",
            "• Lens information",
            "• Copyright information",
            "• Author/Artist information",
            "• Software used",
            "• All metadata except essential image data"
        ]
        
        for item in items_to_remove:
            ctk.CTkLabel(
                info_frame,
                text=item,
                anchor="w",
                text_color="gray"
            ).pack(pady=2, padx=20, anchor="w")
        
        # Warning
        warning_frame = ctk.CTkFrame(tab, fg_color="darkred")
        warning_frame.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(
            warning_frame,
            text="⚠️ Warning: This action cannot be undone!\nMake sure you have backups.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        ).pack(pady=10, padx=10)
        
        # Apply button
        ctk.CTkButton(
            tab,
            text="🧹 Sanitise Selected Files",
            command=self.sanitise_files,
            fg_color="orange",
            hover_color="darkorange",
            height=40
        ).pack(pady=20, padx=10, fill="x")
    
    def set_today(self):
        """Set date to today."""
        today = datetime.now()
        self.date_entry.delete(0, 'end')
        self.date_entry.insert(0, today.strftime("%d/%m/%Y"))
        self.time_entry.delete(0, 'end')
        self.time_entry.insert(0, today.strftime("%H:%M"))
    
    def use_file_datetime(self):
        """Extract DateTimeOriginal from first selected file and populate fields."""
        if not self.selected_files:
            messagebox.showwarning("No Selection", "Please select at least one file first")
            return
        
        # Get first selected file
        file_path = self.selected_files[0]
        
        try:
            # Run exiftool to get DateTimeOriginal
            cmd = 'exiftool.exe' if platform.system() == 'Windows' else 'exiftool'
            args = [cmd, '-DateTimeOriginal', '-s3', str(file_path)]
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                shell=(platform.system() == 'Windows')
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse the datetime (format: 2024:01:17 14:30:25)
                dt_str = result.stdout.strip()
                dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                
                # Populate fields
                self.date_entry.delete(0, 'end')
                self.date_entry.insert(0, dt.strftime("%d/%m/%Y"))
                self.time_entry.delete(0, 'end')
                self.time_entry.insert(0, dt.strftime("%H:%M"))
            else:
                messagebox.showwarning(
                    "No Date Found",
                    f"No DateTimeOriginal found in {file_path.name}"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read EXIF data:\n{e}")
    
    def show_date_picker(self):
        """Show calendar popup to pick a date."""
        picker_window = tk.Toplevel(self)
        picker_window.title("Select Date")
        picker_window.geometry("400x400")
        picker_window.transient(self)
        picker_window.grab_set()
        
        # Position relative to main window, not screen centre
        self.update_idletasks()
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()
        
        # Centre on the main window
        x = main_x + (main_width // 2) - 200
        y = main_y + (main_height // 2) - 200
        picker_window.geometry(f'400x400+{x}+{y}')
        
        # Instructions
        tk.Label(
            picker_window,
            text="Select a Date",
            font=('Segoe UI', 14, 'bold')
        ).pack(pady=10)
        
        # Calendar
        cal = Calendar(
            picker_window,
            selectmode='day',
            date_pattern='dd/mm/yyyy',
            font=('Segoe UI', 11),
            selectbackground='#4285F4',
            selectforeground='white',
            headersbackground='#4285F4',
            headersforeground='white',
            normalbackground='white',
            normalforeground='black',
            weekendbackground='white',
            weekendforeground='black'
        )
        cal.pack(pady=20, padx=20, fill="both", expand=True)
        
        def select_date():
            selected = cal.get_date()
            self.date_entry.delete(0, 'end')
            self.date_entry.insert(0, selected)
            picker_window.destroy()
        
        # Buttons
        btn_frame = tk.Frame(picker_window)
        btn_frame.pack(pady=15)
        
        tk.Button(
            btn_frame,
            text="✓ Select",
            command=select_date,
            font=('Segoe UI', 12, 'bold'),
            bg='#4CAF50',
            fg='white',
            padx=30,
            pady=10,
            relief='flat',
            cursor='hand2'
        ).pack(side="left", padx=10)
        
        tk.Button(
            btn_frame,
            text="✗ Cancel",
            command=picker_window.destroy,
            font=('Segoe UI', 12),
            padx=30,
            pady=10,
            relief='flat',
            cursor='hand2'
        ).pack(side="left", padx=10)
    
    def show_time_picker(self):
        """Show time picker popup."""
        picker_window = tk.Toplevel(self)
        picker_window.title("Select Time")
        picker_window.geometry("400x250")
        picker_window.transient(self)
        picker_window.grab_set()
        
        # Position relative to main window, not screen centre
        self.update_idletasks()
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()
        
        # Centre on the main window
        x = main_x + (main_width // 2) - 200
        y = main_y + (main_height // 2) - 125
        picker_window.geometry(f'400x250+{x}+{y}')
        
        # Instructions
        tk.Label(
            picker_window,
            text="Select a Time",
            font=('Segoe UI', 14, 'bold')
        ).pack(pady=15)
        
        # Time controls
        time_frame = tk.Frame(picker_window)
        time_frame.pack(pady=30)
        
        # Hour
        tk.Label(
            time_frame,
            text="Hour:",
            font=('Segoe UI', 13)
        ).grid(row=0, column=0, padx=15, pady=5)
        
        hour_var = tk.StringVar(value="12")
        hour_spin = tk.Spinbox(
            time_frame,
            from_=0,
            to=23,
            textvariable=hour_var,
            width=10,
            format="%02.0f",
            font=('Segoe UI', 16, 'bold'),
            justify='center'
        )
        hour_spin.grid(row=0, column=1, padx=15, pady=5)
        
        # Minute
        tk.Label(
            time_frame,
            text="Minute:",
            font=('Segoe UI', 13)
        ).grid(row=0, column=2, padx=15, pady=5)
        
        minute_var = tk.StringVar(value="00")
        minute_spin = tk.Spinbox(
            time_frame,
            from_=0,
            to=59,
            textvariable=minute_var,
            width=10,
            format="%02.0f",
            font=('Segoe UI', 16, 'bold'),
            justify='center'
        )
        minute_spin.grid(row=0, column=3, padx=15, pady=5)
        
        def select_time():
            time_str = f"{hour_var.get().zfill(2)}:{minute_var.get().zfill(2)}"
            self.time_entry.delete(0, 'end')
            self.time_entry.insert(0, time_str)
            picker_window.destroy()
        
        # Buttons
        btn_frame = tk.Frame(picker_window)
        btn_frame.pack(pady=20)
        
        tk.Button(
            btn_frame,
            text="✓ Select",
            command=select_time,
            font=('Segoe UI', 12, 'bold'),
            bg='#4CAF50',
            fg='white',
            padx=30,
            pady=10,
            relief='flat',
            cursor='hand2'
        ).pack(side="left", padx=10)
        
        tk.Button(
            btn_frame,
            text="✗ Cancel",
            command=picker_window.destroy,
            font=('Segoe UI', 12),
            padx=30,
            pady=10,
            relief='flat',
            cursor='hand2'
        ).pack(side="left", padx=10)
        
    def apply_datetime(self):
        """Apply date/time to selected files with parallel processing."""
        if not self.selected_files:
            messagebox.showwarning("No Selection", "Please select files first")
            return
        
        # Parse date and time
        date_str = self.date_entry.get().strip()
        time_str = self.time_entry.get().strip()
        increment_str = self.increment_entry.get().strip()
        
        if not date_str or not time_str:
            messagebox.showerror("Error", "Please enter both date and time")
            return
        
        try:
            # Add :00 for seconds if only HH:MM provided
            if len(time_str.split(':')) == 2:
                time_str += ":00"
            base_dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
            increment = int(increment_str)
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid date/time format: {e}")
            return
        
        # Get selected fields
        selected_fields = [field for field, var in self.field_vars.items() if var.get()]
        
        if not selected_fields:
            messagebox.showwarning("No Fields", "Please select at least one field to update")
            return
        
        # Sort files by name and assign timestamps
        sorted_files = sorted(self.selected_files, key=lambda p: p.name)
        file_datetime_pairs = [
            (file_path, base_dt + timedelta(seconds=i * increment))
            for i, file_path in enumerate(sorted_files)
        ]
        
        # Confirm
        confirm = messagebox.askyesno(
            "Confirm",
            f"Apply date/time to {len(sorted_files)} files?\n\n"
            f"Starting: {base_dt.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"Increment: {increment} seconds\n"
            f"Fields: {len(selected_fields)} selected\n\n"
            f"🚀 Processing with {min(8, len(sorted_files))} parallel workers"
        )
        
        if not confirm:
            return
        
        # Run in background thread
        def process_files():
            # Show progress dialog
            self.after(0, lambda: setattr(self, '_progress_window', 
                                         self.show_progress_dialog("Processing Files", len(file_datetime_pairs))))
            
            completed = 0
            errors = []
            
            # Use ThreadPoolExecutor for parallel processing
            # 8 workers = sweet spot for I/O-bound ExifTool processes
            max_workers = min(8, len(file_datetime_pairs))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.set_file_datetime, file_path, dt, selected_fields): (file_path, dt)
                    for file_path, dt in file_datetime_pairs
                }
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_file):
                    file_path, dt = future_to_file[future]
                    try:
                        future.result()  # Raises exception if task failed
                        completed += 1
                    except Exception as e:
                        errors.append((file_path.name, str(e)))
                    
                    # Update progress on main thread
                    self.after(0, lambda c=completed, f=file_path.name: 
                              self.update_progress(getattr(self, '_progress_window', None), 
                                                  c, len(file_datetime_pairs), f))
            
            # Close progress dialog and show result
            self.after(0, lambda: self._finish_apply_datetime(completed, errors))
        
        # Start background thread
        threading.Thread(target=process_files, daemon=True).start()
    
    def _finish_apply_datetime(self, success_count, errors):
        """Finish datetime application and show results."""
        # Close progress window
        if hasattr(self, '_progress_window') and self._progress_window:
            try:
                self._progress_window.destroy()
            except:
                pass
        
        # Show results
        if errors:
            error_msg = f"Updated {success_count} file(s)\n\n"
            error_msg += f"Failed {len(errors)} file(s):\n"
            for name, error in errors[:5]:  # Show first 5 errors
                error_msg += f"• {name}: {error}\n"
            if len(errors) > 5:
                error_msg += f"... and {len(errors) - 5} more"
            messagebox.showwarning("Partial Success", error_msg)
        else:
            self.show_auto_close_message("Success", f"Updated {success_count} file(s) 🚀")

    def apply_datetime(self):
        """Apply date/time to selected files with parallel processing."""
        if not self.selected_files:
            messagebox.showwarning("No Selection", "Please select files first")
            return
        
        # Parse date and time
        date_str = self.date_entry.get().strip()
        time_str = self.time_entry.get().strip()
        increment_str = self.increment_entry.get().strip()
        
        if not date_str or not time_str:
            messagebox.showerror("Error", "Please enter both date and time")
            return
        
        try:
            # Add :00 for seconds if only HH:MM provided
            if len(time_str.split(':')) == 2:
                time_str += ":00"
            base_dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
            increment = int(increment_str)
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid date/time format: {e}")
            return
        
        # Get selected fields
        selected_fields = [field for field, var in self.field_vars.items() if var.get()]
        
        if not selected_fields:
            messagebox.showwarning("No Fields", "Please select at least one field to update")
            return
        
        # Sort files by name and assign timestamps
        sorted_files = sorted(self.selected_files, key=lambda p: p.name)
        file_datetime_pairs = [
            (file_path, base_dt + timedelta(seconds=i * increment))
            for i, file_path in enumerate(sorted_files)
        ]
        
        # Confirm
        confirm = messagebox.askyesno(
            "Confirm",
            f"Apply date/time to {len(sorted_files)} files?\n\n"
            f"Starting: {base_dt.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"Increment: {increment} seconds\n"
            f"Fields: {len(selected_fields)} selected\n\n"
            f"🚀 Processing with {min(8, len(sorted_files))} parallel workers"
        )
        
        if not confirm:
            return
        
        # Run in background thread
        def process_files():
            # Show progress dialog
            self.after(0, lambda: setattr(self, '_progress_window', 
                                         self.show_progress_dialog("Processing Files", len(file_datetime_pairs))))
            
            completed = 0
            errors = []
            
            # Use ThreadPoolExecutor for parallel processing
            # 8 workers = sweet spot for I/O-bound ExifTool processes
            max_workers = min(8, len(file_datetime_pairs))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.set_file_datetime, file_path, dt, selected_fields): (file_path, dt)
                    for file_path, dt in file_datetime_pairs
                }
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_file):
                    file_path, dt = future_to_file[future]
                    try:
                        future.result()  # Raises exception if task failed
                        completed += 1
                    except Exception as e:
                        errors.append((file_path.name, str(e)))
                    
                    # Update progress on main thread
                    self.after(0, lambda c=completed, f=file_path.name: 
                              self.update_progress(getattr(self, '_progress_window', None), 
                                                  c, len(file_datetime_pairs), f))
            
            # Close progress dialog and show result
            self.after(0, lambda: self._finish_apply_datetime(completed, errors))
        
        # Start background thread
        threading.Thread(target=process_files, daemon=True).start()
    
    def _finish_apply_datetime(self, success_count, errors):
        """Finish datetime application and show results."""
        # Close progress window
        if hasattr(self, '_progress_window') and self._progress_window:
            try:
                self._progress_window.destroy()
            except:
                pass
        
        # Show results
        if errors:
            error_msg = f"Updated {success_count} file(s)\n\n"
            error_msg += f"Failed {len(errors)} file(s):\n"
            for name, error in errors[:5]:  # Show first 5 errors
                error_msg += f"• {name}: {error}\n"
            if len(errors) > 5:
                error_msg += f"... and {len(errors) - 5} more"
            messagebox.showwarning("Partial Success", error_msg)
        else:
            self.show_auto_close_message("Success", f"Updated {success_count} file(s) 🚀")

    
    def set_file_datetime(self, file_path, dt, fields):
        """Set date/time fields using ExifTool and Windows API."""
        # Handle EXIF fields
        exif_fields = [f for f in fields if f not in ['WindowsCreated', 'WindowsModified']]
        
        if exif_fields:
            cmd = 'exiftool.exe' if platform.system() == 'Windows' else 'exiftool'
            args = [cmd, '-overwrite_original']
            
            # Format datetime for EXIF
            dt_str = dt.strftime("%Y:%m:%d %H:%M:%S")
            
            for field in exif_fields:
                args.append(f"-{field}={dt_str}")
            
            args.append(str(file_path))
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                shell=(platform.system() == 'Windows')
            )
            
            if result.returncode != 0:
                raise Exception(result.stderr)
        
        # Handle Windows file timestamps
        if 'WindowsCreated' in fields or 'WindowsModified' in fields:
            self.set_windows_timestamps(file_path, dt, fields)
    
    def set_windows_timestamps(self, file_path, dt, fields):
        """Set Windows file Created and Modified timestamps."""
        try:
            # Convert datetime to Windows FILETIME (must convert to timestamp first)
            timestamp = pywintypes.Time(dt.timestamp())
            
            # Open file handle with write access
            handle = win32file.CreateFile(
                str(file_path),
                win32con.GENERIC_WRITE,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_ATTRIBUTE_NORMAL,
                None
            )
            
            try:
                # Set timestamps
                # SetFileTime(handle, CreationTime, LastAccessTime, LastWriteTime)
                created_time = timestamp if 'WindowsCreated' in fields else None
                modified_time = timestamp if 'WindowsModified' in fields else None
                
                # Pass times in correct order: creation, access, modified
                win32file.SetFileTime(handle, created_time, None, modified_time)
            finally:
                handle.Close()
                
        except Exception as e:
            raise Exception(f"Failed to set Windows timestamps: {e}")
    
    def apply_gps_preset(self, preset):
        """Apply a GPS preset to the coordinate fields."""
        self.lat_entry.delete(0, 'end')
        self.lat_entry.insert(0, str(preset["lat"]))
        self.lon_entry.delete(0, 'end')
        self.lon_entry.insert(0, str(preset["lon"]))
        
        # Flash the fields to show update
        self.lat_entry.configure(border_color="green")
        self.lon_entry.configure(border_color="green")
        self.after(1000, lambda: self.lat_entry.configure(border_color=""))
        self.after(1000, lambda: self.lon_entry.configure(border_color=""))
    
    def edit_gps_presets(self):
        """Open the GPS presets file for editing."""
        preset_file = Path(__file__).parent / 'gps_presets.py'
        
        try:
            if platform.system() == 'Windows':
                os.startfile(str(preset_file))
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', str(preset_file)])
            else:  # Linux
                subprocess.call(['xdg-open', str(preset_file)])
            
            messagebox.showinfo(
                "Edit GPS Presets",
                "The GPS presets file has been opened.\n\n"
                "Edit the locations and save the file.\n"
                "Restart the application to see your changes."
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Could not open presets file:\n{e}\n\n"
                f"File location: {preset_file}"
            )
    
    def apply_gps(self):
        """Apply GPS coordinates to selected files with parallel processing."""
        if not self.selected_files:
            messagebox.showwarning("No Selection", "Please select files first")
            return
        
        lat_str = self.lat_entry.get().strip()
        lon_str = self.lon_entry.get().strip()
        
        if not lat_str or not lon_str:
            messagebox.showerror("Error", "Please enter both latitude and longitude")
            return
        
        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid coordinates format")
            return
        
        # Confirm
        confirm = messagebox.askyesno(
            "Confirm",
            f"Apply GPS coordinates to {len(self.selected_files)} files?\n\n"
            f"Latitude: {lat}\n"
            f"Longitude: {lon}\n\n"
            f"🚀 Processing with {min(8, len(self.selected_files))} parallel workers"
        )
        
        if not confirm:
            return
        
        # Run in background thread
        def process_files():
            # Show progress dialog
            self.after(0, lambda: setattr(self, '_gps_progress_window', 
                                         self.show_progress_dialog("Applying GPS Coordinates", len(self.selected_files))))
            
            completed = 0
            errors = []
            
            # Use ThreadPoolExecutor for parallel processing
            max_workers = min(8, len(self.selected_files))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.set_exif_gps, file_path, lat, lon): file_path
                    for file_path in self.selected_files
                }
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        future.result()  # Raises exception if task failed
                        completed += 1
                    except Exception as e:
                        errors.append((file_path.name, str(e)))
                    
                    # Update progress on main thread
                    self.after(0, lambda c=completed, f=file_path.name: 
                              self.update_progress(getattr(self, '_gps_progress_window', None), 
                                                  c, len(self.selected_files), f))
            
            # Close progress dialog and show result
            self.after(0, lambda: self._finish_apply_gps(completed, errors))
        
        # Start background thread
        threading.Thread(target=process_files, daemon=True).start()

    def _finish_apply_gps(self, success_count, errors):
            """Finish GPS application and show results."""
            # Close progress window
            if hasattr(self, '_gps_progress_window') and self._gps_progress_window:
                try:
                    self._gps_progress_window.destroy()
                except:
                    pass
            
            # Show results
            if errors:
                error_msg = f"Updated {success_count} file(s)\n\n"
                error_msg += f"Failed {len(errors)} file(s):\n"
                for name, error in errors[:5]:  # Show first 5 errors
                    error_msg += f"• {name}: {error}\n"
                if len(errors) > 5:
                    error_msg += f"... and {len(errors) - 5} more"
                messagebox.showwarning("Partial Success", error_msg)
            else:
                self.show_auto_close_message("Success", f"Updated {success_count} file(s) 🚀")
    
    def set_exif_gps(self, file_path, lat, lon):
        """Set GPS coordinates using ExifTool."""
        cmd = 'exiftool.exe' if platform.system() == 'Windows' else 'exiftool'
        
        # Determine GPS reference directions
        lat_ref = 'N' if lat >= 0 else 'S'
        lon_ref = 'E' if lon >= 0 else 'W'
        
        # Use absolute values for the coordinates
        abs_lat = abs(lat)
        abs_lon = abs(lon)
        
        args = [
            cmd,
            '-overwrite_original',
            f"-GPSLatitude={abs_lat}",
            f"-GPSLatitudeRef={lat_ref}",
            f"-GPSLongitude={abs_lon}",
            f"-GPSLongitudeRef={lon_ref}",
            str(file_path)
        ]
        
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            shell=(platform.system() == 'Windows')
        )
        
        if result.returncode != 0:
            raise Exception(result.stderr)
    
    def sanitise_files(self):
        """Remove sensitive EXIF data from selected files with parallel processing."""
        if not self.selected_files:
            messagebox.showwarning("No Selection", "Please select files first")
            return
        
        # Confirm
        confirm = messagebox.askyesno(
            "Confirm Sanitisation",
            f"⚠️ Remove all sensitive EXIF data from {len(self.selected_files)} files?\n\n"
            "This will remove:\n"
            "• All GPS data\n"
            "• Camera information\n"
            "• Copyright/Author data\n"
            "• And more...\n\n"
            "This cannot be undone!\n\n"
            f"🚀 Processing with {min(8, len(self.selected_files))} parallel workers"
        )
        
        if not confirm:
            return
        
        # Run in background thread
        def process_files():
            # Show progress dialog
            self.after(0, lambda: setattr(self, '_sanitise_progress_window', 
                                         self.show_progress_dialog("Sanitising Files", len(self.selected_files))))
            
            completed = 0
            errors = []
            
            # Use ThreadPoolExecutor for parallel processing
            max_workers = min(8, len(self.selected_files))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.sanitise_exif, file_path): file_path
                    for file_path in self.selected_files
                }
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        future.result()  # Raises exception if task failed
                        completed += 1
                    except Exception as e:
                        errors.append((file_path.name, str(e)))
                    
                    # Update progress on main thread
                    self.after(0, lambda c=completed, f=file_path.name: 
                              self.update_progress(getattr(self, '_sanitise_progress_window', None), 
                                                  c, len(self.selected_files), f))
            
            # Close progress dialog and show result
            self.after(0, lambda: self._finish_sanitise(completed, errors))
        
        # Start background thread
        threading.Thread(target=process_files, daemon=True).start()
    
    def sanitise_exif(self, file_path):
        """Remove all EXIF data except essential info using ExifTool."""
        cmd = 'exiftool.exe' if platform.system() == 'Windows' else 'exiftool'
        
        args = [
            cmd,
            '-overwrite_original',
            '-all=',
            str(file_path)
        ]
        
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            shell=(platform.system() == 'Windows')
        )
        
        if result.returncode != 0:
            raise Exception(result.stderr)

    def _finish_sanitise(self, success_count, errors):
        """Finish sanitisation and show results."""
        # Close progress window
        if hasattr(self, '_sanitise_progress_window') and self._sanitise_progress_window:
            try:
                self._sanitise_progress_window.destroy()
            except:
                pass
        
        # Show results
        if errors:
            error_msg = f"Sanitised {success_count} file(s)\n\n"
            error_msg += f"Failed {len(errors)} file(s):\n"
            for name, error in errors[:5]:  # Show first 5 errors
                error_msg += f"• {name}: {error}\n"
            if len(errors) > 5:
                error_msg += f"... and {len(errors) - 5} more"
            messagebox.showwarning("Partial Success", error_msg)
        else:
            self.show_auto_close_message("Success", f"Sanitised {success_count} file(s) 🚀")

def main():
    """Main entry point."""
    app = ExifEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
