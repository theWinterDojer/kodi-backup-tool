#!/usr/bin/env python3
"""
Kodi Backup Tool - Cross-Platform GUI Application
Modern replacement for the original Windows batch script with enhanced features.
"""

import customtkinter as ctk
import sys
import threading
import os
import json
from pathlib import Path
from backup_engine import KodiBackupEngine

# Configure CustomTkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class KodiBackupApp:
    # Class constants for cleanup settings
    DEFAULT_CLEANUP_KEYS = ['thumbnails', 'tmdb_blur', 'tmdb_crop', 'addon_packages']
    OPTIONAL_CLEANUP_KEYS = ['tmdb_database', 'umbrella_cache', 'umbrella_search', 'cocoscrapers_cache']
    
    def __init__(self):
        # Create main window
        self.root = ctk.CTk()
        self.root.title("Kodi Backup Tool v1.0")
        self.root.geometry("550x730")
        self.root.minsize(500, 570)
        
        # Set window icon (use embedded icon in executable)
        try:
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller executable - use the embedded icon
                self.root.iconbitmap(default=sys.executable)
            else:
                # Running as Python script - try to find icon.ico for development
                icon_path = Path(__file__).parent / "icon.ico"
                if icon_path.exists():
                    self.root.iconbitmap(str(icon_path))
        except Exception:
            # If icon loading fails, continue without it
            pass
        
        # Initialize state
        self.backup_in_progress = False
        
        # Configuration file path (in same directory as executable)
        # Handle both development and PyInstaller executable scenarios
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable
            app_dir = Path(sys.executable).parent
        else:
            # Running as Python script
            app_dir = Path(__file__).parent
        self.config_file = app_dir / "kodi_backup_config.json"
        
        # Initialize cleanup settings with defaults (matches batch script)
        self.cleanup_settings = {
            'thumbnails': True,
            'tmdb_blur': True,
            'tmdb_crop': True,
            'addon_packages': True,
            # Optional cleanup (unchecked by default)
            'tmdb_database': False,
            'umbrella_cache': False,
            'umbrella_search': False,
            'cocoscrapers_cache': False
        }
        
        # Load saved configuration (before UI setup so paths can be used)
        self.config = self._load_config()
        
        # Load saved cleanup settings if available
        if 'cleanup_settings' in self.config:
            saved_cleanup = self.config['cleanup_settings']
            # Only update DEFAULT cleanup settings from saved config
            # Optional settings always reset to False for safety
            for key, value in saved_cleanup.items():
                if key in self.DEFAULT_CLEANUP_KEYS and key in self.cleanup_settings:
                    self.cleanup_settings[key] = value
            # Ensure optional settings are always reset to False
            for key in self.OPTIONAL_CLEANUP_KEYS:
                if key in self.cleanup_settings:
                    self.cleanup_settings[key] = False
        
        # Initialize UI
        self.setup_ui()
        
        # Show config load status after UI is ready
        if self.config_file.exists() and hasattr(self, 'status_text'):
            default_enabled = sum(1 for key in self.DEFAULT_CLEANUP_KEYS if self.cleanup_settings.get(key, False))
            self.update_status(
                f"CONFIGURATION LOADED\n\n"
                f"Loaded from: {self.config_file.name}\n"
                f"Default cleanup settings: {default_enabled}/{len(self.DEFAULT_CLEANUP_KEYS)} enabled\n"
                f"Optional cleanup settings: Reset to unchecked"
            )
        
    def setup_ui(self):
        """Create the main user interface"""
        
        # Header (compact)
        header_frame = ctk.CTkFrame(self.root)
        header_frame.pack(fill="x", padx=15, pady=10)
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="Kodi Backup Tool", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)
        
        subtitle_label = ctk.CTkLabel(
            header_frame, 
            text="Cross-platform cleaning, backup and restore solution",
            font=ctk.CTkFont(size=12)
        )
        subtitle_label.pack(pady=(0, 10))
        
        # Configuration fields (compact)
        config_frame = ctk.CTkFrame(self.root)
        config_frame.pack(fill="x", padx=15, pady=5)
        
        # Configuration fields with helper method  
        # Use default placeholders, then set actual values after creation
        default_kodi_placeholder = os.path.expanduser(r"~\AppData\Roaming\Kodi")
        default_backup_placeholder = os.path.expanduser(r"~\Documents\Kodi-Backup")
        
        self.kodi_path_entry = self._create_path_field(config_frame, "Kodi Directory:", default_kodi_placeholder, self.browse_kodi_directory)
        self.backup_path_entry = self._create_path_field(config_frame, "Backup Destination:", default_backup_placeholder, self.browse_backup_directory)
        
        # Set actual saved values (not placeholders)
        saved_kodi_path = self.config.get('kodi_path', '')
        saved_backup_path = self.config.get('backup_path', '')
        
        if saved_kodi_path:
            self.kodi_path_entry.delete(0, 'end')
            self.kodi_path_entry.insert(0, saved_kodi_path)
            
        if saved_backup_path:
            self.backup_path_entry.delete(0, 'end')
            self.backup_path_entry.insert(0, saved_backup_path)
        
        # Backup Label
        label_widget = ctk.CTkLabel(
            config_frame, 
            text="Backup Label (optional):", 
            font=ctk.CTkFont(size=13, weight="bold")
        )
        label_widget.pack(anchor="w", padx=12, pady=(0, 5))
        self.label_entry = ctk.CTkEntry(config_frame, height=32, placeholder_text="", font=ctk.CTkFont(size=12))
        self.label_entry.pack(fill="x", padx=12, pady=(0, 15))
        
        # Set saved label if available
        saved_label = self.config.get('backup_label', '')
        if saved_label:
            self.label_entry.insert(0, saved_label)
        
        # Actions Section (bottom - pack first to ensure visibility)
        actions_frame = ctk.CTkFrame(self.root, height=65)
        actions_frame.pack(side="bottom", fill="x", padx=15, pady=5)
        actions_frame.pack_propagate(False)  # Prevent shrinking
        
        # Buttons in horizontal layout - use place to center vertically
        button_container = ctk.CTkFrame(actions_frame)
        button_container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.95)
        
        # Start Backup button
        self.backup_btn = ctk.CTkButton(
            button_container, 
            text="Clean + Backup", 
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35,
            command=self.start_backup
        )
        self.backup_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        # Restore button (dark green)
        self.restore_btn = ctk.CTkButton(
            button_container, 
            text="Restore", 
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35,
            fg_color="#2d5a2d",
            hover_color="#1e3f1e",
            command=self.start_restore
        )
        self.restore_btn.pack(side="left", fill="x", expand=True, padx=(2, 4))
        
        # Settings button
        self.settings_btn = ctk.CTkButton(
            button_container, 
            text="Settings", 
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35,
            fg_color="gray30",
            hover_color="gray20",
            command=self.open_settings
        )
        self.settings_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))
        
        # Status Display (middle section - fills remaining space)
        status_frame = ctk.CTkFrame(self.root)
        status_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        ctk.CTkLabel(
            status_frame, 
            text="Status", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 8))
        
        self.status_text = ctk.CTkTextbox(status_frame, font=ctk.CTkFont(size=13))
        self.status_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        
        # Enable text selection and copying with right-click context menu
        self._setup_status_text_context_menu()
        
        # Set initial welcome message with better formatting
        welcome_message = """KODI BACKUP TOOL - READY
        
INSTRUCTIONS:
• Set your Kodi directory path above
• Set your backup destination path above  
• Click 'Clean + Backup' to begin
"""
        
        self.status_text.insert("0.0", welcome_message)
    
    def _setup_status_text_context_menu(self):
        """Set up right-click context menu for status text area"""
        import tkinter as tk
        
        # Create context menu
        self.status_context_menu = tk.Menu(self.root, tearoff=0)
        self.status_context_menu.add_command(label="Copy Selected", command=self._copy_selected_text)
        self.status_context_menu.add_command(label="Copy All", command=self._copy_all_text)
        self.status_context_menu.add_separator()
        self.status_context_menu.add_command(label="Select All", command=self._select_all_text)
        
        # Bind right-click to show context menu
        self.status_text.bind("<Button-3>", self._show_status_context_menu)
        
        # Add keyboard shortcuts
        self.status_text.bind("<Control-a>", lambda e: self._select_all_text())
        self.status_text.bind("<Control-A>", lambda e: self._select_all_text())
        self.status_text.bind("<Control-c>", lambda e: self._copy_selected_text_keyboard())
        self.status_text.bind("<Control-C>", lambda e: self._copy_selected_text_keyboard())
    
    def _show_status_context_menu(self, event):
        """Show context menu at cursor position"""
        try:
            self.status_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.status_context_menu.grab_release()
    
    def _copy_selected_text(self):
        """Copy selected text to clipboard"""
        try:
            selected_text = self.status_text.get("sel.first", "sel.last")
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
                self.update_status("COPIED\n\nSelected text copied to clipboard")
        except:
            self.update_status("COPY FAILED\n\nNo text selected. Select text first, then right-click → Copy Selected")
    
    def _copy_selected_text_keyboard(self):
        """Copy selected text to clipboard (keyboard shortcut - no status message)"""
        try:
            selected_text = self.status_text.get("sel.first", "sel.last")
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
        except:
            pass  # Silently fail for keyboard shortcuts
    
    def _copy_all_text(self):
        """Copy all status text to clipboard"""
        all_text = self.status_text.get("0.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(all_text)
        self.update_status("ALL TEXT COPIED\n\nEntire status log copied to clipboard")
    
    def _select_all_text(self):
        """Select all text in status area"""
        self.status_text.tag_add("sel", "0.0", "end")
        self.status_text.mark_set("insert", "0.0")
        self.status_text.see("insert")
    
    def _create_path_field(self, parent, label_text, placeholder_text, browse_command):
        """Helper method to create path input fields with browse buttons"""
        # Add top padding for first field, normal for others
        top_padding = 12 if label_text == "Kodi Directory:" else 0
        ctk.CTkLabel(parent, text=label_text, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(top_padding, 5))
        path_frame = ctk.CTkFrame(parent)
        path_frame.pack(fill="x", padx=12, pady=(0, 8))
        
        entry = ctk.CTkEntry(path_frame, height=32, placeholder_text=placeholder_text, font=ctk.CTkFont(size=12))
        entry.pack(side="left", fill="x", expand=True, padx=(5, 8), pady=5)
        
        browse_btn = ctk.CTkButton(path_frame, text="Browse", width=70, height=32, command=browse_command)
        browse_btn.pack(side="right", padx=(0, 5), pady=5)
        
        return entry
    
    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Only show status if UI is ready (status_text exists)
                    if hasattr(self, 'status_text'):
                        self.update_status(f"Configuration loaded from {self.config_file.name}")
                    return config
        except Exception as e:
            # Only show status if UI is ready (status_text exists)
            if hasattr(self, 'status_text'):
                self.update_status(f"Error loading config: {e}")
        
        # Return empty config if file doesn't exist or failed to load
        return {}
    
    def _save_config(self):
        """Save current configuration to JSON file"""
        try:
            # Only save default cleanup settings, not optional ones
            persistent_cleanup = {
                key: self.cleanup_settings[key] for key in self.DEFAULT_CLEANUP_KEYS
                # Optional settings are NOT saved - they reset each launch
            }
            
            config = {
                'kodi_path': self.kodi_path_entry.get().strip(),
                'backup_path': self.backup_path_entry.get().strip(),
                'backup_label': self.label_entry.get().strip(),
                'last_backup_file': self.config.get('last_backup_file', ''),
                'cleanup_settings': persistent_cleanup
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            self.update_status(f"Error saving config: {e}")
            return False
    
    def _confirm_kodi_closed(self):
        """Confirm that Kodi is closed before backup"""
        import tkinter.messagebox as msgbox
        
        # Match the exact message from the batch script
        message = ("IMPORTANT: Ensure Kodi is CLOSED on your device before proceeding!\n\n"
                  "Backing up while Kodi is running can cause:\n"
                  "• File corruption\n"
                  "• Incomplete backup\n"
                  "• Database locks\n\n"
                  "Confirm Kodi is CLOSED and click OK to continue.")
        
        result = msgbox.askokcancel(
            "Kodi Must Be Closed", 
            message,
            icon="warning"
        )
        
        if result:
            self.update_status("KODI CONFIRMATION\n\nUser confirmed Kodi is closed. Proceeding with backup...")
            return True
        else:
            self.update_status("BACKUP CANCELED\n\nPlease close Kodi and try again.")
            return False
        
    def browse_kodi_directory(self):
        """Browse for Kodi directory"""
        self._browse_directory("Select Kodi Installation Directory", self.kodi_path_entry, "Kodi directory")
    
    def browse_backup_directory(self):
        """Browse for backup destination"""
        self._browse_directory("Select Backup Destination Directory", self.backup_path_entry, "Backup destination")
    
    def _browse_directory(self, title, entry_widget, description):
        """Helper method for directory browsing"""
        from tkinter import filedialog
        directory = filedialog.askdirectory(title=title)
        if directory:
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, directory)
            self.update_status(f"{description} updated:\n{directory}")
    
    def update_status(self, message):
        """Update the status display (thread-safe)"""
        # Use after_idle to ensure thread safety
        self.root.after_idle(lambda: self._update_status_ui(message))
    
    def _update_status_ui(self, message):
        """Internal method to update UI (called from main thread)"""
        current_text = self.status_text.get("0.0", "end-1c")
        if current_text.strip():
            # Add spacing and formatting for new messages
            if message.startswith(("ERROR", "FAILED")):
                # Error messages get extra spacing
                self.status_text.insert("end", "\n\n" + message)
            elif message.startswith(("SUCCESS", "COMPLETED", "STARTING", "CONFIGURATION")):
                # Success/action messages get normal spacing  
                self.status_text.insert("end", "\n\n" + message)
            elif message.startswith(("=" * 10)):
                # Section dividers get extra spacing
                self.status_text.insert("end", "\n\n" + message)
            else:
                # Regular messages get single line spacing
                self.status_text.insert("end", "\n" + message)
        else:
            # Clear existing text and insert new message
            self.status_text.delete("0.0", "end")
            self.status_text.insert("0.0", message)
        
        # Auto-scroll to bottom
        self.status_text.see("end")
    
    def set_backup_button_state(self, enabled=True):
        """Enable or disable backup button (thread-safe)"""
        state = "normal" if enabled else "disabled"
        text = "Clean + Backup" if enabled else "Backing up..."
        self.root.after_idle(lambda: self.backup_btn.configure(state=state, text=text))
    
    def start_backup(self):
        """Start the backup process"""
        if self.backup_in_progress:
            return
            
        kodi_path = self.kodi_path_entry.get().strip()
        backup_path = self.backup_path_entry.get().strip()
        label = self.label_entry.get().strip() or "backup"
        
        if not kodi_path or not backup_path:
            error_msg = """ERROR: MISSING PATHS

Please provide both required paths:
• Kodi Directory: Use Browse button or type path manually
• Backup Destination: Use Browse button or type path manually

Both paths are required to continue."""
            self.update_status(error_msg)
            return
        
        # IMPORTANT: Kodi must be closed before backup 
        if not self._confirm_kodi_closed():
            return
        
        # Validate paths exist
        if not Path(kodi_path).exists():
            error_msg = f"""ERROR: KODI DIRECTORY NOT FOUND

Path does not exist:
{kodi_path}

Please check the path and try again."""
            self.update_status(error_msg)
            return
            
        if not Path(backup_path).exists():
            error_msg = f"""ERROR: BACKUP DESTINATION NOT FOUND

Path does not exist:
{backup_path}

Please check the path and try again."""
            self.update_status(error_msg)
            return
        
        # Start backup in separate thread
        self.backup_in_progress = True
        self.set_backup_button_state(False)
        
        backup_thread = threading.Thread(
            target=self._perform_backup_thread,
            args=(kodi_path, backup_path, label),
            daemon=True
        )
        backup_thread.start()
    
    def _perform_backup_thread(self, kodi_path, backup_path, label):
        """Perform backup in separate thread"""
        try:
            startup_msg = f"""STARTING BACKUP PROCESS

CONFIGURATION:
• Kodi Directory: {kodi_path}
• Backup Destination: {backup_path}
• Label: {label}

INITIALIZING..."""
            self.update_status(startup_msg)
            
            # Create backup engine for this operation  
            backup_engine = KodiBackupEngine(self.update_status)
            
            # Get cleanup settings (use current instance settings)
            cleanup_settings = self.cleanup_settings
            
            # Perform backup with status updates
            results = backup_engine.perform_full_backup(kodi_path, backup_path, label, None, cleanup_settings)
            
            # Display summary
            self._display_backup_summary(results, backup_engine)
            
        except Exception as e:
            self.update_status(f"CRITICAL ERROR: {e}")
        finally:
            self._reset_ui_state()
    
    def _display_backup_summary(self, results, backup_engine):
        """Display formatted backup results"""
        divider = "=" * 50
        self.update_status(divider)
        
        if results['success']:
            # Save the full path of the created backup file for restore defaults
            backup_destination = self.backup_path_entry.get().strip()
            full_backup_path = str(Path(backup_destination) / results['filename'])
            self.config['last_backup_file'] = full_backup_path
            self._save_config()  # Persist the last backup file immediately
            
            summary_msg = f"""BACKUP COMPLETED SUCCESSFULLY

BACKUP DETAILS:
• Backup File: {results['filename']}
• Original Size: {backup_engine.format_size(results['size_before_cleanup'])}
• Space Freed: {backup_engine.format_size(results['space_freed'])}
• Final Backup Size: {backup_engine.format_size(results['final_backup_size'])}"""
            
            if results['size_after_cleanup'] > 0:
                compression_ratio = (results['final_backup_size'] / results['size_after_cleanup']) * 100
                summary_msg += f"\n• Compression Ratio: {compression_ratio:.1f}%"
            
            summary_msg += f"\n\nYour Kodi backup is ready!"
            
        else:
            summary_msg = f"""BACKUP FAILED

Error Details:
{results['error_message']}

Please check the error and try again."""
            
        self.update_status(summary_msg)
        self.update_status(divider)
    
    def _reset_ui_state(self):
        """Reset UI to ready state"""
        self.backup_in_progress = False
        self.set_backup_button_state(True)
    
    def start_restore(self):
        """Start the restore process"""
        self._create_restore_dialog()
    
    def _create_restore_dialog(self):
        """Create restore dialog window"""
        restore_window = ctk.CTkToplevel(self.root)
        restore_window.title("Restore Kodi Backup")
        restore_window.geometry("450x350")
        restore_window.minsize(450, 350)
        restore_window.transient(self.root)
        restore_window.grab_set()  # Make it modal
        
        # Center the window
        restore_window.update_idletasks()
        x = (restore_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (restore_window.winfo_screenheight() // 2) - (350 // 2)
        restore_window.geometry(f"450x350+{x}+{y}")
        
        # Main content area
        content_frame = ctk.CTkFrame(restore_window)
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Backup file selection
        backup_label = ctk.CTkLabel(
            content_frame,
            text="Backup File:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        backup_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        backup_frame = ctk.CTkFrame(content_frame)
        backup_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Get smart default for backup file
        default_backup = self.config.get('last_backup_file', '')
        if not default_backup or not Path(default_backup).exists():
            # Try to find newest backup in backup directory
            backup_dir = self.config.get('backup_path', '')
            if backup_dir and Path(backup_dir).exists():
                backup_files = list(Path(backup_dir).glob('*.zip'))
                if backup_files:
                    default_backup = str(max(backup_files, key=lambda f: f.stat().st_mtime))
        
        self.restore_backup_entry = ctk.CTkEntry(
            backup_frame, 
            height=32, 
            font=ctk.CTkFont(size=12)
        )
        self.restore_backup_entry.pack(side="left", fill="x", expand=True, padx=(8, 5), pady=8)
        
        if default_backup:
            self.restore_backup_entry.insert(0, default_backup)
        
        backup_browse_btn = ctk.CTkButton(
            backup_frame, 
            text="Browse", 
            width=70, 
            height=32,
            command=lambda: self._browse_backup_file(restore_window)
        )
        backup_browse_btn.pack(side="right", padx=(0, 8), pady=8)
        
        # Target directory selection
        target_label = ctk.CTkLabel(
            content_frame,
            text="Restore to Kodi Directory:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        target_label.pack(anchor="w", padx=10, pady=(0, 5))
        
        target_frame = ctk.CTkFrame(content_frame)
        target_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Default to current Kodi directory
        default_target = self.config.get('kodi_path', '')
        
        self.restore_target_entry = ctk.CTkEntry(
            target_frame, 
            height=32, 
            font=ctk.CTkFont(size=12)
        )
        self.restore_target_entry.pack(side="left", fill="x", expand=True, padx=(8, 5), pady=8)
        
        if default_target:
            self.restore_target_entry.insert(0, default_target)
        
        target_browse_btn = ctk.CTkButton(
            target_frame, 
            text="Browse", 
            width=70, 
            height=32,
            command=lambda: self._browse_restore_directory(restore_window)
        )
        target_browse_btn.pack(side="right", padx=(0, 8), pady=8)
        
        # Warning message (no background frame)
        warning_text = (
            "⚠️  WARNING: This will completely overwrite all current\n"
            "Kodi settings and data in the target directory!"
        )
        warning_label = ctk.CTkLabel(
            content_frame,
            text=warning_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffaa44",  # Orange warning color
            justify="center"
        )
        warning_label.pack(padx=10, pady=(15, 25))
        
        # Bottom buttons section (match Settings dialog style)
        button_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_container.pack(side="bottom", fill="x", padx=10, pady=10)
        
        restore_btn = ctk.CTkButton(
            button_container,
            text="Restore",
            command=lambda: self._confirm_restore(restore_window),
            height=40,
            fg_color="#2d5a2d",
            hover_color="#1e3f1e",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        restore_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        cancel_btn = ctk.CTkButton(
            button_container,
            text="Cancel",
            command=restore_window.destroy,
            height=40,
            fg_color="gray30",
            hover_color="gray20",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        cancel_btn.pack(side="right", fill="x", expand=True, padx=(8, 0))
    
    def _browse_backup_file(self, parent_window):
        """Browse for backup file (.zip)"""
        from tkinter import filedialog
        
        # Start in backup directory if available
        initial_dir = ""
        backup_path = self.config.get('backup_path', '')
        if backup_path and Path(backup_path).exists():
            initial_dir = backup_path
        
        file_path = filedialog.askopenfilename(
            parent=parent_window,
            title="Select Kodi Backup File",
            initialdir=initial_dir,
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        
        if file_path:
            self.restore_backup_entry.delete(0, 'end')
            self.restore_backup_entry.insert(0, file_path)
    
    def _browse_restore_directory(self, parent_window):
        """Browse for restore target directory"""
        from tkinter import filedialog
        
        directory = filedialog.askdirectory(
            parent=parent_window,
            title="Select Kodi Installation Directory"
        )
        
        if directory:
            self.restore_target_entry.delete(0, 'end')
            self.restore_target_entry.insert(0, directory)
    
    def _confirm_restore(self, restore_window):
        """Validate paths and confirm restore operation"""
        backup_file = self.restore_backup_entry.get().strip()
        target_dir = self.restore_target_entry.get().strip()
        
        # Basic validation
        if not backup_file or not target_dir:
            self.update_status("RESTORE ERROR\n\nPlease provide both backup file and target directory.")
            return
        
        if not Path(backup_file).exists():
            self.update_status(f"RESTORE ERROR\n\nBackup file not found:\n{backup_file}")
            return
        
        if not Path(target_dir).exists():
            self.update_status(f"RESTORE ERROR\n\nTarget directory not found:\n{target_dir}")
            return
        
        # IMPORTANT: Kodi must be closed before restore
        if not self._confirm_kodi_closed():
            return
        
        # Save the selected backup file as the new last_backup_file
        self.config['last_backup_file'] = backup_file
        self._save_config()
        
        # Close dialog and start restore process
        restore_window.destroy()
        
        # Start restore in separate thread
        restore_thread = threading.Thread(
            target=self._perform_restore_thread,
            args=(backup_file, target_dir),
            daemon=True
        )
        restore_thread.start()
    
    def _perform_restore_thread(self, backup_file, target_dir):
        """Perform restore in separate thread"""
        try:
            # Display initial status matching your specification
            startup_msg = f"""RESTORE OPERATION STARTED

Source: {Path(backup_file).name}
Target: {target_dir}

Validating backup file..."""
            self.update_status(startup_msg)
            
            # Create restore engine for this operation
            restore_engine = KodiBackupEngine(self.update_status)
            
            # Perform restore with status updates
            results = restore_engine.perform_restore(backup_file, target_dir)
            
            # Display final summary matching your specification
            self._display_restore_summary(results, backup_file, target_dir, restore_engine)
            
        except Exception as e:
            self.update_status(f"CRITICAL ERROR: {e}")
    
    def _display_restore_summary(self, results, backup_file, target_dir, restore_engine):
        """Display formatted restore results matching specification"""
        self.update_status("")
        
        if results['success']:
            summary_msg = f"""Restored Files:
• userdata: {results['userdata_files']:,} files
• addons: {results['addons_files']:,} files
• Total size: {restore_engine.format_size(results['total_size'])}

Your Kodi backup has been restored!
Restart Kodi to use the restored configuration."""
            
        else:
            summary_msg = f"""RESTORE FAILED

Error Details:
{results['error_message']}

Please check the error and try again."""
            
        self.update_status(summary_msg)
    
    def open_settings(self):
        """Open settings dialog"""
        # Don't spam status when opening settings
        
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Backup Settings")
        settings_window.geometry("480x520")  # More compact size
        settings_window.minsize(480, 520)    # Set minimum size
        settings_window.transient(self.root)
        settings_window.grab_set()  # Make it modal
        
        # Center the window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (480 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (520 // 2)
        settings_window.geometry(f"480x520+{x}+{y}")
        
        # Cleanup Options Section (no frame, cleaner look)
        cleanup_label = ctk.CTkLabel(
            settings_window, 
            text="Cleanup Options", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        cleanup_label.pack(pady=(15, 8))
        
        # Cleanup checkboxes
        self.cleanup_vars = {}
        
        # Default cleanup options (always enabled in batch script)
        default_cleanup_options = [
            ("thumbnails", "Delete Thumbnails (userdata/Thumbnails)"),
            ("tmdb_blur", "Delete TMDb Helper blur cache"),
            ("tmdb_crop", "Delete TMDb Helper crop cache"),
            ("addon_packages", "Delete cached addon packages")
        ]
        
        for key, description in default_cleanup_options:
            var = ctk.BooleanVar(value=self.cleanup_settings[key])
            self.cleanup_vars[key] = var
            
            checkbox = ctk.CTkCheckBox(
                settings_window,
                text=description,
                variable=var,
                font=ctk.CTkFont(size=12)
            )
            checkbox.pack(anchor="w", padx=25, pady=1)
        
        # Separator for optional cleanup
        separator_label = ctk.CTkLabel(
            settings_window,
            text="Optional Cleanup:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray70"
        )
        separator_label.pack(anchor="w", padx=25, pady=(10, 3))
        
        # Optional cleanup options (commented out in batch script)
        optional_cleanup_options = [
            ("tmdb_database", "Delete TMDbHelper database_07 (will rebuild)"),
            ("umbrella_cache", "Delete Umbrella cache.db"),
            ("umbrella_search", "Delete Umbrella search.db"),
            ("cocoscrapers_cache", "Delete cocoscrapers cache.db")
        ]
        
        for key, description in optional_cleanup_options:
            var = ctk.BooleanVar(value=self.cleanup_settings[key])
            self.cleanup_vars[key] = var
            
            checkbox = ctk.CTkCheckBox(
                settings_window,
                text=description,
                variable=var,
                font=ctk.CTkFont(size=12),
                text_color="gray80"  # Slightly dimmed to show they're optional
            )
            checkbox.pack(anchor="w", padx=40, pady=1)  # Extra indent
        
        # Path Management Section
        paths_label = ctk.CTkLabel(
            settings_window,
            text="Path Management",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        paths_label.pack(pady=(18, 8))
        
        # Save current paths button  
        save_paths_btn = ctk.CTkButton(
            settings_window,
            text="Save Current Paths",
            command=lambda: self._save_current_paths(settings_window),
            height=32,
            width=180
        )
        save_paths_btn.pack(pady=3)
        
        # Clear paths button (revert to launch state)
        clear_paths_btn = ctk.CTkButton(
            settings_window,
            text="Clear Paths",
            command=lambda: self._clear_paths(settings_window),
            height=32,
            width=180,
            fg_color="gray40",
            hover_color="gray30"
        )
        clear_paths_btn.pack(pady=3)
        
        # Bottom buttons section
        button_container = ctk.CTkFrame(settings_window, fg_color="transparent")
        button_container.pack(side="bottom", fill="x", padx=15, pady=10)
        
        save_btn = ctk.CTkButton(
            button_container,
            text="Save Settings",
            command=lambda: self._save_settings(settings_window),
            height=40,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        cancel_btn = ctk.CTkButton(
            button_container,
            text="Cancel",
            command=lambda: self._cancel_settings(settings_window),
            height=40,
            fg_color="gray30",
            hover_color="gray20",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        cancel_btn.pack(side="right", fill="x", expand=True, padx=(8, 0))
    
    def _save_current_paths(self, settings_window):
        """Save current paths as defaults"""
        kodi_path = self.kodi_path_entry.get().strip()
        backup_path = self.backup_path_entry.get().strip()
        label = self.label_entry.get().strip()
        
        if kodi_path and backup_path:
            # Save configuration to file
            if self._save_config():
                save_msg = f"""PATHS SAVED

Configuration saved:
• Kodi Directory: {kodi_path}
• Backup Destination: {backup_path}
• Label: {label}

These settings will be restored when you restart the app."""
                self.update_status(save_msg)
            else:
                self.update_status("SAVE FAILED\n\nError writing configuration file.")
            settings_window.lift()  # Bring settings window back to front
        else:
            self.update_status("SAVE FAILED\n\nPlease fill in both paths before saving.")
    
    def _clear_paths(self, settings_window):
        """Clear all paths back to launch state (empty with placeholder text)"""
        self.kodi_path_entry.delete(0, 'end')
        self.backup_path_entry.delete(0, 'end')  
        self.label_entry.delete(0, 'end')
        
        self.update_status("PATHS CLEARED\n\nReady for new configuration.")
        settings_window.lift()  # Bring settings window back to front
    

    def _save_settings(self, settings_window):
        """Save all settings to application state"""
        # Update stored cleanup settings from dialog
        for key, var in self.cleanup_vars.items():
            self.cleanup_settings[key] = var.get()
        
        # Save configuration to file (includes cleanup settings)
        config_saved = self._save_config()
        
        # Count enabled cleanup options
        enabled_count = sum(1 for enabled in self.cleanup_settings.values() if enabled)
        total_count = len(self.cleanup_settings)
        
        if config_saved:
            status_msg = f"SETTINGS SAVED\n\n{enabled_count}/{total_count} cleanup options enabled"
        else:
            status_msg = (
                f"SETTINGS UPDATED\n\n"
                f"{enabled_count}/{total_count} cleanup options enabled\n"
                f"Warning: Could not save to config file"
            )
        
        self.update_status(status_msg)
        settings_window.destroy()
    
    def _cancel_settings(self, settings_window):
        """Cancel settings dialog without saving changes"""
        self.update_status("No changes were saved.")
        settings_window.destroy()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Application entry point"""
    try:
        app = KodiBackupApp()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication closed by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
