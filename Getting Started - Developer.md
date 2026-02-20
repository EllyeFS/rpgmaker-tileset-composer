# Getting Started

## Prerequisites

- Python 3.10 or higher

## Setup

1. **Create a virtual environment:**
   ```powershell
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   ```powershell
   .\venv\Scripts\Activate
   ```
   
   > **Note:** If you get an execution policy error, use one of these alternatives:
   > 
   > **Option A** - Bypass for this session only:
   > ```powershell
   > powershell -ExecutionPolicy Bypass -Command ".\venv\Scripts\Activate"
   > ```
   > 
   > **Option B** - Change policy permanently for your user:
   > ```powershell
   > Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   > ```

3. **Install dependencies in editable mode:**
   ```powershell
   pip install -e ".[dev]"
   ```

## Running the Application

```powershell
tileset-composer
```

## Running Tests

```powershell
pytest
```

## Building an Executable

To create a standalone Windows executable:

```powershell
pyinstaller --onefile --windowed --name "Tileset Composer" --paths . build_entry.py
```

This creates `dist/Tileset Composer.exe`.

**Flags:**
- `--onefile`: Single .exe file (slower startup, easier distribution)
- `--windowed`: No console window (for GUI apps)
- `--name`: Sets the executable name
- `--paths .`: Adds the project root to Python path for imports

**Alternative (faster startup, folder distribution):**
```powershell
pyinstaller --onedir --windowed --name "Tileset Composer" --paths . build_entry.py
```

Creates `dist/Tileset Composer/` folder - zip the whole folder for distribution.
