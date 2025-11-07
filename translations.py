# translations.py
"""
Translation Manager for ZipInstaller Modern
Gestiona las traducciones usando Babel
"""

import subprocess
import sys
import shutil
from pathlib import Path

def find_pybabel():
    """Find pybabel executable with fallbacks"""
    user_dir = Path.home()
    pybabel_locations = [
        "pybabel",  # In PATH
        user_dir / "AppData" / "Local" / "Programs" / "Python" / "Python312" / "Scripts" / "pybabel.exe",
        Path(sys.executable).parent / "Scripts" / "pybabel.exe",
    ]
    
    for pybabel in pybabel_locations:
        pybabel_path = Path(pybabel) if not isinstance(pybabel, Path) else pybabel
        
        if isinstance(pybabel, str) and shutil.which(pybabel):
            return pybabel
        
        if pybabel_path.exists():
            return str(pybabel_path)
    
    return None

def check_babel():
    """Check if Babel is available"""
    pybabel = find_pybabel()
    if not pybabel:
        print("❌ Error: Babel no está instalado")
        print("   Instala con: pip install Babel")
        return None
    return pybabel

def extract_strings():
    """Extract translatable strings from Python files"""
    print("📝 Extrayendo cadenas traducibles...")
    
    pybabel = check_babel()
    if not pybabel:
        return False
    
    # Create locales directory if it doesn't exist
    Path("locales").mkdir(exist_ok=True)
    
    # Create babel.cfg if it doesn't exist
    babel_cfg = Path("babel.cfg")
    if not babel_cfg.exists():
        print("📄 Creando babel.cfg...")
        babel_cfg.write_text("[python: **.py]\nencoding = utf-8\n")
    
    try:
        result = subprocess.run(
            [pybabel, "extract", "-F", "babel.cfg", "-o", "locales/messages.pot", "."],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Cadenas extraídas a locales/messages.pot")
            
            # Count messages
            pot_file = Path("locales/messages.pot")
            if pot_file.exists():
                content = pot_file.read_text(encoding='utf-8')
                msgid_count = content.count('msgid "') - 1  # -1 for the header
                print(f"   📊 Total de cadenas: {msgid_count}")
            return True
        else:
            print(f"❌ Error extrayendo cadenas: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def list_languages():
    """List available language translations"""
    locales_dir = Path("locales")
    if not locales_dir.exists():
        return []
    
    languages = []
    for item in locales_dir.iterdir():
        if item.is_dir() and (item / "LC_MESSAGES" / "messages.po").exists():
            languages.append(item.name)
    
    return sorted(languages)

def init_language(lang_code):
    """Initialize a new language translation"""
    print(f"🌍 Inicializando idioma: {lang_code}")
    
    pybabel = check_babel()
    if not pybabel:
        return False
    
    pot_file = Path("locales/messages.pot")
    if not pot_file.exists():
        print("❌ Error: No existe locales/messages.pot")
        print("   Ejecuta primero: python translations.py extract")
        return False
    
    # Check if language already exists
    lang_dir = Path(f"locales/{lang_code}")
    po_file = lang_dir / "LC_MESSAGES" / "messages.po"
    
    if po_file.exists():
        print(f"⚠️  El idioma {lang_code} ya existe en: {po_file}")
        response = input(f"   ¿Deseas sobrescribirlo? Esto eliminará las traducciones existentes (s/N): ")
        
        if response.lower() != 's':
            print("❌ Cancelado")
            print(f"   💡 Para actualizar un idioma existente usa: python translations.py update")
            return False
        
        # Delete existing language directory
        try:
            shutil.rmtree(lang_dir)
            print(f"   🗑️  Idioma anterior eliminado")
        except Exception as e:
            print(f"❌ Error eliminando idioma anterior: {e}")
            return False
    
    try:
        result = subprocess.run(
            [pybabel, "init", "-i", "locales/messages.pot", "-d", "locales", "-l", lang_code],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Idioma {lang_code} creado en locales/{lang_code}/LC_MESSAGES/messages.po")
            print(f"   📝 Edita el archivo .po para traducir las cadenas")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def update_languages():
    """Update existing language translations with new strings"""
    print("🔄 Actualizando idiomas existentes...")
    
    pybabel = check_babel()
    if not pybabel:
        return False
    
    pot_file = Path("locales/messages.pot")
    if not pot_file.exists():
        print("❌ Error: No existe locales/messages.pot")
        print("   Ejecuta primero: python translations.py extract")
        return False
    
    languages = list_languages()
    if not languages:
        print("⚠️  No hay idiomas para actualizar")
        print("   Usa 'init' para crear un nuevo idioma")
        return False
    
    try:
        result = subprocess.run(
            [pybabel, "update", "-i", "locales/messages.pot", "-d", "locales"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Idiomas actualizados: {', '.join(languages)}")
            print(f"   📝 Revisa y traduce las nuevas cadenas en los archivos .po")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def compile_languages():
    """Compile .po files to .mo files"""
    print("⚙️  Compilando traducciones...")
    
    pybabel = check_babel()
    if not pybabel:
        return False
    
    languages = list_languages()
    if not languages:
        print("⚠️  No hay idiomas para compilar")
        return False
    
    try:
        result = subprocess.run(
            [pybabel, "compile", "-d", "locales"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Traducciones compiladas: {', '.join(languages)}")
            
            # Check compiled files
            for lang in languages:
                mo_file = Path(f"locales/{lang}/LC_MESSAGES/messages.mo")
                if mo_file.exists():
                    size_kb = mo_file.stat().st_size / 1024
                    print(f"   📦 {lang}: {size_kb:.1f} KB")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def delete_language(lang_code):
    """Delete a language translation"""
    print(f"🗑️  Eliminando idioma: {lang_code}")
    
    lang_dir = Path(f"locales/{lang_code}")
    
    if not lang_dir.exists():
        print(f"❌ Error: El idioma {lang_code} no existe")
        return False
    
    # Confirm deletion
    response = input(f"⚠️  ¿Seguro que deseas eliminar '{lang_code}'? (s/N): ")
    if response.lower() != 's':
        print("❌ Cancelado")
        return False
    
    try:
        shutil.rmtree(lang_dir)
        print(f"✅ Idioma {lang_code} eliminado")
        return True
    except Exception as e:
        print(f"❌ Error eliminando: {e}")
        return False

def show_status():
    """Show translation status"""
    print("\n" + "="*60)
    print("📊 ESTADO DE TRADUCCIONES - ZipInstaller Modern")
    print("="*60)
    
    pot_file = Path("locales/messages.pot")
    if pot_file.exists():
        content = pot_file.read_text(encoding='utf-8')
        msgid_count = content.count('msgid "') - 1
        print(f"\n📝 Cadenas extraídas: {msgid_count}")
    else:
        print("\n⚠️  No se han extraído cadenas aún")
        print("   Ejecuta: python translations.py extract")
    
    languages = list_languages()
    
    if languages:
        print(f"\n🌍 Idiomas configurados ({len(languages)}):")
        for lang in languages:
            po_file = Path(f"locales/{lang}/LC_MESSAGES/messages.po")
            mo_file = Path(f"locales/{lang}/LC_MESSAGES/messages.mo")
            
            # Count translated strings
            if po_file.exists():
                content = po_file.read_text(encoding='utf-8')
                total = content.count('msgid "') - 1
                translated = content.count('msgstr "') - content.count('msgstr ""') - 1
                percentage = (translated / total * 100) if total > 0 else 0
                
                status = "✅" if mo_file.exists() else "⚠️ "
                print(f"   {status} {lang}: {translated}/{total} ({percentage:.0f}%) - {'Compilado' if mo_file.exists() else 'Sin compilar'}")
    else:
        print("\n⚠️  No hay idiomas configurados")
        print("   Ejecuta: python translations.py init <código_idioma>")
    
    print("="*60 + "\n")

def show_help():
    """Show help message"""
    print("\n" + "="*60)
    print("🌍 GESTOR DE TRADUCCIONES - ZipInstaller Modern")
    print("="*60)
    print("\nComandos disponibles:")
    print("\n  python translations.py extract")
    print("    📝 Extrae todas las cadenas traducibles a locales/messages.pot")
    print("\n  python translations.py init <código_idioma>")
    print("    🌍 Crea un nuevo idioma (ej: es, en, fr, de, pt)")
    print("\n  python translations.py update")
    print("    🔄 Actualiza todos los idiomas con nuevas cadenas")
    print("\n  python translations.py compile")
    print("    ⚙️  Compila los archivos .po a .mo (necesario para usar)")
    print("\n  python translations.py delete <código_idioma>")
    print("    🗑️  Elimina un idioma")
    print("\n  python translations.py status")
    print("    📊 Muestra el estado de las traducciones")
    print("\n  python translations.py help")
    print("    ❓ Muestra esta ayuda")
    print("\n" + "="*60)
    print("\n📚 Flujo de trabajo típico:")
    print("  1. python translations.py extract")
    print("  2. python translations.py init es")
    print("  3. Editar locales/es/LC_MESSAGES/messages.po")
    print("  4. python translations.py compile")
    print("  5. python build.py  # Compila el ejecutable con traducciones")
    print("\n💡 Códigos de idioma comunes:")
    print("  es = Español          en = English")
    print("  fr = Français         de = Deutsch")
    print("  pt = Português        it = Italiano")
    print("  ja = 日本語            zh = 中文")
    print("="*60 + "\n")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_status()
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "extract":
        extract_strings()
    
    elif command == "init":
        if len(sys.argv) < 3:
            print("❌ Error: Especifica un código de idioma")
            print("   Ejemplo: python translations.py init es")
        else:
            lang_code = sys.argv[2]
            init_language(lang_code)
    
    elif command == "update":
        update_languages()
    
    elif command == "compile":
        compile_languages()
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Error: Especifica un código de idioma")
            print("   Ejemplo: python translations.py delete es")
        else:
            lang_code = sys.argv[2]
            delete_language(lang_code)
    
    elif command == "status":
        show_status()
    
    elif command == "help":
        show_help()
    
    else:
        print(f"❌ Comando desconocido: {command}")
        show_help()

if __name__ == "__main__":
    main()