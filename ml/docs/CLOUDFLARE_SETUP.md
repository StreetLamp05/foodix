# 🌐 HTTP Access Setup Guide

Your Restaurant Inventory Restock API is now configured to work with your Cloudflare Tunnel!

## ✅ Current Configuration

- **Local API Server**: Running on `http://localhost:8001`  
- **Cloudflare Tunnel**: Routes `work1.quentinlab.co` → `localhost:8001`
- **Web Interface**: Available at both local and public URLs

## 🚀 Access Your API

### Local Access (Development)
- **Web Interface**: http://localhost:8001/
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

### Public Access (Production) 
Once your Cloudflare tunnel is running:
- **Web Interface**: https://work1.quentinlab.co/
- **API Docs**: https://work1.quentinlab.co/docs  
- **Health Check**: https://work1.quentinlab.co/health

## 🔧 To Start Your Cloudflare Tunnel

```bash
# In your ~/.cloudflared directory, run:
cloudflared tunnel run
```

Or if you have a specific tunnel name:
```bash 
cloudflared tunnel run 8955137c-251c-4ec1-9f27-44c357e135b5
```

## 📡 API Endpoints Available

### Core Endpoints
- `GET /ping` - Simple connectivity test
- `GET /health` - API status and model health 
- `GET /categories` - Ingredient category information
- `POST /restock/predict-single` - Single ingredient prediction
- `POST /restock/recommendations` - Bulk inventory analysis

### Example API Call (from anywhere on the internet)
```bash
curl -X POST "https://work1.quentinlab.co/restock/predict-single" \
     -H "Content-Type: application/json" \
     -d '{
       "ingredient_id": "REMOTE_001",
       "ingredient_name": "Chicken Breast", 
       "inventory_start": 50.0,
       "qty_used": 12.5,
       "covers": 150
     }'
```

## 🔒 Security Notes

- Your tunnel uses HTTPS automatically (SSL/TLS encryption)
- CORS is enabled for web browser access
- Consider adding authentication for production use
- The API is currently open - add API keys if needed

## 🏪 Integration Options

Your API can now be integrated into:
- **Restaurant POS Systems** (via HTTPS calls)
- **Mobile Apps** (React Native, Flutter, etc.)
- **Web Dashboards** (React, Vue, Angular)
- **Business Intelligence Tools** (Tableau, Power BI)
- **IoT Kitchen Devices** (smart scales, inventory sensors)

## 📊 Monitoring & Logs

- Server logs: `tail -f ~/ugaHacks/api.log`
- Cloudflare tunnel logs: Check your Cloudflare dashboard
- API metrics: Available at `/health` endpoint

🎉 Your restaurant inventory API is now accessible via HTTP from anywhere in the world!