# build.py
import subprocess
import sys
import shutil
from pathlib import Path
from version import increment_build

def find_python():
    """Find Python 3.12 executable with fallbacks"""
    # Try specific Python versions in order of preference
    python_versions = [
        "python3.12",    # Linux/macOS
        "py -3.12",      # Windows Python Launcher
        "python3",       # Generic python3
        "python",        # Generic python
        "py",           # Windows Python Launcher generic
    ]
    
    for python_cmd in python_versions:
        if " " in python_cmd:
            # For commands with spaces like "py -3.12"
            base_cmd = python_cmd.split()
            try:
                result = subprocess.run(base_cmd + ["--version"], 
                                      capture_output=True, text=True, check=True)
                if "3.12" in result.stdout:
                    print(f"✅ Found: {python_cmd}")
                    return base_cmd
            except:
                continue
        else:
            # For single commands
            if shutil.which(python_cmd):
                try:
                    result = subprocess.run([python_cmd, "--version"], 
                                          capture_output=True, text=True, check=True)
                    if "3.12" in result.stdout:
                        print(f"✅ Found: {python_cmd}")
                        return [python_cmd]
                except:
                    continue
    
    # Fallback to current Python
    print("⚠️  Python 3.12 not found, using current Python")
    return [sys.executable]

def find_pybabel():
    """Find pybabel executable with fallbacks"""
    # Try to find pybabel in common locations
    pybabel_locations = [
        "pybabel",  # In PATH
        r"c:\users\josev\appdata\local\programs\python\Python312\Scripts\pybabel.exe",  # Specific location
        Path(sys.executable).parent / "Scripts" / "pybabel.exe",  # Relative to current Python
    ]
    
    for pybabel in pybabel_locations:
        pybabel_path = Path(pybabel) if not isinstance(pybabel, Path) else pybabel
        
        # Try as string first (for commands in PATH)
        if isinstance(pybabel, str) and shutil.which(pybabel):
            return pybabel
        
        # Try as path
        if pybabel_path.exists():
            return str(pybabel_path)
    
    return None

def compile_translations():
    """Compile .po files to .mo files"""
    print("🌍 Compiling translations...")
    
    pybabel = find_pybabel()
    
    if not pybabel:
        print("⚠️  Babel not found. Install with: pip install Babel")
        return False
    
    try:
        result = subprocess.run(
            [pybabel, "compile", "-d", "locales"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Translations compiled successfully")
            return True
        else:
            print(f"⚠️  Warning: Could not compile translations: {result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️  Error compiling translations: {e}")
        return False

def build():
    """
    Build the executable with automated versioning using Python 3.12
    """
    # Find Python 3.12
    python_cmd = find_python()
    
    # Compile translations before building
    compile_translations()
    
    # ONLY increment during build process
    version = increment_build()
    
    print(f"🚀 Building ZipInstaller Modern v{version} with Python 3.12")
    
    # Build command using explicit Python
    command = python_cmd + [
        "-m", "nuitka",
        "--standalone",
        "--onefile", 
        "--windows-console-mode=disable",
        "--enable-plugin=pyside6",
        "--msvc=latest",
        "--company-name=VM/Studio",
        "--product-name=ZipInstaller Modern", 
        f"--file-version={version}",
        f"--product-version={version}",
        "--file-description=Instalador portable de aplicaciones ZIP",
        "--windows-icon-from-ico=zim.ico",
        "--assume-yes-for-downloads",
        "--remove-output",
        "--python-flag=no_asserts",
        "--python-flag=no_docstrings",
        # Only include compiled .mo files, exclude source files
        #"--include-data-files=locales/*/LC_MESSAGES/*.mo=locales/",
        "--include-data-dir=locales=locales",
        "--noinclude-data-files=*.pot,*.po",
        
        # NEW: Size optimization additions
        "--lto=yes",                           # Link Time Optimization
        "--noinclude-setuptools-mode=error",   # Block setuptools bloat
        "--noinclude-pytest-mode=error",       # Block pytest bloat  
        "--noinclude-IPython-mode=error",      # Block IPython bloat
        "--nofollow-import-to=*.tests",        # Exclude test modules
        "--nofollow-import-to=*.testing",
        
        # Qt-specific optimizations
        "--include-qt-plugins=sensible",       # Only essential Qt plugins
        "--noinclude-qt-translations",         # Exclude translation files
        
        # Testing
        #"--static-libpython=yes",        # Static linking (smaller but test compatibility)
        #"--disable-console",             # Alternative to windows-console-mode
        #"--upx",
        "zim.py"
    ]
    
    result = subprocess.run(command)
    
    if result.returncode == 0:
        print(f"✅ Build successful! Version: {version}")
        
        # Show the created file info
        exe_path = Path("zim.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / 1024 / 1024
            print(f"📦 Output: {exe_path}")
            print(f"📏 Size: {size_mb:.1f} MB")
    else:
        print("❌ Build failed!")
    
    # PAUSE at the end
    print("\n" + "="*50)
    input("Presiona ENTER para salir...")

if __name__ == "__main__":
    build()