# Setting Up Stadia Maps for Production

Your app now supports Stadia Maps with a dark theme! Here's how to enable it on Vercel:

## Step 1: Get a Free Stadia Maps API Key

1. Go to [**stadiamaps.com**](https://stadiamaps.com/)
2. Click "Sign Up" (it's free!)
3. After logging in, go to **Dashboard** → **API Keys**
4. Create a new API key
5. Add your Vercel domain to the **Allowed Referrers**:
   - `https://amantti-weather-service.vercel.app`
   - `https://*.vercel.app` (wildcardfor preview deployments)
6. Copy your API key

## Step 2: Add the API Key to Vercel

```bash
vercel env add VITE_STADIA_API_KEY production
# Paste your Stadia API key when prompted
```

Or via the Vercel Dashboard:

1. Go to your project → **Settings** → **Environment Variables**
2. Add:
   - **Name**: `VITE_STADIA_API_KEY`
   - **Value**: Your Stadia API key
   - **Environment**: Production (and Preview if desired)

## Step 3: Redeploy

```bash
vercel --prod
```

## How It Works

- **With API key**: Uses Stadia Maps "Alidade Smooth Dark" tiles (beautiful dark map)
- **Without API key**: Falls back to Bing Maps Aerial (default Cesium provider)

Both work great! The dark Stadia tiles just look better with your weather visualization.

## Free Tier Limits

Stadia's free tier includes:

- ✅ **20,000 map views/month**
- ✅ **200,000 API requests/month**
- ✅ Perfect for demos and small projects

## Testing Locally

Add to your `.env` file (in the frontend directory):

```bash
VITE_STADIA_API_KEY=your_api_key_here
```

Then restart your dev server:

```bash
npm run dev
```
