# version_manager.py
import json
from pathlib import Path
import tempfile

def get_version_file_path():
    """Get version.json path in temp directory to avoid distribution"""
    temp_dir = Path(tempfile.gettempdir()) / "zipinstaller"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir / "version.json"

VERSION_FILE = get_version_file_path()

def bump_major():
    """Bump major version and reset others"""
    with open(VERSION_FILE, 'r') as f:
        data = json.load(f)
    
    data["major"] += 1
    data["minor"] = 0
    data["patch"] = 0
    data["build"] = 0
    
    with open(VERSION_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Version bumped to: {data['major']}.{data['minor']}.{data['patch']}.{data['build']}")

def bump_minor():
    """Bump minor version and reset patch/build"""
    with open(VERSION_FILE, 'r') as f:
        data = json.load(f)
    
    data["minor"] += 1
    data["patch"] = 0
    data["build"] = 0
    
    with open(VERSION_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Version bumped to: {data['major']}.{data['minor']}.{data['patch']}.{data['build']}")

def bump_patch():
    """Bump patch version and reset build"""
    with open(VERSION_FILE, 'r') as f:
        data = json.load(f)
    
    data["patch"] += 1
    data["build"] = 0
    
    with open(VERSION_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Version bumped to: {data['major']}.{data['minor']}.{data['patch']}.{data['build']}")

def show_version():
    """Display current version"""
    with open(VERSION_FILE, 'r') as f:
        data = json.load(f)
    
    version = f"{data['major']}.{data['minor']}.{data['patch']}.{data['build']}"
    print(f"Current version: {version}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "major":
            bump_major()
        elif sys.argv[1] == "minor":
            bump_minor()
        elif sys.argv[1] == "patch":
            bump_patch()
        elif sys.argv[1] == "show":
            show_version()
    else:
        show_version()