# KINOBOT — Railway Deploy Qo'llanma

## 1. Railway.app Loyiha Yaratish

1. https://railway.app ga kiring va GitHub bilan tizimga kiring
2. **"New Project"** → **"Deploy from GitHub repo"**
3. KINOBOT reponi tanlang

## 2. PostgreSQL Qo'shish

1. Railway dashboardida **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. PostgreSQL servisi avtomatik yaratiladi
3. **Variables** bo'limida `DATABASE_URL` avtomatik qo'shiladi

## 3. Redis Qo'shish

1. **"+ New"** → **"Database"** → **"Add Redis"**
2. Redis servisi avtomatik yaratiladi
3. **Variables** bo'limida `REDIS_URL` avtomatik qo'shiladi

## 4. Environment Variables Sozlash

Bot servisiga borib, **Variables** bo'limida quyidagilarni qo'shing:

```
BOT_TOKEN=<telegram_bot_token>
BOT_USERNAME=<bot_username>
SUPER_ADMIN_IDS=<sizning_telegram_id>

# DB va Redis Railway tomonidan avtomatik qo'shiladi:
# DATABASE_URL=<avtomatik>
# REDIS_URL=<avtomatik>

# Kanal IDlari
BASE_CHANNEL_ID=<asosiy_kanal_id>
LOG_CHANNEL_ID=<log_kanal_id>
COMMENT_GROUP_ID=<guruh_id>

# Ixtiyoriy: Userbot
API_ID=0
API_HASH=
USERBOT_SESSION_STRING=

# Sozlamalar
LOG_LEVEL=INFO
TZ=Asia/Tashkent
BROADCAST_BOT_RATE=28
```

## 5. Deploy

1. GitHub ga push qiling:
   ```bash
   git add .
   git commit -m "KINOBOT v1.0 - ready for deploy"
   git push origin main
   ```
2. Railway avtomatik deploy boshlaydi
3. **Deployments** bo'limida loglarni ko'ring

## 6. Tekshirish

1. Telegram da botga `/start` yuboring
2. Bot javob berishi kerak
3. `/admin` bilan admin panelni tekshiring
4. `/help` bilan yordam ko'ring

## 7. Xatolik Bartaraf Etish

- **Bot javob bermaydi**: Loglarni tekshiring (Railway → Service → Logs)
- **DB ulanmaydi**: `DATABASE_URL` to'g'ri ekanligini tekshiring
- **Redis ulanmaydi**: Bot avtomatik MemoryStorage ga o'tadi

## Arxitektura

```
Railway Project
├── Bot Service (Dockerfile)
│   ├── main.py (entry point)
│   ├── bot/ (handlers, middlewares, keyboards)
│   ├── db/ (models, repositories)
│   ├── services/ (broadcast, search, backup)
│   └── utils/ (helpers, logging, texts)
├── PostgreSQL (plugin)
└── Redis (plugin)
```
