# Running Locally with URL Prefix

This guide covers running the application locally for development with or without a URL prefix.

## Quick Start (No URL Prefix - Default)

### Windows
```cmd
.\start.cmd
```

### Linux/Mac
```bash
./start.sh
```

The app will be available at: `http://127.0.0.1:50505/`

## Running with URL Prefix

### Windows
```cmd
set UI_URL_PREFIX=/myapp
set VITE_URL_PREFIX=/myapp
.\start.cmd
```

### Linux/Mac
```bash
export UI_URL_PREFIX=/myapp
export VITE_URL_PREFIX=/myapp
./start.sh
```

The app will be available at: `http://127.0.0.1:50505/myapp/`

## Using .env File

Create a `.env` file in the project root:

```env
UI_URL_PREFIX=/myapp
```

Then for the frontend build, set before running start script:

**Windows:**
```cmd
set VITE_URL_PREFIX=/myapp
.\start.cmd
```

**Linux/Mac:**
```bash
export VITE_URL_PREFIX=/myapp
./start.sh
```

## Important Notes

1. **Both variables required for URL prefix:**
   - `VITE_URL_PREFIX` - Used during frontend build (affects asset paths)
   - `UI_URL_PREFIX` - Used by backend at runtime (affects API routes)
   - Both should have the same value!

2. **Format requirements:**
   - Must start with `/` (e.g., `/myapp`)
   - Must NOT end with `/` (use `/myapp` not `/myapp/`)
   - Leave empty or unset for root path hosting

3. **Rebuilding frontend:**
   If you change the URL prefix, you need to rebuild the frontend:
   ```bash
   cd frontend
   npm run build
   ```

4. **Development mode:**
   For frontend development with hot reload:
   ```bash
   # Terminal 1 - Backend
   python -m quart run --port=50505
   
   # Terminal 2 - Frontend
   cd frontend
   export VITE_URL_PREFIX=/myapp  # Optional
   npm run dev
   ```

## Troubleshooting

### "Not Found" Error
- Check that both `UI_URL_PREFIX` and `VITE_URL_PREFIX` are set to the same value
- Rebuild the frontend if you changed `VITE_URL_PREFIX`
- Verify the URL you're accessing matches the prefix

### Assets Not Loading
- The `VITE_URL_PREFIX` must be set before running `npm run build`
- Rebuild the frontend with the correct environment variable

### API Calls Failing
- Ensure `UI_URL_PREFIX` environment variable is set when starting the backend
- Check browser console for the logged prefix: "API URL prefix configured: ..."
- The backend should show the blueprint registered with the prefix in startup logs
