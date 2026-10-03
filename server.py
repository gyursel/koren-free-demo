"""Koren local MVP: FastAPI + SQLite; admin sessions; COD + optional Stripe Checkout."""
import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, field_validator

ROOT = Path(__file__).resolve().parent
DATA = Path(os.getenv('KOREN_DATA_DIR', str(ROOT / '.data')))
DATA.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA / 'koren.sqlite3'
SECRET_FILE = DATA / 'session.secret'
if os.getenv('SESSION_SECRET'):
    SESSION_SECRET = os.environ['SESSION_SECRET'].encode()
elif SECRET_FILE.exists():
    SESSION_SECRET = SECRET_FILE.read_bytes()
else:
    SESSION_SECRET = secrets.token_bytes(32)
    fd = os.open(SECRET_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(SESSION_SECRET)
# Render supplies the default HTTPS hostname; a custom domain requires APP_BASE_URL.
DEFAULT_URL = ('https://' + os.environ['RENDER_EXTERNAL_HOSTNAME']
               if os.getenv('RENDER_EXTERNAL_HOSTNAME') else 'http://127.0.0.1:8080')
BASE_URL = os.getenv('APP_BASE_URL', DEFAULT_URL).rstrip('/')
STAGING_ONLY = os.getenv('KOREN_STAGING_ONLY') == '1'
STAGING_USER = os.getenv('STAGING_HTTP_USER', '')
STAGING_PASSWORD = os.getenv('STAGING_HTTP_PASSWORD', '')
if STAGING_ONLY and (not STAGING_USER or len(STAGING_PASSWORD) < 12):
    raise RuntimeError('За защитена тестова публикация задай STAGING_HTTP_USER и STAGING_HTTP_PASSWORD (12+ символа).')
IS_HTTPS = BASE_URL.startswith('https://')
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')
STRIPE_SECRET = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
STRIPE_ENABLED = (STRIPE_SECRET.startswith(('sk_test_', 'sk_live_'))
                  and STRIPE_WEBHOOK_SECRET.startswith('whsec_'))
if STAGING_ONLY and STRIPE_SECRET.startswith('sk_live_'):
    raise RuntimeError('Забранен е Stripe live ключ в тестовия публичен сайт.')
if STRIPE_ENABLED and STRIPE_SECRET.startswith('sk_live_') and not IS_HTTPS:
    raise RuntimeError('Реалните плащания изискват APP_BASE_URL с HTTPS адрес.')
CATEGORIES = ['Плодове', 'Зеленчуци', 'Млечни', 'Пекарна', 'Други']
COOKIE_NAME = 'koren_admin'
SESSION_TTL = 8 * 60 * 60
LOGIN_ATTEMPTS: dict[str, list[float]] = {}
app = FastAPI(title='Корен магазин', docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/assets', StaticFiles(directory=ROOT / 'assets'), name='assets')


@app.middleware('http')
async def security_headers(request: Request, call_next):
    # The Stripe webhook must remain publicly reachable; Stripe verifies its own signature.
    if STAGING_ONLY and request.url.path not in ('/healthz', '/api/stripe/webhook'):
        raw = request.headers.get('authorization', '')
        valid = False
        if raw.startswith('Basic ') and len(raw) < 1024:
            try:
                decoded = base64.b64decode(raw[6:], validate=True).decode('utf-8')
                username, sep, password = decoded.partition(':')
                valid = bool(sep and hmac.compare_digest(username.encode(), STAGING_USER.encode())
                             and hmac.compare_digest(password.encode(), STAGING_PASSWORD.encode()))
            except (ValueError, UnicodeDecodeError, binascii.Error):
                pass
        if not valid:
            return JSONResponse({'detail':'Защитена тестова версия на Корен.'}, status_code=401,
                                headers={'WWW-Authenticate':'Basic realm="Koren staging", charset="UTF-8"',
                                         'Cache-Control':'no-store', 'X-Robots-Tag':'noindex, nofollow'})
    response = await call_next(request)
    if STAGING_ONLY:
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if request.url.path.startswith(('/api/admin', '/api/orders', '/api/stripe', '/api/checkout')):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/healthz', include_in_schema=False)
def healthz():
    # The provider checks liveness without receiving authentication credentials.
    return {'ok': True}


@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout=15000')
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaction():
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def init_db():
    with connect() as db:
        db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
                price_cents INTEGER NOT NULL CHECK(price_cents>=1),
                old_price_cents INTEGER, unit TEXT NOT NULL, emoji TEXT NOT NULL,
                tint TEXT NOT NULL, badge TEXT NOT NULL DEFAULT '',
                image TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
                stock INTEGER NOT NULL DEFAULT 0 CHECK(stock>=0),
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT (datetime('now')),
                name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL,
                address TEXT NOT NULL, subtotal_cents INTEGER NOT NULL,
                shipping_cents INTEGER NOT NULL, total_cents INTEGER NOT NULL,
                method TEXT NOT NULL, payment_state TEXT NOT NULL,
                status TEXT NOT NULL, stripe_session_id TEXT UNIQUE
            );
            CREATE TABLE IF NOT EXISTS order_items (
                order_id TEXT NOT NULL REFERENCES orders(id),
                product_id TEXT NOT NULL REFERENCES products(id),
                product_name TEXT NOT NULL, unit TEXT NOT NULL,
                price_cents INTEGER NOT NULL, quantity INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
        ''')
        if not db.execute('SELECT 1 FROM products LIMIT 1').fetchone():
            for p in json.loads((ROOT / 'seed_products.json').read_text()):
                db.execute('''INSERT INTO products
                  (id,name,category,price_cents,old_price_cents,unit,emoji,tint,badge,image,description,stock,active)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (p['id'], p['name'], p['category'], cents(p['price']),
                   cents(p['oldPrice']) if p['oldPrice'] is not None else None,
                   p['unit'], p['emoji'], p['tint'], p['badge'], p['image'],
                   p['description'], p['stock'], int(p['active'])))


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def public_product(p):
    p = dict(p)
    return dict(id=p['id'], name=p['name'], category=p['category'], price=p['price_cents']/100,
                oldPrice=p['old_price_cents']/100 if p['old_price_cents'] is not None else None,
                unit=p['unit'], emoji=p['emoji'], tint=p['tint'], badge=p['badge'],
                image=p['image'], description=p['description'], stock=p['stock'], active=bool(p['active']))


def sign(raw):
    key = hashlib.sha256(SESSION_SECRET + ADMIN_PASSWORD.encode()).digest()
    return hmac.new(key, raw.encode(), hashlib.sha256).hexdigest()


def session_data(request):
    raw = request.cookies.get(COOKIE_NAME, '')
    try:
        timestamp, nonce, signature = raw.split('.')
        message = f'{timestamp}.{nonce}'
        if (hmac.compare_digest(sign(message), signature) and
            0 <= time.time() - int(timestamp) < SESSION_TTL):
            return {'csrf': sign('csrf.' + nonce)}
    except (ValueError, OverflowError):
        pass
    return None


def require_admin(request, write=False):
    if not ADMIN_PASSWORD:
        raise HTTPException(503, 'Администраторска парола не е настроена. Стартирай чрез start-mac.command.')
    data = session_data(request)
    if not data:
        raise HTTPException(401, 'Влез в администраторския панел.')
    if write:
        origin = request.headers.get('origin')
        if origin and origin.rstrip('/') != BASE_URL:
            raise HTTPException(403, 'Невалиден произход на заявката.')
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), data['csrf']):
            raise HTTPException(403, 'Невалиден защитен токен.')
    return data


class Login(BaseModel):
    username: str
    password: str


class ProductInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: Literal['Плодове','Зеленчуци','Млечни','Пекарна','Други']
    price: Decimal = Field(gt=0, le=100000)
    oldPrice: Decimal | None = Field(default=None, gt=0, le=100000)
    unit: str = Field(min_length=1, max_length=50)
    emoji: str = Field(default='🛒', max_length=12)
    tint: str = '#e7eddc'
    badge: str = Field(default='', max_length=60)
    image: str = Field(default='', max_length=500)
    description: str = Field(default='', max_length=1000)
    stock: int = Field(default=0, ge=0, le=100000)
    active: bool = True

    @field_validator('price','oldPrice')
    @classmethod
    def at_most_two_decimal_places(cls, v):
        if v is not None and v.as_tuple().exponent < -2:
            raise ValueError('Цената трябва да е с най-много два знака след запетаята.')
        return v

    @field_validator('image')
    @classmethod
    def image_url(cls, v):
        if v and not v.startswith('https://'):
            raise ValueError('Използвай HTTPS адрес за снимка.')
        return v

    @field_validator('tint')
    @classmethod
    def tint_hex(cls, v):
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', v):
            raise ValueError('Цветът трябва да е шестцифрен HEX.')
        return v


class Item(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=99)


class Customer(BaseModel):
    @field_validator('name','phone','address')
    @classmethod
    def nonempty(cls, v):
        if not v.strip():
            raise ValueError('Полето не може да бъде празно.')
        return v.strip()

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=35)
    address: str = Field(min_length=8, max_length=350)


class OrderInput(BaseModel):
    customer: Customer
    items: list[Item] = Field(min_length=1, max_length=50)
    payment_method: Literal['cod','stripe'] = 'cod'


class StatusChange(BaseModel):
    status: Literal['new','preparing','shipped','completed','cancelled']


@app.get('/')
def home():
    return FileResponse(ROOT / 'index.html')


@app.get('/styles.css')
def css():
    return FileResponse(ROOT / 'styles.css', media_type='text/css')


@app.get('/app.js')
def js():
    return FileResponse(ROOT / 'app.js', media_type='text/javascript')


@app.get('/admin')
def admin_page():
    return FileResponse(ROOT / 'admin.html')


@app.get('/admin.js')
def admin_js():
    return FileResponse(ROOT / 'admin.js', media_type='text/javascript')


@app.get('/admin.css')
def admin_css():
    return FileResponse(ROOT / 'admin.css', media_type='text/css')


@app.get('/api/config')
def config():
    return {'stripe_enabled': STRIPE_ENABLED, 'stripe_test_mode': bool(STRIPE_ENABLED and STRIPE_SECRET.startswith('sk_test_')),
            'currency': 'EUR', 'shipping_threshold_cents': 4500,
            'shipping_cents': 390}


@app.get('/api/products')
def products():
    with connect() as db:
        return [public_product(p) for p in db.execute('SELECT * FROM products WHERE active=1 ORDER BY rowid')]


@app.post('/api/admin/login')
def login(data: Login, request: Request, response: Response):
    if not ADMIN_PASSWORD:
        raise HTTPException(503, 'Не е зададена ADMIN_PASSWORD. Използвай start-mac.command.')
    key = request.client.host if request.client else 'unknown'
    now = time.time()
    attempts = [t for t in LOGIN_ATTEMPTS.get(key, []) if now - t < 900]
    if len(attempts) >= 8:
        raise HTTPException(429, 'Твърде много опити. Изчакай 15 минути.')
    if not (hmac.compare_digest(data.username, ADMIN_USER) and hmac.compare_digest(data.password, ADMIN_PASSWORD)):
        LOGIN_ATTEMPTS[key] = attempts + [now]
        raise HTTPException(401, 'Неправилни данни за вход.')
    LOGIN_ATTEMPTS.pop(key, None)
    message = f'{int(now)}.{secrets.token_hex(20)}'
    response.set_cookie(COOKIE_NAME, message + '.' + sign(message), max_age=SESSION_TTL,
                        httponly=True, secure=IS_HTTPS, samesite='lax', path='/')
    return {'ok': True}


@app.get('/api/admin/me')
def me(request: Request):
    return require_admin(request)


@app.post('/api/admin/logout')
def logout(request: Request, response: Response):
    require_admin(request, write=True)
    response.delete_cookie(COOKIE_NAME, path='/')
    return {'ok': True}


@app.get('/api/admin/products')
def admin_products(request: Request):
    require_admin(request)
    with connect() as db:
        return [public_product(p) for p in db.execute('SELECT * FROM products ORDER BY rowid DESC')]


def save_product(db, pid, p):
    db.execute('''UPDATE products SET name=?,category=?,price_cents=?,old_price_cents=?,unit=?,emoji=?,
       tint=?,badge=?,image=?,description=?,stock=?,active=? WHERE id=?''',
       (p.name,p.category,cents(p.price),cents(p.oldPrice) if p.oldPrice is not None else None,
        p.unit,p.emoji,p.tint,p.badge,p.image,p.description,p.stock,int(p.active),pid))


@app.post('/api/admin/products', status_code=201)
def add_product(p: ProductInput, request: Request):
    require_admin(request, True)
    pid = 'p-' + secrets.token_hex(6)
    with transaction() as db:
        db.execute('''INSERT INTO products(id,name,category,price_cents,unit,emoji,tint,badge,image,description,stock,active)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (pid,'Ново','Други',1,'бр.','🛒','#e7eddc','','','',0,0))
        save_product(db, pid, p)
        return public_product(db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone())


@app.put('/api/admin/products/{pid}')
def edit_product(pid: str, p: ProductInput, request: Request):
    require_admin(request, True)
    with transaction() as db:
        if not db.execute('SELECT 1 FROM products WHERE id=?', (pid,)).fetchone():
            raise HTTPException(404, 'Продуктът не е намерен.')
        save_product(db, pid, p)
        return public_product(db.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone())


@app.delete('/api/admin/products/{pid}')
def hide_product(pid: str, request: Request):
    require_admin(request, True)
    with transaction() as db:
        result = db.execute('UPDATE products SET active=0 WHERE id=?', (pid,))
        if not result.rowcount:
            raise HTTPException(404, 'Продуктът не е намерен.')
    return {'ok': True}


def restore_stock(db, order_id):
    for it in db.execute('SELECT product_id, quantity FROM order_items WHERE order_id=?', (order_id,)):
        db.execute('UPDATE products SET stock=stock+? WHERE id=?', (it['quantity'], it['product_id']))


@app.post('/api/orders', status_code=201)
def create_order(body: OrderInput):
    if body.payment_method == 'stripe' and not STRIPE_ENABLED:
        raise HTTPException(400, 'Онлайн плащанията още не са активирани.')
    if len({i.id for i in body.items}) != len(body.items):
        raise HTTPException(422, 'Повтарящи се артикули.')
    oid = 'K-' + secrets.token_hex(6).upper()
    with transaction() as db:
        rows = []
        for item in body.items:
            p = db.execute('SELECT * FROM products WHERE id=? AND active=1', (item.id,)).fetchone()
            if not p:
                raise HTTPException(400, 'Продукт вече не се предлага. Обнови количката.')
            if p['stock'] < item.quantity:
                raise HTTPException(409, f'Недостатъчна наличност: {p["name"]}.')
            rows.append((p, item.quantity))
        subtotal = sum(p['price_cents'] * qty for p, qty in rows)
        shipping = 0 if subtotal >= 4500 else 390
        total = subtotal + shipping
        state = 'pending' if body.payment_method == 'stripe' else 'cod_due'
        status = 'awaiting_payment' if body.payment_method == 'stripe' else 'new'
        customer = body.customer
        db.execute('''INSERT INTO orders(id,name,email,phone,address,subtotal_cents,shipping_cents,
            total_cents,method,payment_state,status) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (oid,customer.name.strip(),str(customer.email),customer.phone.strip(),
             customer.address.strip(),subtotal,shipping,total,body.payment_method,state,status))
        for p, qty in rows:
            db.execute('UPDATE products SET stock=stock-? WHERE id=?', (qty,p['id']))
            db.execute('INSERT INTO order_items VALUES(?,?,?,?,?,?)',
                       (oid,p['id'],p['name'],p['unit'],p['price_cents'],qty))
    if body.payment_method == 'cod':
        return {'id': oid, 'status': 'new', 'total': total/100, 'payment': 'cod_due'}
    # Checkout is hosted by Stripe; no card data ever touches this app.
    session = None
    stripe = None
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET
        line_items = [{'price_data': {'currency':'eur', 'unit_amount':p['price_cents'],
                       'product_data': {'name':p['name']}}, 'quantity':qty} for p,qty in rows]
        if shipping:
            line_items.append({'price_data':{'currency':'eur','unit_amount':shipping,
                              'product_data':{'name':'Доставка'}},'quantity':1})
        session = stripe.checkout.Session.create(mode='payment', payment_method_types=['card'],
                          customer_email=str(customer.email), locale='bg', line_items=line_items,
                          client_reference_id=oid, metadata={'order_id':oid},
                          success_url=BASE_URL+'/?checkout=return&session_id={CHECKOUT_SESSION_ID}',
                          cancel_url=BASE_URL+'/?checkout=cancelled',
                          expires_at=int(time.time())+1800)
        with transaction() as db:
            db.execute('UPDATE orders SET stripe_session_id=? WHERE id=?',(session.id,oid))
        return {'id':oid, 'status':'awaiting_payment', 'checkout_url':session.url}
    except Exception as exc:
        # Network errors can mean that Stripe created a session but the response was lost.
        # Do not silently free stock and allow a potentially duplicate payment.
        definitive_errors = (getattr(getattr(stripe, 'error', stripe), name, type(None))
                             for name in ('AuthenticationError', 'InvalidRequestError'))
        definitively_rejected = isinstance(exc, tuple(definitive_errors))
        with transaction() as db:
            row=db.execute('SELECT status FROM orders WHERE id=?',(oid,)).fetchone()
            if row and row['status']=='awaiting_payment':
                if definitively_rejected and session is None:
                    db.execute("UPDATE orders SET status='failed',payment_state='failed' WHERE id=?",(oid,))
                    restore_stock(db,oid)
                else:
                    if session is not None:
                        db.execute('UPDATE orders SET stripe_session_id=? WHERE id=?',(session.id,oid))
                    db.execute("UPDATE orders SET status='payment_review',payment_state='review' WHERE id=?",(oid,))
        raise HTTPException(502, f'Няма потвърждение за плащането на поръчка {oid}. Свържи се с магазина, преди да опиташ отново.')


@app.get('/api/checkout/status')
def checkout_status(session_id: str):
    """Public, deliberately minimal lookup: session IDs are random checkout bearer references.

    This endpoint reads our webhook-verified database status; a browser redirect is NOT
    proof that Stripe collected money. It never returns customer data.
    """
    if not (10 <= len(session_id) <= 200 and re.fullmatch(r'cs_[A-Za-z0-9_]+', session_id)):
        raise HTTPException(404, 'Сесията не е намерена.')
    with connect() as db:
        row=db.execute("SELECT id, status, payment_state FROM orders WHERE method='stripe' AND stripe_session_id=?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Сесията не е намерена.')
    return dict(row)


@app.post('/api/stripe/webhook')
async def stripe_webhook(request: Request):
    if not STRIPE_ENABLED:
        raise HTTPException(404, 'Stripe не е конфигуриран.')
    try:
        import stripe
        event = stripe.Webhook.construct_event(await request.body(),
                     request.headers.get('stripe-signature',''), STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, 'Невалиден Stripe подпис.')
    kinds=('checkout.session.completed','checkout.session.async_payment_succeeded',
           'checkout.session.async_payment_failed','checkout.session.expired')
    if event['type'] not in kinds:
        return {'received':True}
    # Prevent accidental mixing of test and live endpoints.
    if bool(event.get('livemode')) != STRIPE_SECRET.startswith('sk_live_'):
        raise HTTPException(400, 'Невалиден платежен режим.')
    session=event['data']['object']
    oid=session.get('client_reference_id')
    session_id=session.get('id')
    with transaction() as db:
        row=db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        if not row or row['method']!='stripe' or not session_id:
            return {'received':True}
        # The Stripe callback may arrive before the creating request saves session.id.
        # Correlate through the independently generated order ID + Stripe metadata,
        # and attach the session only if the amount and currency are correct.
        if (session.get('metadata') or {}).get('order_id') != oid:
            return {'received':True}
        if row['stripe_session_id'] and row['stripe_session_id']!=session_id:
            return {'received':True}
        if session.get('amount_total')!=row['total_cents'] or session.get('currency')!='eur':
            if row['status']=='awaiting_payment':
                db.execute("UPDATE orders SET status='payment_review',payment_state='review' WHERE id=?",(oid,))
            return {'received':True}
        if row['stripe_session_id'] is None:
            db.execute('UPDATE orders SET stripe_session_id=? WHERE id=?',(session_id,oid))
        if row['payment_state']=='paid':
            return {'received':True}  # Duplicate and out-of-order events must not restore stock.
        if row['status']!='awaiting_payment':
            # An unexpected paid callback after an expiry/failure requires manual review.
            if session.get('payment_status')=='paid' and event['type'] in (
                    'checkout.session.completed','checkout.session.async_payment_succeeded'):
                db.execute("UPDATE orders SET status='payment_review',payment_state='review' WHERE id=?",(oid,))
            return {'received':True}
        if event['type'] in ('checkout.session.completed','checkout.session.async_payment_succeeded'):
            if session.get('payment_status')=='paid':
                db.execute("UPDATE orders SET status='new',payment_state='paid' WHERE id=?",(oid,))
        elif event['type'] == 'checkout.session.expired':
            db.execute("UPDATE orders SET status='expired',payment_state='unpaid' WHERE id=?",(oid,))
            restore_stock(db,oid)
        elif event['type'] == 'checkout.session.async_payment_failed':
            db.execute("UPDATE orders SET status='failed',payment_state='failed' WHERE id=?",(oid,))
            restore_stock(db,oid)
    return {'received':True}


@app.get('/api/admin/orders')
def orders(request: Request):
    require_admin(request)
    with connect() as db:
        result=[]
        for row in db.execute('SELECT * FROM orders ORDER BY created_at DESC, rowid DESC LIMIT 500'):
            order=dict(row)
            order['items']=[dict(r) for r in db.execute('SELECT product_name,unit,price_cents,quantity FROM order_items WHERE order_id=?',(row['id'],))]
            result.append(order)
        return result


@app.patch('/api/admin/orders/{oid}')
def update_order(oid: str, change: StatusChange, request: Request):
    require_admin(request, True)
    with transaction() as db:
        row=db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        if not row:
            raise HTTPException(404,'Поръчката не е намерена.')
        if row['status'] in ('expired','failed','cancelled','payment_review'):
            raise HTTPException(409,'Тази поръчка не може да се редактира.')
        if row['status']=='awaiting_payment':
            raise HTTPException(409,'Изчакай потвърждение от платежния оператор.')
        if change.status=='cancelled':
            if row['payment_state']=='paid':
                raise HTTPException(409,'Платена поръчка: първо уреди възстановяване на плащането.')
            restore_stock(db,oid)
        if row['status']=='completed' and change.status!='completed':
            raise HTTPException(409,'Приключена поръчка не може да се променя.')
        if row['status']=='cancelled':
            raise HTTPException(409,'Отменена поръчка не може да се променя.')
        db.execute('UPDATE orders SET status=? WHERE id=?',(change.status,oid))
        return {'ok':True}


init_db()
