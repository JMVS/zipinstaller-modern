# version.py - RUNTIME VERSION (read-only)
import json
from pathlib import Path
import tempfile

def get_version_file_path():
    """Get version.json path in temp directory"""
    temp_dir = Path(tempfile.gettempdir()) / "zipinstaller"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir / "version.json"

VERSION_FILE = get_version_file_path()

def get_version_display():
    """Get version for display purposes without incrementing"""
    if VERSION_FILE.exists():
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return f"{data['major']}.{data['minor']}.{data['patch']}.{data['build']}"
    return "0.9.0.0"  # Fallback

def increment_build():
    """ONLY call this during build process"""
    if VERSION_FILE.exists():
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {"major": 0, "minor": 9, "patch": 0, "build": 0}
    
    data["build"] += 1
    
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    return f"{data['major']}.{data['minor']}.{data['patch']}.{data['build']}"

# For runtime, use the display version (no auto-increment)
__version__ = get_version_display()
__version_info__ = tuple(int(x) for x in __version__.split('.'))