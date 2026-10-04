# Корен във Vercel + Neon

Използвай FastAPI preset и Root Directory `./`.

Добави във Vercel Environment Variables:

| Име | Стойност |
| --- | --- |
| DATABASE_URL | PostgreSQL connection string от Neon; включи Connection pooling. Копирай само URL, без `psql`, кавички или `DATABASE_URL=`. |
| ADMIN_USER | admin |
| ADMIN_PASSWORD | Нова уникална парола, поне 12 символа. |
| SESSION_SECRET | Постоянна случайна стойност, поне 32 символа. Генерирай на Mac: `openssl rand -hex 32`. |

Не качвай тези стойности в GitHub. `SESSION_SECRET` трябва да е еднакъв при всички стартирания, за да остават валидни админ сесиите.

Кодът създава таблиците и примерните продукти при първото използване на базата. Не прехвърля локални поръчки от Mac. Промените и новите поръчки остават в Neon след рестарт/публикуване.

За персонален домейн добави APP_BASE_URL с точния HTTPS адрес. Без него кодът използва VERCEL_PROJECT_PRODUCTION_URL / VERCEL_URL. Админ редакциите изискват вход през същия адрес.

Провери началната страница, /api/products и /admin. Създай тестова поръчка с наложен платеж, виж я в панела, обнови страницата и провери, че остава. Не активирай реални Stripe плащания преди отделен тест на webhook и домейна.

Stripe е незадължителен: за тестови карти задай STRIPE_SECRET_KEY и STRIPE_WEBHOOK_SECRET и създай remote webhook към /api/stripe/webhook. Не използвай локалния Stripe CLI webhook secret.

Локалната работа със SQLite и start-mac.command остава достъпна без DATABASE_URL.
