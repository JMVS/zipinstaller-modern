# Contributing to ZipInstaller Modern

Thank you for your interest in contributing to ZipInstaller Modern! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Translation Guidelines](#translation-guidelines)

## 🤝 Code of Conduct

- Be respectful and constructive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## 🎯 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Screenshots** if applicable
- **Environment details**: Windows version, Python version (if running from source)
- **ZIP file structure** that caused the issue (if relevant)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:

- **Clear description** of the feature
- **Use cases** - why would this be useful?
- **Possible implementation** approach (optional)
- **Mockups or examples** (optional)

### Code Contributions

1. **Fork** the repository
2. **Create a branch** for your feature (`git checkout -b feature/amazing-feature`)
3. **Make your changes** following coding standards
4. **Test thoroughly**
5. **Commit** with clear messages
6. **Push** to your fork
7. **Open a Pull Request**

## 🛠️ Development Setup

### Prerequisites

- Python 3.12 or higher
- Windows 10/11 (primary target platform)
- Git

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/JMVS/zipinstaller-modern.git
cd zipinstaller-modern

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run from source
python zim.py
```

### Running Tests

```bash
# TODO: Add test framework
# python -m pytest tests/
```

## 📝 Coding Standards

### Python Style

- Follow **PEP 8** guidelines
- Use **4 spaces** for indentation (no tabs)
- Maximum line length: **100 characters** (flexible for readability)
- Use **type hints** where applicable
- Write **docstrings** for all public functions/classes

### Code Structure

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of function.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this exception occurs
    """
    # Implementation
    pass
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `InstallThread`)
- **Functions/Methods**: `snake_case` (e.g., `load_zip_file`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `APP_NAME`)
- **Private methods**: prefix with `_` (e.g., `_create_registry_entry`)

### Comments

- Write **clear, concise comments** in English
- Explain **why**, not just **what**
- Update comments when changing code
- Use `# TODO:` for future improvements
- Use `# FIXME:` for known issues

### Imports

```python
# Standard library
import sys
import os

# Third-party
from PySide6.QtWidgets import QWidget

# Local
from utils import FileUtils
```

## 📦 Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding/updating tests
- `chore`: Maintenance tasks
- `i18n`: Translation updates

### Examples

```
feat(installer): add support for nested ZIP structures

Allow installation from ZIP files where executables are in
subdirectories up to 2 levels deep.

Closes #123
```

```
fix(uninstaller): prevent crash when registry key missing

Handle WindowsError when registry key doesn't exist during
uninstallation process.

Fixes #456
```

## 🔄 Pull Request Process

1. **Update documentation** if needed (README, code comments)
2. **Ensure all tests pass** (when test suite exists)
3. **Update CHANGELOG** with your changes
4. **Reference related issues** in PR description
5. **Wait for review** from maintainers
6. **Address feedback** promptly
7. **Squash commits** if requested before merge

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Screenshots (if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
```

## 🌍 Translation Guidelines

### Adding a New Language

1. **Extract strings**:
```bash
pybabel extract -o messages.pot zim.py
```

2. **Initialize new language**:
```bash
pybabel init -i messages.pot -d locales -l <language_code>
# Example: pybabel init -i messages.pot -d locales -l fr
```

3. **Edit translation file**:
   - Open `locales/<lang>/LC_MESSAGES/messages.po`
   - Translate all `msgstr` entries
   - Keep formatting placeholders intact: `{name}`, `{version}`, etc.

4. **Compile translations**:
```bash
pybabel compile -d locales
```

5. **Test** the translation by changing Windows language settings

### Translation Best Practices

- **Maintain formality level** appropriate for the language
- **Keep UI text concise** - consider space constraints
- **Preserve placeholders**: `{name}` must remain as-is
- **Test with long strings** - some languages are more verbose
- **Use native punctuation** (e.g., ¿ ? in Spanish)
- **Translate contextually**, not literally

## 🚀 Release Process (Maintainers)

1. Update version
2. Update CHANGELOG.md
3. Create annotated tag: `git tag -a v1.2.3 -m "Release v1.2.3"`
4. Push tag: `git push origin v1.2.3`
5. GitHub Action builds and creates release automatically
6. Verify release and executable

## ❓ Questions?

- Open an issue for questions
- Check existing issues and discussions
- Contact: TBD

## 📄 License

By contributing, you agree that your contributions will be licensed under the GPLv3 License.

---

Thank you for contributing to ZipInstaller Modern! 🎉