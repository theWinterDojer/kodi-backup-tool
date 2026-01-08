![Banner](https://github.com/theWinterDojer/kodi-backup-tool/blob/main/public/banner.png?raw=true)

# Kodi Backup Tool

Portable GUI application for backing up and restoring Kodi installations. Provides automated cache cleanup, backup creation, and restore functionality.

## Download

### Windows Users
**[Download Windows Executable](https://github.com/theWinterDojer/kodi-backup-tool/releases/latest)** - No installation or Python required

### macOS & Linux Users
Install Python 3.8+ and run from source (see Installation section below)

## Features

- Windows executable available for easy deployment
- GUI interface using CustomTkinter
- Automated cache cleanup to reduce backup size
- ZIP compression (level 6)
- Backup validation and restore functionality
- Persistent configuration storage
- Progress tracking and status reporting

## Installation

### Option 1: Windows Executable (Recommended for Windows)
1. Download the `.exe` file from the [releases page](https://github.com/theWinterDojer/kodi-backup-tool/releases/latest)
2. Run `Kodi-Backup-Tool.exe` - no installation required

### Option 2: Run from Source (Windows, macOS, Linux)

**Requirements:**
- Python 3.8+
- Dependencies listed in requirements.txt

**Steps:**
1. Clone or download the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Usage

### Backup Process

1. Configure Kodi directory path (source)
2. Configure backup destination directory
3. Set optional backup label
4. Adjust cleanup settings in Settings dialog
5. Execute backup operation

The backup process performs the following steps:
1. Validates Kodi directory structure
2. Calculates initial size
3. Performs cache cleanup based on settings
4. Creates compressed ZIP archive
5. Reports final statistics

### Restore Process

1. Select backup ZIP file
2. Select target Kodi directory
3. Confirm overwrite operation
4. Execute restore

The restore process:
1. Validates backup file structure
2. Refuses drive-root targets and non-empty non-Kodi folders
3. Clears existing userdata and addons directories (only when restoring to a Kodi folder)
4. Extracts backup contents to target location (existing or new empty folder)

## Cache Cleanup

### Default Cleanup (Always Enabled)
- `userdata/Thumbnails` - Thumbnail cache
- `addon_data/plugin.video.themoviedb.helper/blur_v2` - TMDb Helper blur cache
- `addon_data/plugin.video.themoviedb.helper/crop_v2` - TMDb Helper crop cache
- `addons/packages` - Cached addon packages

### Optional Cleanup (User Configurable)
- `addon_data/plugin.video.themoviedb.helper/database_07` - TMDb Helper database
- `addon_data/plugin.video.umbrella/cache.db` - Umbrella cache database
- `addon_data/plugin.video.umbrella/search.db` - Umbrella search database
- `addon_data/script.module.cocoscrapers/cache.db` - Cocoscrapers cache database

## Backup Contents

- Complete `userdata` directory (settings, databases, addon configurations)
- Complete `addons` directory (installed addons and dependencies)

## File Format

- Backup filename: `kodi.bkup_YYYY-MM-DD.zip` (no label) or `kodi.bkup_YYYY-MM-DD_LABEL.zip`
- Compression: ZIP format with level 6 compresion (Speed increase for negligible space saving)
- Archive structure preserves original directory hierarchy

## Configuration

Application settings are stored in `kodi_backup_config.json` in the application directory:

```json
{
  "kodi_path": "path/to/kodi",
  "backup_path": "path/to/backup/destination", 
  "backup_label": "optional_label",
  "last_backup_file": "path/to/last/backup.zip",
  "cleanup_settings": {
    "thumbnails": true,
    "tmdb_blur": true,
    "tmdb_crop": true,
    "addon_packages": true
  }
}
```

Note: Optional cleanup settings reset to false on each application launch for safety.

## Building Platform-Specific Executables

To create a standalone executable for your platform using PyInstaller:

```bash
# Install PyInstaller first
pip install PyInstaller

# Create executable (run on the target platform)
python -m PyInstaller --onefile --windowed --icon=icon.ico --name "Kodi-Backup-Tool" main.py
```
If `icon.ico` is missing, omit the `--icon` flag.

**Important Notes:**
- The executable will only run on the platform where it was built
- Windows executable (`.exe`) only works on Windows
- macOS executable only works on macOS  
- Linux executable only works on Linux
- For cross-platform distribution, build on each target platform separately

## Architecture

- `main.py` - GUI interface and application logic
- `backup_engine.py` - Core backup/restore operations
- `requirements.txt` - Python dependencies

## Error Handling

The application includes validation for:
- Kodi directory structure verification
- Backup file integrity checking
- Path existence validation
- Compression/extraction error handling
- Unsafe zip entry (path traversal) detection

All operations include comprehensive error reporting through the status interface.
