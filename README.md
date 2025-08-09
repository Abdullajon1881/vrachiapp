# 🏥 Healzy (Vrachiapp) — Медицинская платформа

Версия: 1.0.0 (major)

Современная платформа для онлайн‑консультаций врачей и пациентов, с голосовым AI‑ассистентом, устойчивыми WebSocket‑чатами и продвинутой безопасностью.

## ✨ Основные возможности

- **Онлайн‑консультации** (чат в реальном времени через WebSocket)
- **Поиск и профиль врачей** (специализация, документы, опыт)
- **Личный кабинет** пациента/врача
- **Авторизация** через email/пароль и **Google OAuth**
- **AI‑диагностика (Healzy AI)**: текст/голос/изображение, ответы голосом
- **Админ‑панель**: модерация заявок врачей, управление пользователями
- **Тёмная/светлая тема**, мобильная навигация, адаптивный UI

## 🛠 Архитектура

- Frontend: React 18 + Vite + SCSS
- Backend: Django 4.2 + DRF + Channels 4
- WebSockets: Daphne (ASGI) + Redis channel layer
- БД: MySQL
- Прод: PM2 (4 инстанса Daphne) + Nginx (HTTPS, HTTP/2, SPA, WS proxy)

## 🔒 Безопасность (сводка 1.0.0)

- CSRF‑защита для SPA: фронт шлёт `X-CSRFToken`, бэкенд выдаёт cookie через `/api/auth/csrf/`
- CSP (Content Security Policy) через Nginx (щадящий, с разрешёнными доменами Google OAuth)
- HSTS, SSL redirect, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, строгий `Referrer-Policy`
- DRF throttling (анти‑флуд на HTTP API)
- Rate‑limit чата (WS) через Redis
- Урезание логов до WARNING в проде

## 🚀 Быстрый старт (dev)

Предварительно: Python 3.12+, Node.js 18+, MySQL 8+, Redis 6+

1) Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

2) Frontend
```bash
cd ../
npm install
npm run dev
```

Откройте `http://localhost:5173`

## ⚙️ Переменные окружения (прод)

- `DJANGO_SECRET_KEY` — секрет Django
- `CHANNEL_LAYER=redis`, `REDIS_HOST=127.0.0.1`, `REDIS_PORT=6379`
- `DB_CONN_MAX_AGE=60`
- `DISABLE_CSRF=false` (true — временно для совместимости, но нежелательно)
- `DRF_THROTTLE_ANON=100/min`, `DRF_THROTTLE_USER=1000/min`
- `CHAT_RATE_LIMIT_PER_MIN=60` (WS‑чат), `CHAT_RATE_LIMIT_BAN_SECONDS=60`
- SMTP: `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_FROM`

## 🧩 PM2 + Daphne (прод)

Мы запускаем 4 ASGI‑инстанса через PM2 (fork mode) и балансируем в Nginx:

```javascript
// ecosystem.config.js (фрагмент)
{
  name: 'healzy-asgi-8001',
  script: '/var/www/healzy.app/backend/venv/bin/daphne',
  args: '-b 127.0.0.1 -p 8001 vrachiapp_backend.asgi:application',
  env: {
    DJANGO_SETTINGS_MODULE: 'vrachiapp_backend.settings',
    PYTHONPATH: '/var/www/healzy.app/backend',
    CHANNEL_LAYER: 'redis', REDIS_HOST: '127.0.0.1', REDIS_PORT: '6379',
    DB_CONN_MAX_AGE: '60', DISABLE_CSRF: 'false'
  }
}
```

## 🌐 Nginx (прод)

Upstream → 4 порта Daphne, SPA fallback, статика/медиа, WS proxy. CSP включает домены Google для OAuth/GIS:

```nginx
add_header Content-Security-Policy "\
  default-src 'self'; \
  img-src 'self' data: https:; \
  media-src 'self' https:; \
  script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com https://www.gstatic.com; \
  style-src 'self' 'unsafe-inline' https:; \
  connect-src 'self' https://healzy.uz wss://healzy.uz https://accounts.google.com https://oauth2.googleapis.com https://www.googleapis.com https://www.gstatic.com; \
  frame-src 'self' https://accounts.google.com; \
  base-uri 'self'; form-action 'self' https://accounts.google.com;" always;
```

После правки: `sudo nginx -t && sudo systemctl reload nginx`

## 🔄 CSRF для SPA

Фронт на старте запрашивает cookie csrftoken:

```js
useEffect(() => { fetch('https://healzy.uz/api/auth/csrf/', { credentials: 'include' }); }, []);
```

При POST/PUT/DELETE отправляйте заголовок:

```js
headers: {
  'Content-Type': 'application/json',
  'X-CSRFToken': (document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)')||[]).pop() || ''
}
```

## 📡 AI (Healzy AI)

- Backend: Google Gemini API (сервис `authentication/ai_service.py`), хранение диалогов в БД (модели `AIDialogue`, `AIMessage`).
- Frontend: компонент `AIDiagnosis` — голосовой ввод (Web Speech API), голосовой ответ (TTS), очистка текста от эмодзи.

## 🧪 Тест нагрузки / масштабирование

- Redis channel layer обязателен для множественных воркеров/серверов
- Увеличьте `ulimit -n`, sysctl (`somaxconn`, `tcp_fin_timeout`, и т.д.)
- Масштабирование — добавляйте инстансы Daphne/серверы за тем же Redis

## 🛠 Траблшутинг

- 403 на `/api/auth/google-auth/`: проверьте CSP (добавьте домены Google как в примере), наличие cookie csrftoken, `X-CSRFToken` в запросе, и настройки Google OAuth (Authorized JavaScript origins = `https://healzy.uz`).
- В чате сообщения не уходят: проверьте WS (Nginx `/ws/`), Redis работает (`redis-cli ping`), нет ли превышения rate‑limit.

## 📄 Лицензия и контакты

MIT License. Вопросы — Issues/Support.
