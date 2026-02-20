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
   
   > **Note:** If you get an execution policy error, run this first:
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
