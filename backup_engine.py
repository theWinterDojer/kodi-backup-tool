#!/usr/bin/env python3
"""
Kodi Backup Engine - Cross-Platform Implementation
Converts the Windows batch script logic to Python for cross-platform compatibility.
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Tuple


class KodiBackupEngine:
    """Cross-platform Kodi backup engine based on the original batch script logic."""
    
    def __init__(self, progress_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the backup engine.
        
        Args:
            progress_callback: Optional function to call with status updates
        """
        self.progress_callback = progress_callback or self._default_callback
        
    def _default_callback(self, message: str) -> None:
        """Default progress callback that prints to console."""
        print(f"[BACKUP] {message}")
    
    def _update_progress(self, message: str) -> None:
        """Send progress update to callback."""
        self.progress_callback(message)
    
    def validate_kodi_directory(self, kodi_path: str) -> bool:
        """
        Validate that the provided path is a valid Kodi installation.
        
        Args:
            kodi_path: Path to Kodi installation directory
            
        Returns:
            True if valid Kodi directory, False otherwise
        """
        kodi_dir = Path(kodi_path)
        
        # Check if userdata directory exists (key indicator of Kodi installation)
        userdata_path = kodi_dir / "userdata"
        addons_path = kodi_dir / "addons"
        
        if not userdata_path.exists():
            self._update_progress(f"ERROR: Invalid Kodi directory - userdata folder not found: {kodi_path}")
            return False
            
        self._update_progress(f"Valid Kodi directory found: {kodi_path}")
        return True
    
    def format_size(self, size_bytes: int) -> str:
        """
        Format size in bytes to human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string (e.g., "1.23 MB")
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/(1024**2):.2f} MB"
        else:
            return f"{size_bytes/(1024**3):.2f} GB"
    
    def cleanup_cache_files(self, kodi_path: str, cleanup_settings: Dict[str, bool] = None) -> Tuple[Dict[str, bool], int]:
        """
        Clean up cache and temporary files to reduce backup size.
        Based on the original batch script cleanup logic.
        
        Args:
            kodi_path: Path to Kodi installation
            cleanup_settings: Dict of cleanup options (None = use defaults)
            
        Returns:
            Tuple of (cleanup_results_dict, total_space_freed_bytes)
        """
        # Default cleanup settings (matches batch script enabled operations)
        if cleanup_settings is None:
            cleanup_settings = {
                'thumbnails': True,
                'tmdb_blur': True,
                'tmdb_crop': True,
                'addon_packages': True,
                'tmdb_database': False,
                'umbrella_cache': False,
                'umbrella_search': False,
                'cocoscrapers_cache': False
            }
        
        results = {}
        total_space_freed = 0
        kodi_dir = Path(kodi_path)
        
        # Define all cleanup targets (both default and optional)
        all_cleanup_targets = {
            'thumbnails': {
                'name': 'Thumbnails',
                'path': kodi_dir / "userdata" / "Thumbnails",
                'description': 'userdata/Thumbnails (Kodi rebuilds automatically)',
                'is_directory': True
            },
            'tmdb_blur': {
                'name': 'TMDbHelper blur cache',
                'path': kodi_dir / "userdata" / "addon_data" / "plugin.video.themoviedb.helper" / "blur_v2",
                'description': 'TMDbHelper blur cache',
                'is_directory': True
            },
            'tmdb_crop': {
                'name': 'TMDbHelper crop cache',
                'path': kodi_dir / "userdata" / "addon_data" / "plugin.video.themoviedb.helper" / "crop_v2",
                'description': 'TMDbHelper crop cache',
                'is_directory': True
            },
            'addon_packages': {
                'name': 'Addon packages',
                'path': kodi_dir / "addons" / "packages",
                'description': 'addons/packages (cached addon ZIPs)',
                'is_directory': True
            },
            # Optional cleanup targets (matches commented lines in batch script)
            'tmdb_database': {
                'name': 'TMDbHelper database',
                'path': kodi_dir / "userdata" / "addon_data" / "plugin.video.themoviedb.helper" / "database_07",
                'description': 'TMDbHelper database_07 (will rebuild)',
                'is_directory': True
            },
            'umbrella_cache': {
                'name': 'Umbrella cache',
                'path': kodi_dir / "userdata" / "addon_data" / "plugin.video.umbrella" / "cache.db",
                'description': 'Umbrella cache.db',
                'is_directory': False
            },
            'umbrella_search': {
                'name': 'Umbrella search',
                'path': kodi_dir / "userdata" / "addon_data" / "plugin.video.umbrella" / "search.db",
                'description': 'Umbrella search.db',
                'is_directory': False
            },
            'cocoscrapers_cache': {
                'name': 'Cocoscrapers cache',
                'path': kodi_dir / "userdata" / "addon_data" / "script.module.cocoscrapers" / "cache.db",
                'description': 'cocoscrapers cache.db',
                'is_directory': False
            }
        }
        
        self._update_progress("Cleaning cache/temp folders...")
        
        # Give user time to see what's happening
        import time
        time.sleep(2)
        
        # Process cleanup targets based on settings
        for key, target in all_cleanup_targets.items():
            if not cleanup_settings.get(key, False):
                results[target['name']] = False
                self._update_progress(f"Skipped {target['description']} (disabled in settings)")
                continue
                
            try:
                if target['path'].exists():
                    # Calculate size before deletion
                    size_freed = 0
                    if target['is_directory']:
                        # Use fast size calculation for directories
                        try:
                            for root, dirs, files in os.walk(target['path']):
                                for file in files:
                                    try:
                                        file_path = os.path.join(root, file)
                                        size_freed += os.path.getsize(file_path)
                                    except (OSError, IOError):
                                        continue
                        except (OSError, IOError):
                            pass
                        shutil.rmtree(target['path'])
                    else:
                        try:
                            size_freed = target['path'].stat().st_size
                        except (OSError, IOError):
                            size_freed = 0
                        target['path'].unlink()
                    
                    total_space_freed += size_freed
                    results[target['name']] = True
                    self._update_progress(f"Deleted {target['description']}")
                    time.sleep(0.5)  # Pause after successful deletion
                else:
                    results[target['name']] = False
                    self._update_progress(f"Skipped {target['description']} (not found)")
                    
            except Exception as e:
                results[target['name']] = False
                self._update_progress(f"Failed to delete {target['description']}: {e}")
        
        # Create cleanup summary
        items_cleaned = sum(1 for success in results.values() if success)
        total_items = len(results)
        
        self._update_progress("Cache cleanup complete")
        self._update_progress("")
        self._update_progress(f"Cleanup Summary: {items_cleaned}/{total_items} items cleaned, {self.format_size(total_space_freed)} freed")
        
        return results, total_space_freed
    
    def create_backup_filename(self, label: str = "backup") -> str:
        """
        Create backup filename with timestamp and label.
        
        Args:
            label: Custom label for the backup
            
        Returns:
            Formatted filename (e.g., "kodi.bkup_2024-01-15_Umbrella+AF2.zip")
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"kodi.bkup_{date_str}_{label}.zip"
    
    def create_backup_archive(self, kodi_path: str, backup_destination: str, 
                            filename: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Tuple[bool, int]:
        """
        Create compressed backup archive of Kodi installation.
        
        Args:
            kodi_path: Path to Kodi installation
            backup_destination: Destination directory for backup
            filename: Backup filename
            progress_callback: Optional callback for progress updates (current_files, total_files)
            
        Returns:
            Tuple of (success_boolean, total_uncompressed_size_bytes)
        """
        kodi_dir = Path(kodi_path)
        backup_dir = Path(backup_destination)
        backup_file = backup_dir / filename
        
        # Ensure backup directory exists
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Directories to backup (same as batch script)
        backup_dirs = [
            kodi_dir / "userdata",
            kodi_dir / "addons"
        ]
        
        self._update_progress(f"Creating backup with compression...")
        self._update_progress(f"Output: {filename}")
        self._update_progress("")
        
        try:
            total_uncompressed_size = 0
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zipf:
                current_file = 0
                last_progress_update = 0
                
                for backup_dir_path in backup_dirs:
                    if backup_dir_path.exists():
                        dir_name = backup_dir_path.name
                        self._update_progress(f"Backing up {dir_name} directory...")
                        
                        # Use os.walk for better network performance - single traversal
                        for root, dirs, files in os.walk(backup_dir_path):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    # Get file size before adding to archive
                                    file_size = os.path.getsize(file_path)
                                    total_uncompressed_size += file_size
                                    
                                    # Calculate relative path for archive
                                    rel_path = os.path.relpath(file_path, kodi_path)
                                    zipf.write(file_path, rel_path)
                                    current_file += 1
                                    
                                    # Show progress every 1000 files to give user feedback without spam
                                    if current_file - last_progress_update >= 1000:
                                        self._update_progress(f"Processing... {current_file} files archived")
                                        last_progress_update = current_file
                                        
                                except Exception as e:
                                    # Silently skip problem files
                                    continue
            
            # Get final backup size
            backup_size = backup_file.stat().st_size
            
            return True, total_uncompressed_size
            
        except Exception as e:
            self._update_progress(f"ERROR: Failed to create backup archive: {e}")
            return False, 0
    
    def perform_full_backup(self, kodi_path: str, backup_destination: str, 
                          label: str = "backup", archive_progress_callback: Optional[Callable[[int, int], None]] = None,
                          cleanup_settings: Optional[Dict[str, bool]] = None) -> Dict:
        """
        Perform complete backup process (validation, cleanup, size calculation, backup).
        
        Args:
            kodi_path: Path to Kodi installation
            backup_destination: Destination directory for backup
            label: Custom label for backup filename
            
        Returns:
            Dictionary with backup results and statistics
        """
        results = {
            'success': False,
            'filename': '',
            'size_before_cleanup': 0,
            'size_after_cleanup': 0,
            'space_freed': 0,
            'final_backup_size': 0,
            'cleanup_results': {},
            'error_message': ''
        }
        
        try:
            # Step 1: Validate Kodi directory
            if not self.validate_kodi_directory(kodi_path):
                results['error_message'] = "Invalid Kodi directory"
                return results
            
            # Step 2: Cleanup cache files (with space tracking)
            self._update_progress("=" * 25 + " CLEANUP " + "=" * 25)
            cleanup_results, space_freed = self.cleanup_cache_files(kodi_path, cleanup_settings)
            results['cleanup_results'] = cleanup_results
            results['space_freed'] = space_freed
            
            # Step 3: Create backup filename
            filename = self.create_backup_filename(label)
            results['filename'] = filename
            
            # Step 4: Create backup archive (with size tracking)
            self._update_progress("=" * 22 + " BACKUP ARCHIVE " + "=" * 22)
            backup_success, total_uncompressed_size = self.create_backup_archive(kodi_path, backup_destination, filename, archive_progress_callback)
            
            if backup_success:
                # Get final backup file size
                backup_file = Path(backup_destination) / filename
                if backup_file.exists():
                    results['final_backup_size'] = backup_file.stat().st_size
                
                # Calculate derived values for summary
                # Original size = what we actually backed up + what we cleaned up
                results['size_before_cleanup'] = total_uncompressed_size + space_freed
                results['size_after_cleanup'] = total_uncompressed_size
                
                results['success'] = True
            else:
                results['error_message'] = "Failed to create backup archive"
                
        except Exception as e:
            results['error_message'] = f"Unexpected error: {e}"
            self._update_progress(f"ERROR: {e}")
        
        return results
    
    def validate_backup_file(self, backup_file_path: str) -> Dict:
        """
        Validate that backup file exists and contains required Kodi structure.
        
        Args:
            backup_file_path: Path to backup ZIP file
            
        Returns:
            Dictionary with validation results and file counts
        """
        results = {
            'valid': False,
            'error_message': '',
            'userdata_files': 0,
            'addons_files': 0,
            'total_size': 0
        }
        
        backup_file = Path(backup_file_path)
        
        try:
            if not backup_file.exists():
                results['error_message'] = f"Backup file not found: {backup_file_path}"
                return results
            
            if not backup_file.suffix.lower() == '.zip':
                results['error_message'] = "Backup file must be a ZIP archive"
                return results
            
            # Check if it's a valid ZIP file and contains required structure
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                file_list = zipf.namelist()
                
                # Check for required directories
                has_userdata = any(f.startswith('userdata/') for f in file_list)
                has_addons = any(f.startswith('addons/') for f in file_list)
                
                if not has_userdata:
                    results['error_message'] = "Backup file does not contain userdata directory"
                    return results
                
                if not has_addons:
                    results['error_message'] = "Backup file does not contain addons directory"
                    return results
                
                # Count files in each directory
                results['userdata_files'] = sum(1 for f in file_list if f.startswith('userdata/') and not f.endswith('/'))
                results['addons_files'] = sum(1 for f in file_list if f.startswith('addons/') and not f.endswith('/'))
                
                # Get total uncompressed size
                results['total_size'] = sum(info.file_size for info in zipf.infolist() if not info.is_dir())
                
                results['valid'] = True
                self._update_progress(f"✓ Backup file is valid")
                self._update_progress(f"✓ Contains userdata folder ({results['userdata_files']} files)")
                self._update_progress(f"✓ Contains addons folder ({results['addons_files']} files)")
                
        except zipfile.BadZipFile:
            results['error_message'] = "File is not a valid ZIP archive"
        except Exception as e:
            results['error_message'] = f"Error validating backup file: {e}"
        
        return results
    
    def clear_kodi_directories(self, target_directory: str) -> bool:
        """
        Clear existing userdata and addons directories in target location.
        
        Args:
            target_directory: Path to Kodi installation directory
            
        Returns:
            True if successful, False otherwise
        """
        target_dir = Path(target_directory)
        
        try:
            # Clear userdata directory
            userdata_path = target_dir / "userdata"
            if userdata_path.exists():
                shutil.rmtree(userdata_path)
                self._update_progress("✓ Removed existing userdata directory")
            
            # Clear addons directory
            addons_path = target_dir / "addons"
            if addons_path.exists():
                shutil.rmtree(addons_path)
                self._update_progress("✓ Removed existing addons directory")
            
            return True
            
        except Exception as e:
            self._update_progress(f"ERROR: Failed to clear existing directories: {e}")
            return False
    
    def extract_backup_with_progress(self, backup_file_path: str, target_directory: str) -> bool:
        """
        Extract backup archive to target directory with progress updates.
        
        Args:
            backup_file_path: Path to backup ZIP file
            target_directory: Path to Kodi installation directory
            
        Returns:
            True if successful, False otherwise
        """
        backup_file = Path(backup_file_path)
        target_dir = Path(target_directory)
        
        try:
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                file_list = zipf.namelist()
                total_files = len([f for f in file_list if not f.endswith('/')])
                
                self._update_progress(f"Extracting backup archive...")
                self._update_progress(f"Restoring userdata files...")
                
                extracted_files = 0
                userdata_files = 0
                addons_files = 0
                
                for file_info in zipf.infolist():
                    if file_info.is_dir():
                        continue
                        
                    try:
                        zipf.extract(file_info, target_dir)
                        extracted_files += 1
                        
                        if file_info.filename.startswith('userdata/'):
                            userdata_files += 1
                        elif file_info.filename.startswith('addons/'):
                            addons_files += 1
                        
                        # Update progress for every 100 files
                        if extracted_files % 100 == 0:
                            progress_msg = f"Restored {extracted_files}/{total_files} files..."
                            if file_info.filename.startswith('addons/') and userdata_files > 0:
                                self._update_progress("Restoring addons files...")
                                userdata_files = 0  # Only show this message once
                            
                    except Exception as e:
                        self._update_progress(f"Warning: Could not restore file {file_info.filename}: {e}")
                        continue
                
                return True
                
        except Exception as e:
            self._update_progress(f"ERROR: Failed to extract backup archive: {e}")
            return False
    
    def perform_restore(self, backup_file_path: str, target_directory: str) -> Dict:
        """
        Perform complete restore process (validation, clearing, extraction).
        
        Args:
            backup_file_path: Path to backup ZIP file
            target_directory: Path to Kodi installation directory
            
        Returns:
            Dictionary with restore results and statistics
        """
        results = {
            'success': False,
            'userdata_files': 0,
            'addons_files': 0,
            'total_size': 0,
            'error_message': ''
        }
        
        try:
            # Step 1: Validate backup file
            validation = self.validate_backup_file(backup_file_path)
            if not validation['valid']:
                results['error_message'] = validation['error_message']
                return results
            
            results['userdata_files'] = validation['userdata_files']
            results['addons_files'] = validation['addons_files']
            results['total_size'] = validation['total_size']
            
            # Step 2: Clear existing directories
            self._update_progress("")
            self._update_progress("=" * 22 + " RESTORE PROCESS " + "=" * 22)
            self._update_progress("Clearing existing Kodi data...")
            
            if not self.clear_kodi_directories(target_directory):
                results['error_message'] = "Failed to clear existing directories"
                return results
            
            # Step 3: Extract backup
            self._update_progress("")
            if not self.extract_backup_with_progress(backup_file_path, target_directory):
                results['error_message'] = "Failed to extract backup archive"
                return results
            
            # Step 4: Success
            results['success'] = True
            self._update_progress("")
            self._update_progress("RESTORE COMPLETED SUCCESSFULLY")
            
        except Exception as e:
            results['error_message'] = f"Unexpected error during restore: {e}"
            self._update_progress(f"ERROR: {e}")
        
        return results


if __name__ == "__main__":
    # Simple test when run directly
    def test_callback(message: str):
        print(f"[TEST] {message}")
    
    engine = KodiBackupEngine(test_callback)
    print("Backup engine initialized successfully")
