# RAILWAY DEPLOYMENT GUIDE

## Quick Deploy Steps:

### 1. Railway.io-ga o'ting: https://railway.app

### 2. GitHub bilan login qil
- Sign up / Sign in with GitHub

### 3. New Project yarat
- "Create New Project" bosing
- "Deploy from GitHub Repo" tanlang
- Repository: wiklauefrh/kinobot tanlang

### 4. Services qo'shish (Marketplace)
1. **PostgreSQL 16**
   - "Add" bosing
   - Auto-provides DATABASE_URL

2. **Redis 7**
   - "Add" bosing
   - Auto-provides REDIS_URL

3. **Bot Service** (from Dockerfile)
   - Already created from repo

### 5. Environment Variables o'rnata

Railway dashboard → Bot service → Variables:

```env
BOT_TOKEN=8736516835:AAF_jLaDsPS1PmPwCEGHNRrgTorgd1dLWoU
BOT_USERNAME=kinobot_uz
SUPER_ADMIN_IDS=123456789

# Database & Redis auto-provided by Railway
DATABASE_URL=<auto-from-PostgreSQL>
REDIS_URL=<auto-from-Redis>

BASE_CHANNEL_ID=-1001234567890
LOG_CHANNEL_ID=-1001234567890
COMMENT_GROUP_ID=-1001234567890

FORCE_SUBSCRIPTION=true
MAINTENANCE_MODE=false
LOG_LEVEL=INFO
TZ=Asia/Tashkent
```

### 6. Deploy
- Railway auto-triggers on GitHub push
- Or manually: Railway → Bot Service → Deploy

### 7. Check Logs
- Railway → Bot Service → Logs
- Verify: "Starting polling..." ✓

---

## Railway CLI o'rnatasiz (opsional):

```powershell
npm install -g @railway/cli
railway link
railway up
```

---

## Xatosiz Deploy:

✅ GitHub auth
✅ PostgreSQL service
✅ Redis service  
✅ Environment variables
✅ Auto-deploy enabled

---

**Status**: Railway-ga push qilish tayyorlandi!

Next: https://railway.app → "Create New Project" → "Deploy from GitHub"
