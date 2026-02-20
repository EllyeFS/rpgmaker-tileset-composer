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

3. **Install the application:**
   ```powershell
   pip install .
   ```

## Running the Application

```powershell
tileset-composer
```
