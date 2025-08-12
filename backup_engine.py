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
from typing import Optional, Callable, Dict, List, Tuple


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
    
    def calculate_directory_size(self, directory_path: str) -> int:
        """
        Calculate total size of directory and all subdirectories.
        
        Args:
            directory_path: Path to directory
            
        Returns:
            Total size in bytes
        """
        total_size = 0
        dir_path = Path(directory_path)
        
        if not dir_path.exists():
            return 0
            
        try:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, IOError):
                        # Skip files we can't access
                        continue
        except (OSError, IOError):
            # Skip directories we can't access
            pass
            
        return total_size
    
    def calculate_kodi_size(self, kodi_path: str) -> Tuple[int, int]:
        """
        Calculate size of userdata and addons directories.
        
        Args:
            kodi_path: Path to Kodi installation
            
        Returns:
            Tuple of (userdata_size, addons_size) in bytes
        """
        kodi_dir = Path(kodi_path)
        
        userdata_size = self.calculate_directory_size(str(kodi_dir / "userdata"))
        addons_size = self.calculate_directory_size(str(kodi_dir / "addons"))
        
        return userdata_size, addons_size
    
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
    
    def cleanup_cache_files(self, kodi_path: str, cleanup_settings: Dict[str, bool] = None) -> Dict[str, bool]:
        """
        Clean up cache and temporary files to reduce backup size.
        Based on the original batch script cleanup logic.
        
        Args:
            kodi_path: Path to Kodi installation
            cleanup_settings: Dict of cleanup options (None = use defaults)
            
        Returns:
            Dictionary with cleanup results for each operation
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
        
        # Process cleanup targets based on settings
        for key, target in all_cleanup_targets.items():
            if not cleanup_settings.get(key, False):
                results[target['name']] = False
                self._update_progress(f"Skipped {target['description']} (disabled in settings)")
                continue
                
            try:
                if target['path'].exists():
                    if target['is_directory']:
                        shutil.rmtree(target['path'])
                    else:
                        target['path'].unlink()
                    
                    results[target['name']] = True
                    self._update_progress(f"Deleted {target['description']}")
                else:
                    results[target['name']] = False
                    self._update_progress(f"Skipped {target['description']} (not found)")
                    
            except Exception as e:
                results[target['name']] = False
                self._update_progress(f"Failed to delete {target['description']}: {e}")
        
        self._update_progress("Cache cleanup complete")
        return results
    
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
                            filename: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Create compressed backup archive of Kodi installation.
        
        Args:
            kodi_path: Path to Kodi installation
            backup_destination: Destination directory for backup
            filename: Backup filename
            progress_callback: Optional callback for progress updates (current_files, total_files)
            
        Returns:
            True if backup successful, False otherwise
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
        
        # Count total files for progress tracking
        total_files = 0
        file_list = []
        
        for backup_dir_path in backup_dirs:
            if backup_dir_path.exists():
                for file_path in backup_dir_path.rglob('*'):
                    if file_path.is_file():
                        # Store relative path for archive
                        rel_path = file_path.relative_to(kodi_dir)
                        file_list.append((file_path, rel_path))
                        total_files += 1
        
        self._update_progress(f"Creating backup with compression...")
        self._update_progress(f"Output: {filename}")
        self._update_progress("")
        self._update_progress(f"Compressing {total_files} files...")
        
        # Initialize progress at start of compression
        if progress_callback:
            progress_callback(0, total_files)
        
        try:
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                current_file = 0
                
                for file_path, archive_path in file_list:
                    try:
                        zipf.write(file_path, archive_path)
                        current_file += 1
                        
                        # Update progress bar every 100 files or at completion (no status spam)
                        if current_file % 100 == 0 or current_file == total_files:
                            if progress_callback:
                                progress_callback(current_file, total_files)
                                
                    except Exception as e:
                        self._update_progress(f"Warning: Could not backup file {file_path}: {e}")
                        continue
            
            # Get final backup size
            backup_size = backup_file.stat().st_size
            self._update_progress("")
            self._update_progress(f"Backup complete! File: {filename}  Size: {self.format_size(backup_size)}")
            self._update_progress(f"Saved to: {backup_file}")
            
            return True
            
        except Exception as e:
            self._update_progress(f"ERROR: Failed to create backup archive: {e}")
            return False
    
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
            
            # Step 2: Calculate size before cleanup
            self._update_progress("=" * 20 + " SIZE BEFORE CLEANUP " + "=" * 20)
            self._update_progress("Measuring size of Kodi Userdata and Addons BEFORE cleanup...")
            userdata_before, addons_before = self.calculate_kodi_size(kodi_path)
            total_before = userdata_before + addons_before
            results['size_before_cleanup'] = total_before
            self._update_progress(f"Current size: {self.format_size(total_before)}")
            self._update_progress("")
            
            # Step 3: Cleanup cache files
            self._update_progress("=" * 25 + " CLEANUP " + "=" * 25)
            cleanup_results = self.cleanup_cache_files(kodi_path, cleanup_settings)
            results['cleanup_results'] = cleanup_results
            self._update_progress("")
            
            # Step 4: Calculate size after cleanup
            self._update_progress("=" * 20 + " SIZE AFTER CLEANUP " + "=" * 20)
            self._update_progress("Measuring size AFTER cleanup...")
            userdata_after, addons_after = self.calculate_kodi_size(kodi_path)
            total_after = userdata_after + addons_after
            results['size_after_cleanup'] = total_after
            
            space_freed = total_before - total_after
            results['space_freed'] = space_freed
            
            self._update_progress(f"Space freed: {self.format_size(space_freed)}")
            self._update_progress(f"Size to backup: {self.format_size(total_after)}")
            self._update_progress("")
            
            # Step 5: Create backup filename
            filename = self.create_backup_filename(label)
            results['filename'] = filename
            
            # Step 6: Create backup archive
            self._update_progress("=" * 22 + " BACKUP ARCHIVE " + "=" * 22)
            backup_success = self.create_backup_archive(kodi_path, backup_destination, filename, archive_progress_callback)
            
            if backup_success:
                # Get final backup file size
                backup_file = Path(backup_destination) / filename
                if backup_file.exists():
                    results['final_backup_size'] = backup_file.stat().st_size
                
                results['success'] = True
                self._update_progress("Backup completed successfully!")
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
