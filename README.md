# Kodi Backup Tool

Cross-platform GUI application for backing up and restoring Kodi installations. Provides automated cache cleanup, backup creation, and restore functionality through a unified interface.

## Download

**[Download Latest Release](https://github.com/YOUR_USERNAME/kodi-backup-tool/releases/latest)**

The standalone executable requires no installation or Python dependencies.

## Features

- Cross-platform support (Windows, macOS, Linux)
- GUI interface using CustomTkinter
- Automated cache cleanup to reduce backup size
- ZIP compression with configurable settings
- Backup validation and restore functionality
- Persistent configuration storage
- Progress tracking and status reporting

## Requirements

- Python 3.8+
- Dependencies listed in requirements.txt

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
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
2. Clears existing userdata and addons directories
3. Extracts backup contents to target location

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

- Backup filename: `kodi.bkup_YYYY-MM-DD_LABEL.zip`
- Compression: ZIP format with maximum compression level
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

## Executable Distribution

Create standalone executable using PyInstaller:

```bash
python -m PyInstaller --onefile --windowed --icon=icon.ico --name "Kodi-Backup-Tool" main.py
```

The resulting executable is fully portable and includes all dependencies.

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

All operations include comprehensive error reporting through the status interface.