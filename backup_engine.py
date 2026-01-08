#!/usr/bin/env python3
"""
Kodi Backup Engine - Cross-Platform Implementation
Converts the Windows batch script logic to Python for cross-platform compatibility.
"""

import os
import re
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
        
        # Check if userdata and addons directories exist (key indicators of Kodi installation)
        userdata_path = kodi_dir / "userdata"
        addons_path = kodi_dir / "addons"
        
        if not userdata_path.exists() or not addons_path.exists():
            self._update_progress("ERROR: Invalid Kodi directory: missing userdata/ and/or addons/")
            return False
            
        self._update_progress(f"✓ Valid Kodi directory found: {kodi_path}")
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

    def _log_remaining_contents(self, target_path: Path, kodi_dir: Path, limit: int = 10) -> None:
        """Log remaining files when cleanup fails due to non-empty directory."""
        remaining_paths = []
        total_files = 0

        try:
            for root, dirs, files in os.walk(target_path):
                for file in files:
                    total_files += 1
                    if len(remaining_paths) < limit:
                        file_path = os.path.join(root, file)
                        try:
                            rel_path = os.path.relpath(file_path, kodi_dir)
                        except ValueError:
                            rel_path = file_path
                        remaining_paths.append(rel_path)
        except Exception as e:
            self._update_progress(f"Could not list remaining files: {e}")
            return

        self._update_progress(f"Remaining files: {total_files}")
        for rel_path in remaining_paths:
            self._update_progress(f"Remaining: {rel_path}")

    def _is_drive_root(self, target_dir: Path) -> bool:
        """Return True if target_dir is a drive root (e.g., C:\\ or /)."""
        try:
            resolved_target = target_dir.resolve()
        except Exception:
            resolved_target = target_dir

        anchor = resolved_target.anchor
        if anchor:
            resolved_str = str(resolved_target).rstrip("\\/")
            anchor_str = anchor.rstrip("\\/")
            if resolved_str == anchor_str:
                return True

        return resolved_target.parent == resolved_target or len(resolved_target.parts) <= 1

    def _is_safe_zip_member(self, target_dir: Path, member_name: str) -> bool:
        """Return True if zip member path is safe to extract within target_dir."""
        if not member_name:
            return False

        normalized = member_name.replace("\\", "/")
        if normalized.startswith("/") or normalized.startswith("\\"):
            return False
        if re.match(r"^[A-Za-z]:", normalized):
            return False

        target_abs = os.path.normcase(os.path.abspath(str(target_dir)))
        member_abs = os.path.normcase(os.path.abspath(os.path.join(target_abs, normalized)))
        try:
            common = os.path.commonpath([target_abs, member_abs])
        except ValueError:
            return False

        return common == target_abs
    
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
                    self._update_progress(f"Not present: {target['description']} (nothing to delete)")
                    
            except Exception as e:
                results[target['name']] = False
                self._update_progress(f"Failed to delete {target['description']}: {e}")
                if target['is_directory'] and key in ("tmdb_blur", "tmdb_crop"):
                    winerror = getattr(e, "winerror", None)
                    errno = getattr(e, "errno", None)
                    if winerror == 145 or errno == 145:
                        self._log_remaining_contents(target['path'], kodi_dir)
        
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
        if not label:
            return f"kodi.bkup_{date_str}.zip"

        clean_label = self.sanitize_label(label)
        return f"kodi.bkup_{date_str}_{clean_label}.zip"

    def sanitize_label(self, label: str) -> str:
        """
        Sanitize backup label to produce a safe filename component.
        """
        if not label:
            return "backup"

        cleaned = label.strip()
        if not cleaned:
            return "backup"

        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", cleaned)
        cleaned = re.sub(r"_+", "_", cleaned)
        cleaned = cleaned[:50]

        return cleaned if cleaned else "backup"
    
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

        total_files = 0
        for backup_dir_path in backup_dirs:
            if backup_dir_path.exists():
                for _, _, files in os.walk(backup_dir_path):
                    total_files += len(files)
        
        self._update_progress(f"Creating backup archive...")
        self._update_progress(f"Output: {filename}")
        self._update_progress("")
        
        try:
            total_uncompressed_size = 0
            skipped_files_count = 0
            skipped_examples = []
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
                                file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(file_path, kodi_path)
                                arcname = rel_path.replace("\\", "/")
                                try:
                                    # Get file size before adding to archive
                                    file_size = os.path.getsize(file_path)
                                    
                                    # Calculate relative path for archive
                                    zipf.write(file_path, arcname)
                                    total_uncompressed_size += file_size
                                    current_file += 1
                                    
                                    # Show progress every 1000 files to give user feedback without spam
                                    if current_file - last_progress_update >= 1000:
                                        self._update_progress(f"Processing... {current_file}/{total_files} files archived")
                                        if progress_callback:
                                            progress_callback(current_file, total_files)
                                        last_progress_update = current_file
                                        
                                except Exception as e:
                                    skipped_files_count += 1
                                    if len(skipped_examples) < 10:
                                        skipped_examples.append((arcname, str(e)))
                                    continue
            
            self._update_progress(f"ZIP creation completed with {skipped_files_count} skipped files")
            if skipped_files_count > 0:
                for rel_path, error_message in skipped_examples:
                    self._update_progress(f"Skipped: {rel_path} ({error_message})")
            
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
            'total_size': 0,
            'error_logged': False
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
                normalized_list = [name.replace("\\", "/") for name in file_list]
                
                # Check for required directories
                has_userdata = any(f.split('/', 1)[0] == 'userdata' for f in normalized_list)
                has_addons = any(f.split('/', 1)[0] == 'addons' for f in normalized_list)
                
                if not has_userdata or not has_addons:
                    results['error_message'] = "Backup file does not contain required directories: userdata/ and/or addons/"
                    self._update_progress(f"ERROR: {results['error_message']}")
                    results['error_logged'] = True
                    return results
                
                # Count files in each directory
                results['userdata_files'] = sum(1 for f in normalized_list if f.startswith('userdata/') and not f.endswith('/'))
                results['addons_files'] = sum(1 for f in normalized_list if f.startswith('addons/') and not f.endswith('/'))
                
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
                total_files = sum(1 for zi in zipf.infolist() if not zi.is_dir())
                
                self._update_progress(f"Extracting {total_files} items...")
                self._update_progress(f"Extracting backup archive...")
                
                extracted_files = 0
                skipped_files_count = 0
                userdata_banner_shown = False
                addons_banner_shown = False
                progress_interval = 1000
                
                for file_info in zipf.infolist():
                    if file_info.is_dir():
                        continue

                    name = file_info.filename.replace("\\", "/")
                    try:
                        if not self._is_safe_zip_member(target_dir, name):
                            self._update_progress(f"ERROR: Unsafe zip entry detected (path traversal): {name}")
                            return False

                        if name != file_info.filename:
                            dest_path = target_dir / name
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            with zipf.open(file_info) as source, open(dest_path, "wb") as dest:
                                shutil.copyfileobj(source, dest)
                        else:
                            zipf.extract(file_info, target_dir)
                        extracted_files += 1
                        
                        if name.startswith('userdata/') and not userdata_banner_shown:
                            self._update_progress("Restoring userdata files...")
                            userdata_banner_shown = True
                        elif name.startswith('addons/') and not addons_banner_shown:
                            self._update_progress("Restoring addons files...")
                            addons_banner_shown = True
                        
                        # Update progress for every N files
                        if extracted_files % progress_interval == 0 or extracted_files == total_files:
                            self._update_progress(f"Extracting... {extracted_files}/{total_files} files restored")
                            
                    except Exception as e:
                        self._update_progress(f"Warning: Could not restore file {file_info.filename}: {e}")
                        skipped_files_count += 1
                        continue

                self._update_progress(f"Extraction completed with {skipped_files_count} skipped files")
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
            'error_message': '',
            'error_logged': False
        }
        
        try:
            # Step 1: Validate backup file
            validation = self.validate_backup_file(backup_file_path)
            if not validation['valid']:
                results['error_message'] = validation['error_message']
                results['error_logged'] = validation.get('error_logged', False)
                return results
            
            results['userdata_files'] = validation['userdata_files']
            results['addons_files'] = validation['addons_files']
            results['total_size'] = validation['total_size']
            
            # Step 2: Validate restore target
            target_dir = Path(target_directory)
            if self._is_drive_root(target_dir):
                msg = f"Refusing restore to drive root: {target_dir}"
                results['error_message'] = msg
                results['error_logged'] = True
                self._update_progress(f"ERROR: {msg}")
                return results

            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                self._update_progress(f"Restore target did not exist; created directory: {target_dir}")
            
            userdata_path = target_dir / "userdata"
            addons_path = target_dir / "addons"
            has_userdata = userdata_path.is_dir()
            has_addons = addons_path.is_dir()
            
            if not (has_userdata and has_addons):
                allowed_names = {".ds_store", "thumbs.db", "desktop.ini"}
                try:
                    entries = list(target_dir.iterdir())
                except Exception as e:
                    msg = f"Unable to read restore target: {e}"
                    results['error_message'] = msg
                    results['error_logged'] = True
                    self._update_progress(f"ERROR: {msg}")
                    return results
                
                if any(entry.name.lower() not in allowed_names for entry in entries):
                    msg = ("Restore target is not a Kodi folder and is not empty. Choose an empty folder "
                           "(new device) or a Kodi folder containing userdata/ and addons/.")
                    results['error_message'] = msg
                    results['error_logged'] = True
                    self._update_progress(f"ERROR: {msg}")
                    return results
            
            # Step 3: Validate zip entries for path traversal
            try:
                with zipfile.ZipFile(backup_file_path, 'r') as zipf:
                    for member_name in zipf.namelist():
                        if not self._is_safe_zip_member(target_dir, member_name):
                            msg = f"Unsafe zip entry detected (path traversal): {member_name}"
                            results['error_message'] = msg
                            results['error_logged'] = True
                            self._update_progress(f"ERROR: {msg}")
                            return results
            except Exception as e:
                msg = f"Error validating backup file entries: {e}"
                results['error_message'] = msg
                results['error_logged'] = True
                self._update_progress(f"ERROR: {msg}")
                return results

            # Step 4: Clear existing directories if restoring into Kodi folder
            self._update_progress("")
            self._update_progress("=" * 22 + " RESTORE PROCESS " + "=" * 22)
            
            if has_userdata and has_addons:
                self._update_progress("Clearing existing Kodi data...")
                if not self.clear_kodi_directories(target_directory):
                    msg = "Failed to clear existing directories"
                    results['error_message'] = msg
                    self._update_progress(f"ERROR: {msg}")
                    results['error_logged'] = True
                    return results
            
            # Step 5: Extract backup
            self._update_progress("")
            if not self.extract_backup_with_progress(backup_file_path, target_directory):
                results['error_message'] = "Failed to extract backup archive"
                results['error_logged'] = True
                return results
            
            # Step 6: Success
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
