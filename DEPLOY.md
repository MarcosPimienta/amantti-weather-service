# 🚀 Deploying to Vercel

This guide walks you through deploying the Amantti Weather Service to Vercel.

## Prerequisites

- Vercel account (sign up at [vercel.com](https://vercel.com))
- OpenWeatherMap API key ([get one here](https://openweathermap.org/api))
- Vercel CLI (optional but recommended)

## Step 1: Install Vercel CLI (Optional)

```bash
npm i -g vercel
```

## Step 2: Login to Vercel

```bash
vercel login
```

## Step 3: Configure Environment Variables

Before deploying, you need to set up your environment variables:

### Option A: Via Vercel Dashboard (Recommended)

1. Go to [vercel.com](https://vercel.com) and create a new project
2. Import your GitHub repository (or upload manually)
3. Go to **Project Settings** → **Environment Variables**
4. Add the following variables:
   - `WEATHER_API_KEY`: Your OpenWeatherMap API key
   - `DATABASE_URL` (optional): External database URL if not using SQLite

### Option B: Via CLI

```bash
vercel env add WEATHER_API_KEY
# Enter your API key when prompted
```

## Step 4: Deploy

### From the Command Line

From the project root directory:

```bash
# Preview deployment
vercel

# Production deployment
vercel --prod
```

### From GitHub (Continuous Deployment)

1. Push your code to GitHub
2. Import the repository in Vercel dashboard
3. Vercel will automatically deploy on every push to main/master

## Step 5: Verify Deployment

After deployment, Vercel will provide a URL (e.g., `https://your-project.vercel.app`)

1. **Test the frontend**: Visit the URL to see the Cesium map
2. **Test the API**:
   - Visit `https://your-project.vercel.app/api/fetch_data`
   - Visit `https://your-project.vercel.app/api/results`

## Project Structure

```
amantti-weather-service/
├── frontend/              # Vue.js + Cesium frontend
│   ├── src/
│   └── dist/             # Built output (generated)
├── backend/              # FastAPI backend code
│   ├── api.py
│   ├── weather.py
│   └── ...
├── api/                  # Vercel serverless functions
│   ├── index.py         # Serverless wrapper
│   └── requirements.txt # Python dependencies
├── vercel.json          # Vercel configuration
└── .env                 # Local environment (don't commit!)
```

## Important Notes

### Database Considerations

**⚠️ SQLite Limitation**: Vercel serverless functions are stateless, so SQLite data won't persist between deployments.

**Solutions**:

- **For Production**: Use an external database (PostgreSQL, MySQL, etc.)
  - Recommended free options: [Neon](https://neon.tech), [Supabase](https://supabase.com), [PlanetScale](https://planetscale.com)
  - Set `DATABASE_URL` environment variable
- **For Demo**: Accept that data resets on each deployment

### CORS Configuration

The API is configured with CORS enabled (`Access-Control-Allow-Origin: *`). For production, update `api/index.py` to restrict to your frontend domain:

```python
allow_origins=["https://your-domain.vercel.app"]
```

## Troubleshooting

### Build Fails

- Check that all dependencies are in `frontend/package.json` and `api/requirements.txt`
- Verify Node.js version (should be 20.19+ or 22.12+)
- Check build logs in Vercel dashboard

### API Returns 404

- Ensure `/api/` routes are correctly configured in `vercel.json`
- Check that `api/index.py` exists and is properly formatted
- Verify Python runtime is set to 3.9+

### Database Errors

- If using external database, verify `DATABASE_URL` is set correctly
- Check database connection string format
- Ensure database is accessible from Vercel's infrastructure

### Cesium Assets Not Loading

- Verify `vite-plugin-static-copy` copied Cesium files correctly
- Check browser console for 404 errors
- Ensure `CESIUM_BASE_URL` is set to `/Cesium` in `vite.config.ts`

## Local Development

Run frontend and backend separately:

```bash
# Terminal 1: Backend
cd backend
python -m uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

The frontend proxy will forward `/api` requests to `localhost:8000`.

## Updating the Deployment

```bash
# Make your changes, then
vercel --prod
```

Or simply push to GitHub if you've set up continuous deployment.

## Resources

- [Vercel Documentation](https://vercel.com/docs)
- [FastAPI on Vercel](https://vercel.com/guides/deploying-fastapi-with-vercel)
- [Vue.js Deployment Guide](https://vuejs.org/guide/best-practices/production-deployment.html)
