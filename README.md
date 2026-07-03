# 🎰 Casino Bot — Railway Deployment Guide

## Lokal Ishga Tushirish

```bash
# 1. Papkaga o'ting
cd casino-bot

# 2. Dependencylarni o'rnating
pip install -r requirements.txt

# 3. .env faylini tekshiring (bot token va admin ID to'g'ri)

# 4. Botni ishga tushiring
python start.py
```

## Railway Deployment

### 1-qadam: GitHub ga yuklash
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/casino-bot.git
git push -u origin main
```

### 2-qadam: Railway da loyiha yaratish
1. [railway.app](https://railway.app) ga kiring
2. "New Project" → "Deploy from GitHub repo"
3. Reponi tanlang

### 3-qadam: Environment Variables (Railway da)
Railway dashboard → Variables bo'limiga qo'shing:
```
BOT_TOKEN=8455033289:AAGcfbPQWpPKHEbXtv6XJnEdYEjyah6sSF4
ADMIN_IDS=6594366391
ADMIN_SECRET=supersecretadmintoken2024
DB_PATH=/data/casino.db
PORT=8000
COMMISSION_RATE=5
WEBAPP_URL=https://YOUR-APP.up.railway.app
ADMIN_PANEL_URL=https://YOUR-APP.up.railway.app/admin
```

### 4-qadam: Volume qo'shish (DB uchun)
Railway → Storage → Add Volume → Mount path: `/data`

### 5-qadam: URL ni .env ga qo'yish
Deploy bo'lgandan keyin URL ni `WEBAPP_URL` ga qo'ying va redeploy qiling.

### 6-qadam: Bot ga WebApp o'rnatish
[@BotFather](https://t.me/BotFather) ga yozing:
```
/setmenubutton
```
URL: `https://YOUR-APP.up.railway.app/webapp/`

## Admin Panel

URL: `https://YOUR-APP.up.railway.app/admin/`
Token: `supersecretadmintoken2024` (yoki .env da o'zgartiring)

## Funksiyalar

### Bot Komandalar
- `/start` — Bosh menyu
- `/balance` — Balans
- `/play` — O'yin WebApp
- `/deposit` — Stars to'ldirish  
- `/profile` — Profil
- `/help` — Yordam

### Admin Panel
- 📊 Dashboard — Statistika
- 👥 Foydalanuvchilar — Boshqaruv
- 💰 Balans — Qo'shish/Ayirish
- 🎮 O'yinlar — Tarix
- 💳 Tranzaksiyalar
- 📢 Xabar — Broadcast
- ⚙️ Sozlamalar — Komissiya, taymер va boshqalar
