#!/usr/bin/env python3
"""
ZipInstaller Modern (ZIM) - Portable Application Installer from ZIP files

A lightweight application installer for Windows that extracts portable applications
from ZIP archives and integrates them into the system with shortcuts, registry 
entries, and proper uninstallation support.

Copyright (C) 2025 VM/Studio

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

Author: VM/Studio
Repository: https://github.com/JMVS/zipinstaller-modern
"""

import sys
import os
import json
import zipfile
import shutil
import winreg
import subprocess
import gettext
from version import __version__, __version_info__
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QFileDialog, QCheckBox, QMessageBox, QProgressBar, 
                             QGroupBox, QDialog, QListWidget, QMenu, QTextBrowser)
from PySide6.QtCore import Qt, QThread, Signal, QLocale
from PySide6.QtGui import QFont, QPalette, QColor, QAction, QIcon


# ====================== GLOBAL VARIABLES =======================

# Initialize localization support
_ = gettext.gettext
# Static strings
ERROR_TEXT = _("Error")
WARNING_TEXT = _("Warning")
APP_NAME = "ZipInstaller Modern"
DEVELOPER = "VM/Studio"

# ==================== DEPENDENCY MANAGEMENT ====================

# Check for optional win32com support (Windows shortcuts)
try:
    import win32com.client
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    if __debug__: print(f"{WARNING_TEXT}: {_('pywin32 is not installed. Shortcuts will not work.')}")

# Check for optional pefile support (executable metadata reading)
try:
    import pefile
    PEFILE_AVAILABLE = True
except ImportError:
    PEFILE_AVAILABLE = False
    if __debug__: print(f"{WARNING_TEXT}: {_('pefile is not installed. Executable metadata reading will not work.')}")

# Check for optional pyshortcuts support (cross-platform shortcuts)
try:
    from pyshortcuts import make_shortcut
    PYSHORTCUTS_AVAILABLE = True
except ImportError:
    PYSHORTCUTS_AVAILABLE = False
    if __debug__: print(f"{WARNING_TEXT}: {_('pyshortcuts is not installed. Will use win32com for shortcuts.')}")

# ==================== UTILITY FUNCTIONS ====================

def custom_question_dialog(parent, title, text, default_yes=True):
    """
    Display a custom question dialog with support for translated Yes/No buttons.
    
    Args:
        parent: Parent widget
        title: Dialog title
        text: Dialog message
        default_yes: Whether Yes button should be default (True) or No (False)
        
    Returns:
        bool: True if Yes clicked, False if No clicked
    """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setIcon(QMessageBox.Icon.Question)
    
    yes_button = msg_box.addButton(_("Yes"), QMessageBox.ButtonRole.YesRole)
    no_button = msg_box.addButton(_("No"), QMessageBox.ButtonRole.NoRole)
    
    if default_yes:
        msg_box.setDefaultButton(yes_button)
    else:
        msg_box.setDefaultButton(no_button)
    
    msg_box.exec()
    return msg_box.clickedButton() == yes_button


class SystemUtils:
    """Utility class for system-level operations"""
    
    @staticmethod
    def get_shell_folder(folder_name):
        """
        Get Windows special folder path from registry.
        
        Args:
            folder_name: Name of the shell folder (e.g., "Desktop", "Local AppData")
            
        Returns:
            str: Full path to the folder, or fallback path if registry read fails
        """
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            value, __ = winreg.QueryValueEx(key, folder_name)
            winreg.CloseKey(key)
            return os.path.expandvars(value)
        except:
            # Fallback to standard paths if registry read fails
            if folder_name == "Desktop":
                return str(Path.home() / 'Desktop')
            elif folder_name == "Local AppData":
                return str(Path.home() / 'AppData' / 'Local')
            elif folder_name == "Personal":
                return str(Path.home() / 'Documents')
            return str(Path.home())

    @staticmethod
    def is_windows_dark_mode():
        """
        Detect if Windows is using dark theme.
        
        Returns:
            bool: True if dark mode is active, False otherwise
        """
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
            value, __ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            winreg.CloseKey(key)
            return value == 0  # 0 = dark mode, 1 = light mode
        except:
            return False

    @staticmethod
    def calculate_directory_size(path):
        """
        Calculate total size of all files in a directory recursively.
        
        Args:
            path: Directory path
            
        Returns:
            int: Total size in bytes
        """
        total = 0
        try:
            for entry in Path(path).rglob('*'):
                if entry.is_file():
                    total += entry.stat().st_size
        except:
            pass
        return total

    @staticmethod
    def is_zipinstaller_installed():
        """
        Check if ZipInstaller Modern is installed on the system.
        
        Returns:
            bool: True if installed, False otherwise
        """
        is_installed, __, ___ = SystemUtils.get_installed_zipinstaller_version()
        return is_installed
            
    @staticmethod
    def get_installed_zipinstaller_version():
        """
        Get version information of installed ZipInstaller Modern from Registry.
        
        Returns:
            tuple: (is_installed: bool, version: str, install_path: str)
        """
        try:
            key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            
            try:
                version, __ = winreg.QueryValueEx(key, "DisplayVersion")
            except:
                version = "0.0.0.0"
            
            try:
                install_location, __ = winreg.QueryValueEx(key, "InstallLocation")
            except:
                install_location = ""
            
            winreg.CloseKey(key)
            return (True, version, install_location)
        except:
            return (False, None, None)
            
    @staticmethod
    #TODO: Rewrite as old_version / new_version for clarity
    def compare_versions(version1, version2):
        """
        Compare two version strings in major.minor.patch.build format
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            int: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
        """
        try:
            # Parse and normalize versions to 4 components
            v1_parts = [int(x) for x in version1.split('.')[:4]]
            v2_parts = [int(x) for x in version2.split('.')[:4]]
            
            # Pad with zeros if components are missing
            while len(v1_parts) < 4:
                v1_parts.append(0)
            while len(v2_parts) < 4:
                v2_parts.append(0)
            
            # Compare each component
            for i in range(4):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            
            return 0
        except:
            return 0


class FileUtils:
    """Utility class for file operations."""
    
    @staticmethod
    def get_exe_icon_path(exe_path):
        """
        Get executable path for using its first icon.
        
        Args:
            exe_path: Path to executable file
            
        Returns:
            str: Icon path in format "path,0" or empty string if file doesn't exist
        """
        if Path(exe_path).exists():
            return f"{exe_path},0"
        return ""

    @staticmethod
    def find_executables_in_zip(zip_path):
        """
        Find all .exe files in ZIP root or first subdirectory.
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            tuple: (list of executable names, root directory name or None)
        """
        executables = []
        root_dir = None
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                all_files = zip_ref.namelist()
                
                # First search in ZIP root
                for file in all_files:
                    if '/' not in file and '\\' not in file:
                        if file.lower().endswith('.exe'):
                            executables.append(file)
                
                # If no executables in root, search first subdirectory
                # This is so apps packed inside it's own directory
                # (i.e. ZIP/app/app.exe) can be detected as well
                if not executables:
                    first_dir = None
                    for file in all_files:
                        if '/' in file or '\\' in file:
                            first_dir = file.split('/')[0] if '/' in file else file.split('\\')[0]
                            break
                    
                    if first_dir:
                        root_dir = first_dir
                        for file in all_files:
                            normalized = file.replace('\\', '/')
                            parts = normalized.split('/')
                            if len(parts) == 2 and parts[0] == first_dir and parts[1].lower().endswith('.exe'):
                                # Return executable name without parent directory
                                executables.append(parts[1])
        except Exception as e:
            if __debug__: print(_("Error reading ZIP: {error}").format(error=e))
        return executables, root_dir

    @staticmethod
    def create_self_delete_batch(exe_path, install_dir):
        """
        Create a batch file that deletes itself along with the executable and directory.
        Used for uninstaller self-deletion after closing.
        Based on https://www.catch22.net/tuts/system/self-deleting-executables/
        
        Args:
            exe_path: Path to executable to delete
            install_dir: Directory to remove
            
        Returns:
            Path: Path to created batch file
        """
        batch_content = f"""@echo off
REM Created by "{APP_NAME}" as part of the uninstall process. It is safe to delete.
:Repeat
del /f /q "{exe_path}"
if exist "{exe_path}" goto Repeat
timeout /t 1 /nobreak > nul
rmdir /s /q "{install_dir}"
del /f /q "%~f0"
"""
        
        batch_file = Path(os.environ.get('TEMP', '.')) / f'uninstall_{os.getpid()}.bat'
        with open(batch_file, 'w') as f:
            f.write(batch_content)
        
        return batch_file


class ExecutableUtils:
    """Utility class for executable operations."""
    
    @staticmethod
    def get_exe_metadata(exe_path):
        """
        Extract metadata from Windows executable file using pefile.
        
        Args:
            exe_path: Path to executable (.exe) file
            
        Returns:
            dict: Metadata dictionary with keys like ProductName, FileVersion, etc.
        """
        if not PEFILE_AVAILABLE:
            return {}
        
        try:
            pe = pefile.PE(exe_path, fast_load=True)
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
            
            metadata = {}
            
            # Extract string resources (ProductName, Copyright, etc.)
            if hasattr(pe, 'FileInfo'):
                for file_info in pe.FileInfo:
                    if hasattr(file_info, 'StringTable'):
                        for string_table in file_info.StringTable:
                            for entry in string_table.entries.items():
                                key = entry[0].decode('utf-8', errors='ignore')
                                value = entry[1].decode('utf-8', errors='ignore')
                                metadata[key] = value
            
            # Extract version information
            if hasattr(pe, 'VS_FIXEDFILEINFO'):
                if pe.VS_FIXEDFILEINFO:
                    version = pe.VS_FIXEDFILEINFO[0]
                    file_version = f"{version.FileVersionMS >> 16}.{version.FileVersionMS & 0xFFFF}.{version.FileVersionLS >> 16}.{version.FileVersionLS & 0xFFFF}"
                    metadata['FileVersionRaw'] = file_version
            
            pe.close()
            return metadata
        
        except Exception as e:
            if __debug__: 
                print(_("Error reading executable metadata: {error}").format(error=e))
            return {}

    @staticmethod
    def get_current_exe_metadata():
        """
        Get metadata from currently running executable (ZIM itself).
        This is used during self-install
        
        Returns:
            dict: Metadata with name, version, publisher, icon_path
        """
        if getattr(sys, 'frozen', False) or sys.executable.endswith('.exe'):
            current_exe = sys.executable
            metadata = ExecutableUtils.get_exe_metadata(current_exe)
            
            return {
                'name': metadata.get('ProductName', APP_NAME),
                'version': __version__,
                'product_name': metadata.get('ProductName', APP_NAME),
                'publisher': metadata.get('LegalCopyright', DEVELOPER),
                'icon_path': FileUtils.get_exe_icon_path(current_exe)
            }
        else:
            return {
                'name': APP_NAME,
                'version': __version__,
                'product_name': APP_NAME,
                'publisher': DEVELOPER,
                'icon_path': ''
            }

    @staticmethod
    def create_shortcut(target, shortcut_path, working_dir, icon_path=None):
        """
        Create Windows shortcut using available method (win32com or pyshortcuts).
        Prefers win32com for better reliability with .exe files.
        
        Args:
            target: Target file path
            shortcut_path: Path where .lnk file will be created
            working_dir: Working directory for shortcut
            icon_path: Optional icon path
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Try win32com first
        if WINDOWS_AVAILABLE:
            try:
                Path(shortcut_path).parent.mkdir(parents=True, exist_ok=True)
                
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(str(shortcut_path))
                shortcut.TargetPath = str(target)
                shortcut.WorkingDirectory = str(working_dir)
                shortcut.IconLocation = icon_path if icon_path else str(target)
                shortcut.save()
                return True
            except Exception as e:
                if __debug__: 
                    print(_("Error creating shortcut with win32com: {error}").format(error=e))
        
        # Fallback to pyshortcuts if win32com failed
        if PYSHORTCUTS_AVAILABLE:
            try:
                name = Path(shortcut_path).stem
                folder = str(Path(shortcut_path).parent)
                
                make_shortcut(
                    script=str(target),
                    name=name,
                    folder=folder,
                    icon=icon_path if icon_path else str(target),
                    terminal=False,
                    desktop=False
                )
                return True
            except Exception as e:
                if __debug__: print(_("Error creating shortcut with pyshortcuts: {error}").format(error=e))
      
        return False

    @staticmethod
    def normalize_path(path):
        """
        Normalize path to use consistent backslashes for Windows.
        
        Args:
            path: Path string or Path object
            
        Returns:
            str: Normalized path string
        """
        return str(Path(path))


class RegistryUtils:
    """Utility class for Windows Registry operations."""
    
    @staticmethod
    def get_zip_progid():
        """
        Detect the ProgID associated with .zip files.
        Used to register context menu in correct location.
        This is used during self-install
        
        Returns:
            str: ProgID string (e.g., "CompressedFolder")
        """
        try:
            # Try to get user's association first
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.zip\UserChoice",
                0,
                winreg.KEY_READ
            )
            progid, __ = winreg.QueryValueEx(key, "ProgId")
            winreg.CloseKey(key)
            return progid
        except:
            pass
        
        # Fallback: search in HKEY_CLASSES_ROOT
        try:
            key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r".zip", 0, winreg.KEY_READ)
            progid, __ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            if progid:
                return progid
        except:
            pass
        
        # Windows default
        return "CompressedFolder"
    
    @staticmethod
    def register_context_menu():
        """
        Register "Install with ZIM..." context menu for ZIP files.
        This is used during self-install
        
        Returns:
            bool: True if successful, False otherwise
        """
        context_menu_text = _("Install with ZIM...")
        try:
            local_appdata = Path(SystemUtils.get_shell_folder("Local AppData"))
            install_path = local_appdata / 'Programs' / APP_NAME
            exe_path = install_path / 'ZIM.exe'
            
            if not exe_path.exists():
                return False
            
            # Detect correct ProgID for ZIP files
            progid = RegistryUtils.get_zip_progid()
            key_path = rf"Software\Classes\{progid}\shell\InstallWithZIM"
            
            try:
                # Register in detected ProgID
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, context_menu_text)
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{exe_path}",0')
                winreg.CloseKey(key)
                
                command_key_path = key_path + r"\command"
                command_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_key_path)
                winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, f'"{exe_path}" "%1"')
                winreg.CloseKey(command_key)
                
                # Save used ProgID for uninstallation
                config_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\{APP_NAME}")
                winreg.SetValueEx(config_key, "RegisteredProgId", 0, winreg.REG_SZ, progid)
                winreg.CloseKey(config_key)
                
                return True
            except Exception as e:
                if __debug__: 
                    print(_("Error registering in {progid}: {error}").format(progid=progid, error=e))
                
                # Universal fallback if specific ProgID fails
                try:
                    key_path = r"Software\Classes\*\shell\InstallWithZIM"
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, context_menu_text)
                    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{exe_path}",0')
                    winreg.SetValueEx(key, "AppliesTo", 0, winreg.REG_SZ, 
                                    'System.FileName:"*.zip"')
                    winreg.CloseKey(key)
                    
                    command_key_path = key_path + r"\command"
                    command_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_key_path)
                    winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, f'"{exe_path}" "%1"')
                    winreg.CloseKey(command_key)
                    
                    config_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\{APP_NAME}")
                    winreg.SetValueEx(config_key, "RegisteredProgId", 0, winreg.REG_SZ, "*")
                    winreg.CloseKey(config_key)
                    
                    return True
                except Exception as e2:
                    if __debug__: print(_("Generic fallback error: {error}").format(error=e2))
                    return False
                    
        except Exception as e:
            if __debug__: print(_("Error registering context menu: {error}").format(error=e))
            return False

    @staticmethod
    def unregister_context_menu():
        """
        Remove "Install with ZIM..." context menu for ZIP files.
        This is used during self-uninstall
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read saved ProgID from installation
            progid = None
            try:
                config_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    rf"Software\{APP_NAME}",
                    0,
                    winreg.KEY_READ
                )
                progid, __ = winreg.QueryValueEx(config_key, "RegisteredProgId")
                winreg.CloseKey(config_key)
            except:
                # If not saved, try to detect or use default
                progid = RegistryUtils.get_zip_progid()
            
            # Remove from specific ProgID
            if progid:
                key_path = rf"Software\Classes\{progid}\shell"
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
                    
                    try:
                        winreg.DeleteKey(key, r"InstallWithZIM\command")
                    except:
                        pass
                    
                    try:
                        winreg.DeleteKey(key, "InstallWithZIM")
                    except:
                        pass
                    
                    winreg.CloseKey(key)
                except:
                    pass
            
            # Clean up ZipInstaller configuration
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software",
                    0,
                    winreg.KEY_ALL_ACCESS
                )
                winreg.DeleteKey(key, APP_NAME)
                winreg.CloseKey(key)
            except:
                pass
            
            return True
        except Exception as e:
            if __debug__: 
                print(_("Error unregistering context menu: {error}").format(error=e))
            return False


# ==================== INSTALLATION THREAD ====================

class InstallThread(QThread):
    """
    Thread for installing applications (without blocking UI).
    Emits signals to update progress bar and status messages.
    """
    progress = Signal(int)  # Progress percentage (0-100)
    status = Signal(str)     # Status message
    finished = Signal(bool, str)  # Success flag, message/path
    
    def __init__(self, config):
        """
        Initialize installation thread.
        
        Args:
            config: Dictionary with installation configuration
        """
        super().__init__()
        self.config = config
    
    def run(self):
        """Main installation process."""
        try:
            install_path = Path(self.config['install_path']) / self.config['install_folder']
            install_path.mkdir(parents=True, exist_ok=True)
            
            self.status.emit(_("Extracting files..."))
            self.progress.emit(10)
            
            installed_files = []
            zip_root_dir = self.config.get('zip_root_dir')  # Root directory inside ZIP
            
            # Extract ZIP contents
            with zipfile.ZipFile(self.config['zip_file'], 'r') as zip_ref:
                members = zip_ref.namelist()
                
                # Filter only files from subdirectory if exists
                if zip_root_dir:
                    members_to_extract = [m for m in members if m.startswith(zip_root_dir + '/') or m.startswith(zip_root_dir + '\\')]
                else:
                    members_to_extract = members
                
                total = len(members_to_extract)
                
                for i, member in enumerate(members_to_extract):
                    # Extract removing root directory prefix if exists
                    if zip_root_dir:
                        member_path = member.replace('\\', '/')
                        if member_path.startswith(zip_root_dir + '/'):
                            relative_path = member_path[len(zip_root_dir) + 1:]
                            if relative_path:  # Don't process empty root directory
                                target_path = install_path / relative_path
                                
                                if member.endswith('/') or member.endswith('\\'):
                                    target_path.mkdir(parents=True, exist_ok=True)
                                else:
                                    target_path.parent.mkdir(parents=True, exist_ok=True)
                                    with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                                        target.write(source.read())
                                    installed_files.append(relative_path)
                    else:
                        zip_ref.extract(member, install_path)
                        installed_files.append(member)
                    
                    # Update progress every ~5% of files
                    if i % max(1, total // 20) == 0:
                        progress_val = 10 + int((i / total) * 50)
                        self.progress.emit(progress_val)
            
            self.status.emit(_("Creating uninstaller..."))
            self.progress.emit(60)
            
            # Copy uninstaller executable (itself)
            if getattr(sys, 'frozen', False) or sys.executable.endswith('.exe'):
                current_exe = Path(sys.executable)
                uninstaller_exe = install_path / 'uninstall.exe'
                shutil.copy2(current_exe, uninstaller_exe)
            
            self.status.emit(_("Compiling installation info..."))
            self.progress.emit(65)
            
            # Calculate installed size (includes additional files needed for uninstallation)
            installed_size = SystemUtils.calculate_directory_size(install_path)
            
            # Create installation info JSON
            install_info = {
                'name': self.config['name'], # App's name
                'executable': self.config['executable'], # App's executable
                'install_date': datetime.now().isoformat(), # Intall date
                'install_path': str(install_path), # Install folder
                'version': self.config.get('version', '1.0.0.0'), # App's version or fallback to 1.0.0.0
                'product_name': self.config.get('product_name', self.config['name']), #App's product name
                'installed_by': self.config.get('installed_by', APP_NAME), # Installer's name
                'icon_path': self.config.get('icon_path', ''), # App's icon
                'installed_size': installed_size, # Total space in bytes ocuppied (app + uninstaller)
                'installed_files': installed_files # List of files installed (app + uninstaller)
            }
            
            # Create JSON file with installation information
            info_file = install_path / 'install_info.json'
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(install_info, f, indent=2, ensure_ascii=False)
            
            self.progress.emit(70)
            
            # Verify executable exists
            exe_path = install_path / self.config['executable']
            if not exe_path.exists():
                raise Exception(_("The executable {exec} does not exist in the ZIP").format(exec=self.config['executable']))
            
            icon_path = self.config.get('icon_path', str(exe_path))
            
            # Normalize all paths for Windows
            normalized_exe_path = ExecutableUtils.normalize_path(exe_path)
            normalized_install_path = ExecutableUtils.normalize_path(install_path)
            normalized_icon_path = ExecutableUtils.normalize_path(icon_path) if icon_path else None
            
            # Create desktop shortcut if requested
            if self.config['create_desktop']:
                self.status.emit(_("Creating Desktop shortcut..."))
                try:
                    desktop_folder = Path(SystemUtils.get_shell_folder("Desktop"))
                    desktop_path = desktop_folder / f"{self.config['name']}.lnk"
                    ExecutableUtils.create_shortcut(
                        normalized_exe_path, 
                        ExecutableUtils.normalize_path(desktop_path), 
                        normalized_install_path, 
                        normalized_icon_path
                    )
                except Exception as e:
                    if __debug__: 
                        print(_("Could not create Desktop shortcut: {error}").format(error=e))
            
            self.progress.emit(85)
            
            # Create Start Menu shortcut if requested
            if self.config['create_startmenu']:
                self.status.emit(_("Creating Start Menu shortcut..."))
                try:
                    start_menu = Path(os.environ['APPDATA']) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
                    start_menu_path = start_menu / f"{self.config['name']}.lnk"
                    ExecutableUtils.create_shortcut(
                        normalized_exe_path,
                        ExecutableUtils.normalize_path(start_menu_path),
                        normalized_install_path,
                        normalized_icon_path
                    )
                except Exception as e:
                    if __debug__: 
                        print(_("Could not create Start Menu shortcut: {error}").format(error=e))
            
            self.progress.emit(90)
            
            # Add to Windows Registry (Add/Remove Programs)
            self.status.emit(_("Registering in system..."))
            self._create_registry_entry(install_path, install_info)
            
            self.progress.emit(100)
            self.status.emit(_("Installation complete!"))
            self.finished.emit(True, str(install_path))
            
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def _create_registry_entry(self, install_path, info):
        """
        Create Windows Registry entry for uninstallation (Add/Remove Programs).
        
        Args:
            install_path: Installation directory path
            info: Installation info dictionary
        """
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            app_key = winreg.CreateKey(key, info['name'])
            
            uninstaller_exe = install_path / 'uninstall.exe'
            uninstall_string = f'"{uninstaller_exe}"' if uninstaller_exe.exists() else ''
            
            display_name = info['product_name']
            if info['version'] and info['version'] != '1.0.0.0':
                display_name += f" {info['version']}"
            
            # Set registry values for Add/Remove Programs
            winreg.SetValueEx(app_key, "DisplayName", 0, winreg.REG_SZ, display_name)
            winreg.SetValueEx(app_key, "DisplayVersion", 0, winreg.REG_SZ, info['version'])
            winreg.SetValueEx(app_key, "Publisher", 0, winreg.REG_SZ, info['installed_by'])
            winreg.SetValueEx(app_key, "InstallLocation", 0, winreg.REG_SZ, str(install_path))
            
            if info.get('icon_path'):
                winreg.SetValueEx(app_key, "DisplayIcon", 0, winreg.REG_SZ, info['icon_path'])
            
            if info.get('installed_size'):
                size_kb = int(info['installed_size'] / 1024)
                winreg.SetValueEx(app_key, "EstimatedSize", 0, winreg.REG_DWORD, size_kb)
            
            if uninstall_string:
                winreg.SetValueEx(app_key, "UninstallString", 0, winreg.REG_SZ, uninstall_string)
            
            winreg.SetValueEx(app_key, "InstallDate", 0, winreg.REG_SZ, datetime.now().strftime('%Y%m%d'))
            winreg.SetValueEx(app_key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(app_key, "NoRepair", 0, winreg.REG_DWORD, 1)
            
            winreg.CloseKey(app_key)
            winreg.CloseKey(key)
            
        except Exception as e:
            if __debug__: print(WARNING_TEXT + ": " + _("Could not create Registry entry: {error}").format(error=e))


# ==================== UNINSTALLER DIALOG ====================

class UninstallerDialog(QDialog):
    """
    Dialog for uninstalling applications installed by ZIM.
    
    This code executes when running as uninstallation module.
    The application checks for the existance of 'install_info.json'
    and being itself called 'uninstall.exe'
    """
    
    def __init__(self):
        super().__init__()
        self.setup_paths()
        self.load_install_info()
        self.setup_ui()
    
    def setup_paths(self):
        """Determine installation paths based on executable location."""
        if getattr(sys, 'frozen', False) or (hasattr(sys, 'executable') and sys.executable.endswith('.exe')):
            self.install_dir = Path(sys.executable).parent
            self.uninstaller_exe = Path(sys.executable)
        else:
            self.install_dir = Path(__file__).parent
            self.uninstaller_exe = None
        
        self.info_file = self.install_dir / 'install_info.json'
    
    def load_install_info(self):
        """Load installation information from JSON file."""
        if not self.info_file.exists():
            QMessageBox.critical(None, ERROR_TEXT, 
                _("Installation information file not found!") +
                "\n\n" +
                _("Search path: ") + str(self.info_file))
            sys.exit(1)
        
        with open(self.info_file, 'r', encoding='utf-8') as f:
            self.info = json.load(f)
        
        # Track original and additional files
        self.original_files = set(self.info.get('installed_files', []))
        self.additional_files = []
        
        # Detect files created after installation (user data, config, etc.)
        if self.install_dir.exists():
            for item in self.install_dir.rglob('*'):
                if item.is_file():
                    rel_path = str(item.relative_to(self.install_dir))
                    if rel_path not in self.original_files and rel_path not in ['uninstall.exe', 'install_info.json']:
                        self.additional_files.append(rel_path)
    
    def setup_ui(self):
        """Create uninstaller dialog UI."""
        uninstall_name = _("Uninstall {name}").format(name=self.info['name'])
        
        self.setWindowTitle(uninstall_name)
        self.setMinimumSize(600, 450)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header
        header = QLabel("🗑️ " + uninstall_name)
        header.setFont(QFont('Segoe UI', 16, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Application info group
        info_group = QGroupBox(_("App Info"))
        info_layout = QVBoxLayout()
        
        info_text = _("<b>Version:</b> {version}<br>").format(version=self.info.get('version', 'Unknown'))
        info_text += _("<b>Installed:</b> {install_date}<br>").format(install_date=self.info.get('install_date', 'Unknown')[:10])
        info_text += _("<b>Location:</b> {install_dir}").format(install_dir=self.install_dir)
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        if SystemUtils.is_windows_dark_mode():
            info_label.setStyleSheet("padding: 10px; background-color: #353535; border-radius: 5px; color: #e0e0e0;")
        else:
            info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px; color: #1f2937;")
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Warning
        warning = QLabel("⚠️ " + _("This action cannot be undone"))
        warning.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        warning.setStyleSheet("color: #d97706; padding: 8px;")
        layout.addWidget(warning)
        
        # Additional files section (if any)
        if self.additional_files:
            extra_group = QGroupBox("📁 " + _("Additional files detected ({count_files})").format(count_files=len(self.additional_files)))
            extra_layout = QVBoxLayout()
            
            extra_info = QLabel(_("These files were not part of the original installation (settings, saved data, etc):"))
            extra_info.setWordWrap(True)
            extra_info.setStyleSheet("color: #666; font-weight: normal;")
            extra_layout.addWidget(extra_info)
            
            # List widget showing additional files
            list_widget = QListWidget()
            list_widget.setMaximumHeight(120)
            for f in self.additional_files[:20]:
                list_widget.addItem(f)
            if len(self.additional_files) > 20:
                list_widget.addItem(_("... and {count_additional_files} more files").format(count_additional_files=len(self.additional_files) - 20))
            extra_layout.addWidget(list_widget)
            
            # Checkbox to delete additional files
            self.delete_extra_check = QCheckBox(_("Delete additional files too"))
            self.delete_extra_check.setChecked(True)
            self.delete_extra_check.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
            extra_layout.addWidget(self.delete_extra_check)
            
            extra_group.setLayout(extra_layout)
            layout.addWidget(extra_group)
        else:
            self.delete_extra_check = None
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.uninstall_btn = QPushButton("🗑️ " + _("Uninstall"))
        self.uninstall_btn.setMinimumHeight(40)
        self.uninstall_btn.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        self.uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        self.uninstall_btn.clicked.connect(self.do_uninstall)
        btn_layout.addWidget(self.uninstall_btn)
        
        cancel_btn = QPushButton(_("Cancel"))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.apply_styles()
    
    def apply_styles(self):
        """Apply dark or light theme based on Windows settings."""
        dark_mode = SystemUtils.is_windows_dark_mode()
        
        if dark_mode:
            self.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                }
                QLabel {
                    font-size: 10pt;
                    color: #e0e0e0;
                }
                QCheckBox {
                    font-size: 10pt;
                    padding: 5px;
                    color: #e0e0e0;
                }
                QGroupBox {
                    font-size: 10pt;
                    color: #e0e0e0;
                    background-color: #2d2d2d;
                    border: 2px solid #404040;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    color: #e0e0e0;
                }
                QListWidget {
                    border: 1px solid #404040;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 9pt;
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                }
                QLabel {
                    font-size: 10pt;
                    color: #1f2937;
                }
                QCheckBox {
                    font-size: 10pt;
                    padding: 5px;
                    color: #1f2937;
                }
                QGroupBox {
                    font-size: 10pt;
                    color: #1f2937;
                    background-color: #ffffff;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    color: #1f2937;
                }
                QListWidget {
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 9pt;
                    background-color: #ffffff;
                    color: #1f2937;
                }
            """)
    
    def do_uninstall(self):
        """Execute uninstallation process."""
        if not custom_question_dialog(
            self,
            _('Confirm'),
            _("Confirm uninstall of {name}?").format(name=self.info['name']),
            default_yes=False
        ):
            return
        
        try:
            self.remove_shortcuts()
            self.remove_registry_entry()
            
            delete_all = self.delete_extra_check.isChecked() if self.delete_extra_check else True
            
            files_deleted = 0
            files_remaining = []
            
            if delete_all:
                # Delete all files in installation directory
                for item in self.install_dir.rglob('*'):
                    if item.is_file() and item != self.uninstaller_exe:
                        try:
                            item.unlink()
                            files_deleted += 1
                        except Exception as e:
                            files_remaining.append(str(item))
                            if __debug__: 
                                print(_("Could not delete {item_error}: {error}").format(item_error=item, error=e))
                
                # Remove empty directories
                for item in sorted(self.install_dir.rglob('*'), reverse=True):
                    if item.is_dir():
                        try:
                            item.rmdir()
                        except:
                            pass
            else:
                # Delete only original installation files
                for file_path in self.original_files:
                    full_path = self.install_dir / file_path
                    if full_path.exists() and full_path.is_file():
                        try:
                            full_path.unlink()
                            files_deleted += 1
                        except Exception as e:
                            files_remaining.append(str(full_path))
                            if __debug__: 
                                print(_("Could not delete {full_path_error}: {error}").format(full_path_error=full_path, error=e))
                
                try:
                    self.info_file.unlink()
                except:
                    pass
            
            # Create self-delete batch file for uninstaller
            if self.uninstaller_exe:
                batch_file = FileUtils.create_self_delete_batch(str(self.uninstaller_exe), str(self.install_dir))
                
                msg = "✅ " + _("{name} uninstalled successfully").format(name=self.info['name']) + "\n\n"
                msg += "📊 " + _("{total_files_deleted} files deleted").format(total_files_deleted=files_deleted) + "\n\n"
                
                if files_remaining or delete_all:
                    msg += _("The uninstaller and remaining files will be deleted automatically when closing this window.")
                
                QMessageBox.information(self, _("Uninstall Complete"), msg)
                self.accept()
                
                # Launch self-delete batch in background
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                
                subprocess.Popen(
                    ['cmd', '/c', str(batch_file)],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
                )
            else:
                msg = "✅ " + _("{name} uninstalled successfully").format(name=self.info['name']) + "\n\n"
                msg += "📊 " + _("{total_files_deleted} files deleted").format(total_files_deleted=files_deleted)
                QMessageBox.information(self, _("Uninstall Complete"), msg)
                self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, ERROR_TEXT, _("Error during uninstallation:") + "\n" + str(e))
    
    def remove_shortcuts(self):
        """Remove Desktop and Start Menu shortcuts."""
        target_name = self.info['name']
        
        desktop = Path(SystemUtils.get_shell_folder("Desktop")) / f"{target_name}.lnk"
        if desktop.exists():
            try:
                desktop.unlink()
            except:
                pass
        
        start_menu = Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / f"{target_name}.lnk"
        if start_menu.exists():
            try:
                start_menu.unlink()
            except:
                pass
    
    def remove_registry_entry(self):
        """Remove Windows Registry entry (Add/Remove Programs)."""
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            winreg.DeleteKey(key, self.info['name'])
            winreg.CloseKey(key)
        except Exception as e:
            if __debug__: 
                print(WARNING_TEXT + ": " + _("Could not delete registry entry: {error}").format(error=e))


# ==================== ABOUT DIALOG ====================

class AboutDialog(QDialog):
    """About dialog showing application information and licenses."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Create About dialog UI."""
        self.setWindowTitle(_("About") + " " + APP_NAME)
        self.setMinimumSize(550, 500)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("📦 " + APP_NAME)
        title.setFont(QFont('Segoe UI', 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Version
        version = QLabel(_("Version {version}").format(version=__version__))
        version.setFont(QFont('Segoe UI', 11))
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        # Author
        author = QLabel(_("Developed by") + " " + DEVELOPER)
        author.setFont(QFont('Segoe UI', 10))
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(author)
        
        # Description
        desc = QLabel(_("Installs and uninstalls applications and utilities that do not provide an internal installation program"))
        desc.setFont(QFont('Segoe UI', 10))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # License and components information
        license_group = QGroupBox(_("Licenses and Components"))
        license_layout = QVBoxLayout()
        
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        
        # Build HTML content with translation support
        title = APP_NAME
        license_label = _("License")
        view_license = _("View GPLv3 license")
        components_title = _("Components used")
        about_gpl_title = _("About GPLv3")
        gpl_paragraph_1 = _(
            "This program is free software: you can redistribute it and/or modify "
            "it under the terms of the GNU General Public License as published by "
            "the Free Software Foundation, either version 3 of the License, or "
            "(at your option) any later version."
        )
        gpl_paragraph_2 = _(
            "This program is distributed in the hope that it will be useful, "
            "but WITHOUT ANY WARRANTY; without even the implied warranty of "
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. "
            "See the GNU General Public License for more details."
        )

        # Dependencies (only descriptions can be translated)
        deps = [
            ("PySide6", _("GUI framework"), "LGPL v3 / GPL v3 / Commercial", "https://www.qt.io/qt-for-python"),
            ("pywin32", _("Windows extensions for Python"), "PSF License", "https://github.com/mhammond/pywin32"),
            ("pefile", _("Windows PE file parser"), "MIT License", "https://github.com/erocarrera/pefile"),
            ("pyshortcuts", _("Cross-platform desktop shortcut creation"), "MIT License", "https://github.com/newville/pyshortcuts"),
            ("Babel", _("Internationalization library"), "BSD License", "https://babel.pocoo.org/"),
            ("Nuitka", _("Python compiler"), "Apache 2.0", "https://nuitka.net/"),
        ]

        deps_html = "\n".join(
            f"""
            <p><b>{name}</b> – {desc}<br>
            {license_label}: {license}<br>
            <a href="{url}">{url}</a></p>
            """
            for name, desc, license, url in deps
        )

        html = f"""
        <style>
            body {{ font-family: 'Segoe UI'; font-size: 10pt; }}
            h3 {{ color: #4F46E5; margin-top: 10px; }}
            p {{ margin: 5px 0; }}
            a {{ color: #4F46E5; }}
        </style>

        <h3>{title}</h3>
        <p><b>{license_label}:</b> GNU GPLv3</p>
        <p><a href="https://www.gnu.org/licenses/gpl-3.0.html">{view_license}</a></p>

        <h3>{components_title}:</h3>
        {deps_html}

        <h3>{about_gpl_title}:</h3>
        <p>{gpl_paragraph_1}</p>
        <p>{gpl_paragraph_2}</p>
        """

        text_browser.setHtml(html)
        
        if SystemUtils.is_windows_dark_mode():
            text_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    border: 1px solid #404040;
                    border-radius: 4px;
                }
            """)
        
        license_layout.addWidget(text_browser)
        license_group.setLayout(license_layout)
        layout.addWidget(license_group)
        
        # Close button
        close_btn = QPushButton(_("Close"))
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        self.apply_styles()
    
    def apply_styles(self):
        """Apply dark or light theme based on Windows settings."""
        dark_mode = SystemUtils.is_windows_dark_mode()
        
        if dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #1e1e1e; }
                QLabel { color: #e0e0e0; }
                QGroupBox {
                    color: #e0e0e0;
                    background-color: #2d2d2d;
                    border: 2px solid #404040;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QPushButton {
                    background-color: #4F46E5;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #6366f1; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #ffffff; }
                QLabel { color: #1f2937; }
                QGroupBox {
                    color: #1f2937;
                    background-color: #ffffff;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QPushButton {
                    background-color: #4F46E5;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #4338CA; }
            """)


# ==================== MAIN APPLICATION WINDOW ====================

class ZipInstallerApp(QMainWindow):
    """Main application window for ZipInstaller Modern."""
    
    def __init__(self, zip_file_arg=None):
        """
        Initialize main window.
        
        Args:
            zip_file_arg: Optional ZIP file path from command line (to support launching from context menu)
        """
        super().__init__()
        self.zip_file_arg = zip_file_arg
        self.setup_ui()
        
        # Load ZIP file if provided via command line
        if self.zip_file_arg and Path(self.zip_file_arg).exists():
            self.load_zip_file(self.zip_file_arg)
               
    def setup_ui(self):
        """Create main window UI."""
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(700, 675)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header section
        header_layout = QHBoxLayout()
        
        header_left = QVBoxLayout()
        header = QLabel("📦 " + APP_NAME)
        header.setFont(QFont('Segoe UI', 24, QFont.Weight.Bold))
        header.setStyleSheet("color: #4F46E5;")
        header_left.addWidget(header)
        
        subtitle = QLabel(_("Portable application installer from ZIP files"))
        subtitle.setFont(QFont('Segoe UI', 10))
        subtitle.setStyleSheet("color: #666; margin-bottom: 20px;")
        header_left.addWidget(subtitle)
        
        header_layout.addLayout(header_left)
        header_layout.addStretch()
        
        # Menu button
        menu_btn = QPushButton("☰")
        menu_btn.setFont(QFont('Segoe UI', 20, QFont.Weight.Bold))
        menu_btn.setFixedSize(45, 45)
        menu_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #4F46E5;
                border-radius: 22px;
                color: #4F46E5;
            }
            QPushButton:hover {
                background-color: #4F46E5;
                color: white;
            }
        """)
        menu_btn.clicked.connect(self.show_menu)
        header_layout.addWidget(menu_btn, alignment=Qt.AlignmentFlag.AlignTop)
        
        main_layout.addLayout(header_layout)
        
        # Installation panel
        install_panel = self.create_install_panel()
        main_layout.addWidget(install_panel)
        
        self.apply_styles()
    
    def show_menu(self):
        """Show simple context menu with self-install/uninstall options."""
        menu = QMenu(self)
        
        is_installed, installed_version, __ = SystemUtils.get_installed_zipinstaller_version()
        
        if is_installed:
            # If installed, check if running version is newer than installed version
            current_version = __version__
            comparison = SystemUtils.compare_versions(current_version, installed_version)
            
            if comparison > 0:
                # Running process is newer than installed. Offer update option
                update_text = _("Update {app} (v{vOld} → v{vNew})")
                update_text_action = "🔄 " + update_text.format(app=APP_NAME, vOld=installed_version, vNew=current_version)
                update_action = QAction(update_text_action, self)
                update_action.triggered.connect(self.install_self)
                menu.addAction(update_action)
            
            self_action = QAction(f"🗑️ {_('Uninstall {app_name}...').format(app_name=APP_NAME)}", self)
            self_action.triggered.connect(self.uninstall_self)
        else:
            self_action = QAction(f"📥 {_('Install {app_name} in the system').format(app_name=APP_NAME)}", self)
            self_action.triggered.connect(self.install_self)
        menu.addAction(self_action)
        
        menu.addSeparator()
        
        # About option
        about_action = QAction("ℹ️ " + _("About..."), self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        
        menu.exec(self.sender().mapToGlobal(self.sender().rect().bottomLeft()))
    
    def install_self(self):
        """Install ZipInstaller Modern itself on the system."""
        if not (getattr(sys, 'frozen', False) or sys.executable.endswith('.exe')):
            QMessageBox.warning(self, _("Not available"),
                _("Self install is only available in the compiled version."))
            return
        
        if custom_question_dialog(
            self,
            _("Install {app_name}").format(app_name=APP_NAME),
            _("Do you want to install {app_name} on your system?").format(app_name=APP_NAME) + "\n\n" + _("This will allow running it from the Start Menu."),
            default_yes=True
        ):
            try:
                current_exe = Path(sys.executable)
                local_appdata = Path(SystemUtils.get_shell_folder("Local AppData"))
                install_path = local_appdata / 'Programs' / APP_NAME
                install_path.mkdir(parents=True, exist_ok=True)
                
                # Copy main executable
                dest_exe = install_path / 'ZIM.exe'
                shutil.copy2(current_exe, dest_exe)
                
                # Copy uninstaller
                uninstall_exe = install_path / 'uninstall.exe'
                shutil.copy2(current_exe, uninstall_exe)
                
                exe_metadata = ExecutableUtils.get_current_exe_metadata()
                icon_path = f'"{dest_exe}",0'
                
                # Create installation info
                install_info = {
                    'name': APP_NAME,
                    'executable': 'ZIM.exe',
                    'install_date': datetime.now().isoformat(),
                    'install_path': str(install_path),
                    'version': exe_metadata['version'],
                    'product_name': exe_metadata['product_name'],
                    'installed_by': exe_metadata['publisher'],
                    'icon_path': icon_path,
                    'installed_size': current_exe.stat().st_size * 2,
                    'installed_files': ['ZIM.exe', 'uninstall.exe', 'install_info.json']
                }
                
                info_file = install_path / 'install_info.json'
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(install_info, f, indent=2, ensure_ascii=False)
                
                # Create Start Menu shortcut
                start_menu = Path(os.environ['APPDATA']) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
                shortcut_path = start_menu / f"{APP_NAME}.lnk"
                
                normalized_dest_exe = ExecutableUtils.normalize_path(dest_exe)
                normalized_install_path = ExecutableUtils.normalize_path(install_path)
                normalized_shortcut_path = ExecutableUtils.normalize_path(shortcut_path)
                
                ExecutableUtils.create_shortcut(
                    normalized_dest_exe, 
                    normalized_shortcut_path, 
                    normalized_install_path, 
                    normalized_dest_exe
                )
                
                # Create registry entry
                key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
                app_key = winreg.CreateKey(key, APP_NAME)
                
                display_name = f"{exe_metadata['product_name']} {exe_metadata['version']}"
                
                winreg.SetValueEx(app_key, "DisplayName", 0, winreg.REG_SZ, display_name)
                winreg.SetValueEx(app_key, "DisplayVersion", 0, winreg.REG_SZ, exe_metadata['version'])
                winreg.SetValueEx(app_key, "Publisher", 0, winreg.REG_SZ, exe_metadata['publisher'])
                winreg.SetValueEx(app_key, "InstallLocation", 0, winreg.REG_SZ, str(install_path))
                winreg.SetValueEx(app_key, "DisplayIcon", 0, winreg.REG_SZ, icon_path)
                winreg.SetValueEx(app_key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstall_exe}"')
                winreg.SetValueEx(app_key, "InstallDate", 0, winreg.REG_SZ, datetime.now().strftime('%Y%m%d'))
                winreg.SetValueEx(app_key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(app_key, "NoRepair", 0, winreg.REG_DWORD, 1)
                
                size_kb = int((install_info['installed_size']) / 1024)
                winreg.SetValueEx(app_key, "EstimatedSize", 0, winreg.REG_DWORD, size_kb)
                
                winreg.CloseKey(app_key)
                winreg.CloseKey(key)
                
                # Register context menu
                RegistryUtils.register_context_menu()
                
                QMessageBox.information(
                    self,
                    _("Installation completed"),
                    "✅ "
                    + _("{app_name} installed successfully").format(app_name=APP_NAME)
                    + "\n\n"
                    + _("You can now run it from the Start Menu.")
                )
                    
            except Exception as e:
                QMessageBox.critical(self, ERROR_TEXT,
                    _("Error during installation:") + 
                    "\n" + str(e))
    
    def uninstall_self(self):
        """Uninstall ZipInstaller Modern from the system."""
        if custom_question_dialog(
            self,
            _("Uninstall {app_name}").format(app_name=APP_NAME),
            _("Do you want to uninstall {app_name} from this system?").format(app_name=APP_NAME),
            default_yes=False
        ):
            try:
                local_appdata = Path(SystemUtils.get_shell_folder("Local AppData"))
                install_path = local_appdata / 'Programs' / APP_NAME
                
                # Remove Start Menu shortcut
                start_menu = Path(os.environ['APPDATA']) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
                shortcut_path = start_menu / f"{APP_NAME}.lnk"
                if shortcut_path.exists():
                    shortcut_path.unlink()
                
                # Remove registry entry
                key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
                winreg.DeleteKey(key, APP_NAME)
                winreg.CloseKey(key)
                
                # Unregister context menu
                RegistryUtils.unregister_context_menu()
                
                # Create self-delete batch
                if install_path.exists():
                    exe_path = install_path / 'ZIM.exe'
                    batch_file = FileUtils.create_self_delete_batch(str(exe_path), str(install_path))
                    
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0
                    
                    subprocess.Popen(
                        ['cmd', '/c', str(batch_file)],
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
                    )
                
                QMessageBox.information(self, _("Uninstall completed"),
                    "✅ " + _("{app_name} uninstalled successfully").format(app_name=APP_NAME))
                
            except Exception as e:
                QMessageBox.critical(self, ERROR_TEXT,
                    _("Error during installation:") + 
                    "\n" + str(e))
    
    def show_about(self):
        """Show About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
    
    def create_install_panel(self):
        """Create the installation panel UI."""
        panel = QGroupBox("🚀 " + _("Install New Application"))
        panel.setFont(QFont('Segoe UI', 12, QFont.Weight.Bold))
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Step 1: Select ZIP file
        zip_group = QGroupBox("1️⃣  " + _("Select ZIP file"))
        zip_layout = QHBoxLayout()
        self.zip_path_edit = QLineEdit()
        self.zip_path_edit.setPlaceholderText(_("Select a ZIP file..."))
        self.zip_path_edit.setReadOnly(True)
        zip_layout.addWidget(self.zip_path_edit)
        
        browse_btn = QPushButton("📂 " + _("Browse"))
        browse_btn.clicked.connect(self.browse_zip)
        zip_layout.addWidget(browse_btn)
        zip_group.setLayout(zip_layout)
        layout.addWidget(zip_group)
        
        # Step 2: Configuration
        config_group = QGroupBox("2️⃣  " + _("Configuration"))
        config_layout = QVBoxLayout()
        
        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(_("Name:")))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(_("Application name"))
        self.name_edit.textChanged.connect(self.on_name_changed)
        name_layout.addWidget(self.name_edit)
        config_layout.addLayout(name_layout)
        
        # Version field (read-only, auto-detected)
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel(_("Version:")))
        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText(_("Will be auto-detected"))
        self.version_edit.setReadOnly(True)
        if SystemUtils.is_windows_dark_mode():
            self.version_edit.setStyleSheet("background-color: #353535; color: #a0a0a0;")
        else:
            self.version_edit.setStyleSheet("background-color: #f0f0f0; color: #6b7280;")
        version_layout.addWidget(self.version_edit)
        config_layout.addLayout(version_layout)
        
        # Install path field
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel(_("Install in:")))
        self.install_path_edit = QLineEdit()
        default_install = Path(SystemUtils.get_shell_folder("Local AppData")) / 'Programs'
        self.install_path_edit.setText(str(default_install))
        self.install_path_edit.textChanged.connect(self.check_install_ready)
        path_layout.addWidget(self.install_path_edit)
        
        path_browse_btn = QPushButton("📁")
        path_browse_btn.clicked.connect(self.browse_install_path)
        path_layout.addWidget(path_browse_btn)
        config_layout.addLayout(path_layout)
        
        # Executable field
        exe_layout = QHBoxLayout()
        exe_layout.addWidget(QLabel(_("Executable:")))
        self.exe_edit = QLineEdit()
        self.exe_edit.setPlaceholderText("app.exe")
        self.exe_edit.textChanged.connect(self.check_install_ready)
        exe_layout.addWidget(self.exe_edit)
        config_layout.addLayout(exe_layout)
        
        # Shortcut options
        self.desktop_check = QCheckBox(_("Create Desktop shortcut"))
        self.desktop_check.setChecked(True)
        config_layout.addWidget(self.desktop_check)
        
        self.startmenu_check = QCheckBox(_("Create Start Menu shortcut"))
        self.startmenu_check.setChecked(True)
        config_layout.addWidget(self.startmenu_check)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Install button
        self.install_btn = QPushButton("⬇️ " + _("INSTALL"))
        self.install_btn.setMinimumHeight(40)
        self.install_btn.setFont(QFont('Segoe UI', 12, QFont.Weight.Bold))
        self.install_btn.clicked.connect(self.start_install)
        self.install_btn.setEnabled(False)
        layout.addWidget(self.install_btn)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def apply_styles(self):
        """Apply dark or light theme based on Windows settings."""
        dark_mode = SystemUtils.is_windows_dark_mode()
        
        if dark_mode:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                }
                QGroupBox {
                    background-color: #2d2d2d;
                    border: 2px solid #404040;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 15px;
                    font-size: 11pt;
                    color: #e0e0e0;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    color: #e0e0e0;
                }
                QLineEdit {
                    padding: 8px;
                    border: 2px solid #404040;
                    border-radius: 4px;
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    font-size: 10pt;
                }
                QLineEdit:focus {
                    border-color: #6366f1;
                }
                QPushButton {
                    background-color: #4F46E5;
                    color: #ffffff;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #6366f1;
                }
                QPushButton:pressed {
                    background-color: #3730A3;
                }
                QPushButton:disabled {
                    background-color: #404040;
                    color: #808080;
                }
                QCheckBox {
                    spacing: 8px;
                    font-size: 10pt;
                    color: #e0e0e0;
                }
                QProgressBar {
                    border: 2px solid #404040;
                    border-radius: 4px;
                    text-align: center;
                    height: 25px;
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                }
                QProgressBar::chunk {
                    background-color: #4F46E5;
                }
                QLabel {
                    color: #e0e0e0;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f8f9fa;
                }
                QGroupBox {
                    background-color: #ffffff;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 15px;
                    font-size: 11pt;
                    color: #1f2937;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    color: #1f2937;
                }
                QLineEdit {
                    padding: 8px;
                    border: 2px solid #e5e7eb;
                    border-radius: 4px;
                    background-color: #ffffff;
                    color: #1f2937;
                    font-size: 10pt;
                }
                QLineEdit:focus {
                    border-color: #4F46E5;
                }
                QPushButton {
                    background-color: #4F46E5;
                    color: #ffffff;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #4338CA;
                }
                QPushButton:pressed {
                    background-color: #3730A3;
                }
                QPushButton:disabled {
                    background-color: #D1D5DB;
                    color: #9ca3af;
                }
                QCheckBox {
                    spacing: 8px;
                    font-size: 10pt;
                    color: #1f2937;
                }
                QProgressBar {
                    border: 2px solid #e5e7eb;
                    border-radius: 4px;
                    text-align: center;
                    height: 25px;
                    background-color: #ffffff;
                    color: #1f2937;
                }
                QProgressBar::chunk {
                    background-color: #4F46E5;
                }
                QLabel {
                    color: #1f2937;
                }
            """)
    
    def browse_zip(self):
        """Open file dialog to select ZIP file."""
        default_dir = SystemUtils.get_shell_folder("Personal")
        
        file_path, __ = QFileDialog.getOpenFileName(
            self, _("Select ZIP file"), default_dir, _("ZIP Files (*.zip)")
        )
        if file_path:
            self.load_zip_file(file_path)
    
    def load_zip_file(self, file_path):
        """
        Load and process a ZIP file, extracting metadata from executables.
        
        Args:
            file_path: Path to ZIP file
        """
        self.zip_path_edit.setText(file_path)
        
        executables, root_dir = FileUtils.find_executables_in_zip(file_path)
        
        if executables:
            first_exe = executables[0]
            self.exe_edit.setText(first_exe)
            self.zip_root_dir = root_dir
            
            # Extract executable temporarily to read metadata
            temp_dir = Path(os.environ.get('TEMP', '.')) / 'zipinstaller_temp'
            temp_dir.mkdir(exist_ok=True)
            
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    if root_dir:
                        exe_in_zip = f"{root_dir}/{first_exe}"
                        zip_ref.extract(exe_in_zip, temp_dir)
                        temp_exe = temp_dir / root_dir / first_exe
                    else:
                        zip_ref.extract(first_exe, temp_dir)
                        temp_exe = temp_dir / first_exe
                
                # Read executable metadata
                metadata = ExecutableUtils.get_exe_metadata(str(temp_exe))
                icon_path = FileUtils.get_exe_icon_path(str(temp_exe))
                self.icon_path = icon_path
                
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Extract product info
                product_name = metadata.get('ProductName', metadata.get('InternalName', Path(first_exe).stem))
                file_version = metadata.get('FileVersion', metadata.get('FileVersionRaw', metadata.get('ProductVersion', '')))
                copyright_info = metadata.get('LegalCopyright', 'ZipInstaller Modern')
                
                self.copyright_info = copyright_info
                
                # Clean up version string
                product_name = product_name.strip()
                if file_version:
                    file_version = file_version.strip().replace(',', '.').replace(' ', '')
                
                self.name_edit.setText(product_name)
                
                if file_version:
                    self.version_edit.setText(file_version)
                else:
                    self.version_edit.setText("1.0.0")
                
                # Update status
                status_msg = "✅ " + _("Found: {first_exe}").format(first_exe=first_exe)
                if root_dir:
                    status_msg += _(" (in {root_dir}/)").format(root_dir=root_dir)
                if metadata:
                    status_msg += f" - {product_name}"
                    if file_version:
                        status_msg += f" v{file_version}"
                self.status_label.setText(status_msg)
                
            except Exception as e:
                if __debug__: 
                    print(_("Error reading metadata: {error}").format(error=e))
                app_name = Path(first_exe).stem
                self.name_edit.setText(app_name)
                self.version_edit.setText("1.0.0")
                self.copyright_info = APP_NAME
                self.icon_path = ""
                self.zip_root_dir = root_dir
                self.status_label.setText("✅ " + _("Found: {first_exe} (no metadata)").format(first_exe=first_exe))
                shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            name = Path(file_path).stem
            self.name_edit.setText(name)
            self.version_edit.setText("1.0.0")
            self.copyright_info = APP_NAME
            self.icon_path = ""
            self.zip_root_dir = None
            self.status_label.setText("⚠️ " + _("No executables found in ZIP's root folder"))
        
        self.check_install_ready()
    
    def browse_install_path(self):
        """Open directory dialog to select installation path."""
        dir_path = QFileDialog.getExistingDirectory(
            self, _("Select installation directory")
        )
        if dir_path:
            self.install_path_edit.setText(dir_path)
    
    def on_name_changed(self):
        """Update installation path when name changes."""
        if self.name_edit.text():
            base_path = Path(SystemUtils.get_shell_folder("Local AppData")) / 'Programs'
            full_path = base_path / self.name_edit.text()
            self.install_path_edit.setText(str(full_path))
        self.check_install_ready()
    
    def check_install_ready(self):
        """Enable install button only when all required fields are filled."""
        ready = bool(self.zip_path_edit.text() and 
                     self.name_edit.text() and 
                     self.exe_edit.text())
        self.install_btn.setEnabled(ready)
    
    def start_install(self):
        """Start installation process in background thread."""
        install_full_path = Path(self.install_path_edit.text())
        exe_file = self.exe_edit.text()
        exe_full_path = install_full_path / exe_file
        icon_path = f"{exe_full_path},0"
        
        # Prepare installation configuration
        config = {
            'zip_file': self.zip_path_edit.text(),
            'name': self.name_edit.text(),
            'install_path': str(install_full_path.parent),
            'install_folder': install_full_path.name,
            'executable': self.exe_edit.text(),
            'version': self.version_edit.text() or '1.0.0.0',
            'product_name': self.name_edit.text(),
            'installed_by': getattr(self, 'copyright_info', APP_NAME),
            'icon_path': icon_path,
            'create_desktop': self.desktop_check.isChecked(),
            'create_startmenu': self.startmenu_check.isChecked(),
            'zip_root_dir': getattr(self, 'zip_root_dir', None)
        }
        
        # Disable UI during installation
        self.install_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start background thread
        self.install_thread = InstallThread(config)
        self.install_thread.progress.connect(self.progress_bar.setValue)
        self.install_thread.status.connect(self.status_label.setText)
        self.install_thread.finished.connect(self.install_finished)
        self.install_thread.start()
    
    def install_finished(self, success, message):
        """
        Handle installation completion.
        
        Args:
            success: True if installation succeeded
            message: Installation path or error message
        """
        self.progress_bar.setVisible(False)
        self.install_btn.setEnabled(True)
        
        if success:
            display_name = self.name_edit.text()
            version = self.version_edit.text()
            if version and version != '1.0.0':
                display_name += f" {version}"
            
            msg = "✅ " + _("{display_name} installed sucessfully").format(display_name=display_name)
            msg += "\n\n"
            msg += "📁 " + _("Location: {message}").format(message=message)
            msg += "\n\n"
            msg += _("The app will show in:")
            msg += "\n• "
            msg += _("Windows Configuration → Apps")
            msg += "\n• "
            msg += _("Control Panel → Programs")
            msg += "\n\n"
            msg += _("To uninstall:")
            msg += "\n• "
            msg += _("From Windows Configuration, or")
            msg += "\n• "
            msg += _("Running uninstall.exe from installation folder")
            
            QMessageBox.information(self, _("Installation Finished"), msg)
            
            # Clear form
            self.zip_path_edit.clear()
            self.name_edit.clear()
            self.version_edit.clear()
            self.exe_edit.clear()
            self.status_label.clear()
            self.copyright_info = APP_NAME
            self.icon_path = ""
        else:
            QMessageBox.critical(self, ERROR_TEXT, 
                f"❌ {_('Error during installation:')}\n\n{message}")


# ==================== APPLICATION SETUP ====================

def setup_application():
    """
    Setup QApplication with proper styling and translations.
    Does NOT load Qt translations - only app translations via babel.
    
    Returns:
        QApplication: Configured application instance
    """
    global _
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application icon if available
    icon_path = Path(__file__).parent / "zim.ico" if not getattr(sys, 'frozen', False) else Path(sys.executable).parent / "zim.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Load application translations (babel)
    def resource_path(relative_path):
        """Get absolute path to resource for PyInstaller compatibility."""
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        elif getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(__file__)
        return os.path.join(base_path, relative_path)

    locales_dir = resource_path("locales")

    try:
        app_translation = gettext.translation(
            "messages",
            localedir=locales_dir,
            languages=[QLocale.system().name(), QLocale.system().name().split("_")[0]],
            fallback=True,
        )
        app_translation.install()
        _ = app_translation.gettext
    except Exception as e:
        if __debug__:
            print(f"Failed to load app translations: {e}")
        _ = gettext.gettext
    
    # Setup color palette based on Windows dark mode
    dark_mode = SystemUtils.is_windows_dark_mode()
    palette = QPalette()
    
    if dark_mode:
        palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e0e0e0"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#2d2d2d"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#353535"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2d2d2d"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e0e0e0"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#e0e0e0"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#2d2d2d"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e0e0e0"))
        palette.setColor(QPalette.ColorRole.BrightText, QColor("#ff5252"))
        palette.setColor(QPalette.ColorRole.Link, QColor("#6366f1"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#4F46E5"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    else:
        palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#1f2937"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f3f4f6"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1f2937"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#1f2937"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#f3f4f6"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1f2937"))
        palette.setColor(QPalette.ColorRole.BrightText, QColor("#dc2626"))
        palette.setColor(QPalette.ColorRole.Link, QColor("#4F46E5"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#4F46E5"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    
    app.setPalette(palette)
    return app


def main():
    """Main entry point for the application."""
    # Check for ZIP file argument from command line
    zip_file_arg = None
    if len(sys.argv) > 1:
        potential_zip = sys.argv[1]
        if Path(potential_zip).exists() and potential_zip.lower().endswith('.zip'):
            zip_file_arg = potential_zip
    
    # Detect if we're running in uninstaller mode
    if getattr(sys, 'frozen', False) or (hasattr(sys, 'executable') and sys.executable.endswith('.exe')):
        current_dir = Path(sys.executable).parent
        current_exe_name = Path(sys.executable).name.lower()
    else:
        current_dir = Path(__file__).parent
        current_exe_name = Path(__file__).name.lower()
    
    install_info_file = current_dir / 'install_info.json'
    
    # Uninstaller mode: only if named uninstall.exe AND install_info.json exists
    if current_exe_name == 'uninstall.exe' and install_info_file.exists():
        app = setup_application()
        dialog = UninstallerDialog()
        result = dialog.exec()
        sys.exit(0 if result == QDialog.DialogCode.Accepted else 1)
    else:
        # Normal installer mode
        app = setup_application()
        window = ZipInstallerApp(zip_file_arg)
        window.show()
        sys.exit(app.exec())


if __name__ == '__main__':
    main()