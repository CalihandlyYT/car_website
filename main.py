from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import random
import string
from datetime import datetime, timedelta
import os
import sqlite3
import hashlib
import json
import threading
import time
from translations import get_translation

app = Flask(__name__, static_folder='static')
app.config['DEBUG'] = True
app.secret_key = 'supersecretkey'

# === НАСТРОЙКА БАЗЫ ДАННЫХ ===
DATABASE = 'users.db'

# === ИНИЦИАЛИЗАЦИЯ БАЗЫ ===
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                verified BOOLEAN NOT NULL DEFAULT 0,
                banned BOOLEAN NOT NULL DEFAULT 0,
                banned_until TEXT,
                ban_reason TEXT,
                last_login TEXT,
                rank TEXT DEFAULT NULL
            )
        """)
        # Добавляем колонку rank, если её нет (для существующих БД)
        try:
            conn.execute("ALTER TABLE users ADD COLUMN rank TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
        # Добавляем колонки для уведомлений об изменении ранга
        try:
            conn.execute("ALTER TABLE users ADD COLUMN rank_changed_by TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN rank_change_reason TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN rank_changed_at TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN old_rank TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN rank_notification_seen BOOLEAN DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        # Добавляем колонку password для входа по паролю
        try:
            conn.execute("ALTER TABLE users ADD COLUMN password TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        # Добавляем колонку theme для темы оформления
        try:
            conn.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'light'")
        except sqlite3.OperationalError:
            pass
        # Таблица для ежемесячных отчетов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS monthly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_month TEXT NOT NULL,
                report_year INTEGER NOT NULL,
                total_logs INTEGER DEFAULT 0,
                total_posts INTEGER DEFAULT 0,
                total_users INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                total_views INTEGER DEFAULT 0,
                total_discussions INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                total_favorites INTEGER DEFAULT 0,
                total_subscriptions INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(report_month, report_year)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                image TEXT NOT NULL,
                specs TEXT NOT NULL,
                pros TEXT NOT NULL,
                cons TEXT NOT NULL,
                author TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts (id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts (id),
                UNIQUE(post_id, user_email)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                image TEXT NOT NULL,
                price TEXT NOT NULL,
                author TEXT NOT NULL,
                contact TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sale_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                text TEXT NOT NULL,
                rating INTEGER DEFAULT 5,
                created_at TEXT NOT NULL,
                FOREIGN KEY (sale_id) REFERENCES sales (id)
            )
        """)
        # Таблица для множественных фото постов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS post_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                display_order INTEGER DEFAULT 0,
                FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
            )
        """)
        # Таблица для тегов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        # Связь постов и тегов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS post_tags (
                post_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (post_id, tag_id),
                FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        """)
        # Добавляем колонку category в posts
        try:
            conn.execute("ALTER TABLE posts ADD COLUMN category TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        # Таблица избранного
        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                post_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_email, post_id),
                FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
            )
        """)
        # Таблица подписок на авторов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_email TEXT NOT NULL,
                author_email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(subscriber_email, author_email)
            )
        """)
        # Таблица уведомлений
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                post_id INTEGER,
                author_email TEXT,
                created_at TEXT NOT NULL,
                seen BOOLEAN DEFAULT 0
            )
        """)
        # Таблица жалоб
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_email TEXT NOT NULL,
                type TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                reviewed_by TEXT,
                reviewed_at TEXT
            )
        """)
        # Таблица заявок на карьеру
        conn.execute("""
            CREATE TABLE IF NOT EXISTS career_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                full_name TEXT NOT NULL,
                bio TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)
        # Таблица просмотров постов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS post_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                viewed_at TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
                UNIQUE(post_id, user_email)
            )
        """)
        # Таблица истории просмотров
        conn.execute("""
            CREATE TABLE IF NOT EXISTS view_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                post_id INTEGER NOT NULL,
                viewed_at TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
            )
        """)
        # Таблица сохраненных поисковых запросов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                search_name TEXT NOT NULL,
                search_params TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # Таблица обсуждений (форум)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS discussions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author_email TEXT NOT NULL,
                category TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                replies_count INTEGER DEFAULT 0
            )
        """)
        # Таблица ответов в обсуждениях
        conn.execute("""
            CREATE TABLE IF NOT EXISTS discussion_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discussion_id INTEGER NOT NULL,
                author_email TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (discussion_id) REFERENCES discussions (id) ON DELETE CASCADE
            )
        """)
        # Таблица личных сообщений
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_email TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                subject TEXT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                read BOOLEAN DEFAULT 0,
                read_at TEXT
            )
        """)
        # Добавляем колонки для расширенного поиска в posts
        try:
            conn.execute("ALTER TABLE posts ADD COLUMN price TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE posts ADD COLUMN year INTEGER DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE posts ADD COLUMN power INTEGER DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE posts ADD COLUMN fuel_consumption REAL DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE posts ADD COLUMN video_url TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE posts ADD COLUMN views_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        # Добавляем колонку темы в users
        try:
            conn.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'light'")
        except sqlite3.OperationalError:
            pass
    if not os.path.exists("access.log"):
        with open("access.log", "w", encoding="utf-8") as f:
            f.write("=== ЛОГ ДОСТУПА К САЙТУ ЗАПУЩЕН ===\n")

# === АДМИНЫ ===
admins = {
    'VladimirKhudyakov': 'Voldemar130516$_',
    'VladimirKhudyakov_moderator': 'Voldemar130516$_'
}

# === СИСТЕМА РАНГОВ ===
RANKS = {
    'высшая_администрация': 7,  # Самый высокий ранг
    'вторые_аккаунты': 7,  # Самый высокий ранг (равен высшей администрации)
    'главный_админ': 6,
    'админ': 5,
    'младший_админ': 4,
    'старший_модератор': 3,
    'модератор': 2,
    'младший_модератор': 1
}

RANK_NAMES = {
    'высшая_администрация': 'Высшая Администрация',
    'главный_админ': 'Главный админ',
    'админ': 'Админ',
    'младший_админ': 'Младший админ',
    'старший_модератор': 'Старший модератор',
    'модератор': 'Модератор',
    'младший_модератор': 'Младший модератор',
    'вторые_аккаунты': 'Вторые аккаунты'
}

def get_user_rank(email):
    """Получить ранг пользователя"""
    user = get_user(email)
    if user and user.get('rank'):
        return user['rank']
    return None

def get_rank_level(rank):
    """Получить уровень ранга (число)"""
    if rank and rank in RANKS:
        return RANKS[rank]
    return 0

def can_manage_rank(admin_email, target_rank):
    """Проверить, может ли админ управлять пользователем с указанным рангом"""
    admin_rank = get_user_rank(admin_email)
    if not admin_rank:
        return False
    admin_level = get_rank_level(admin_rank)
    target_level = get_rank_level(target_rank)
    # Админ может управлять только рангами ниже своего
    return admin_level > target_level

def has_permission(email, required_rank):
    """Проверить, есть ли у пользователя достаточный ранг для действия"""
    user_rank = get_user_rank(email)
    if not user_rank:
        return False
    user_level = get_rank_level(user_rank)
    required_level = get_rank_level(required_rank)
    return user_level >= required_level

# === ФУНКЦИЯ: ЗАПИСЬ В ЛОГ-ФАЙЛ ===
def log_access(email, action, user_agent=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ua_string = user_agent if user_agent else "Неизвестно"
    log_entry = f"[{timestamp}] | {action:20} | {email:25} | {ua_string}\n"
    with open("access.log", "a", encoding="utf-8") as f:
        f.write(log_entry)

# === ГЕНЕРАЦИЯ КОДА ПОДТВЕРЖДЕНИЯ ===
def generate_otp():
    otp = ''.join(random.choices(string.digits, k=6))
    print(f"\n\033[92m🔐 КОД ПОДТВЕРЖДЕНИЯ ДЛЯ ВХОДА: {otp}\033[0m\n")
    return otp

# === РАБОТА С ПОЛЬЗОВАТЕЛЕМ В БАЗЕ ===
def get_user(email):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        return dict(row) if row else None

def create_user(email, rank=None, password=None):
    # Хешируем пароль, если он указан
    password_hash = None
    if password:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    with sqlite3.connect(DATABASE) as conn:
        # Проверяем, существует ли колонка theme
        try:
            conn.execute("SELECT theme FROM users LIMIT 1")
        except sqlite3.OperationalError:
            # Колонка не существует, добавляем её
            try:
                conn.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'light'")
                conn.commit()
            except Exception as e:
                print(f"Ошибка при добавлении колонки theme: {e}")
        
        # Пробуем вставить с theme
        try:
            conn.execute("""
                INSERT INTO users (email, verified, banned, banned_until, ban_reason, last_login, rank, 
                                  rank_changed_by, rank_change_reason, rank_changed_at, old_rank, rank_notification_seen, password, theme)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (email, False, False, None, None, None, rank, None, None, None, None, True, password_hash, 'light'))
            conn.commit()
        except sqlite3.OperationalError as e:
            # Если ошибка из-за отсутствия колонки theme, пробуем без неё
            if 'theme' in str(e).lower():
                try:
                    conn.execute("""
                        INSERT INTO users (email, verified, banned, banned_until, ban_reason, last_login, rank, 
                                          rank_changed_by, rank_change_reason, rank_changed_at, old_rank, rank_notification_seen, password)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (email, False, False, None, None, None, rank, None, None, None, None, True, password_hash))
                    conn.commit()
                    # Потом добавляем theme отдельно
                    try:
                        conn.execute("UPDATE users SET theme = 'light' WHERE email = ?", (email,))
                        conn.commit()
                    except:
                        pass
                except Exception as e2:
                    print(f"Ошибка при создании пользователя: {e2}")
                    raise
            else:
                raise

def update_user(email, **kwargs):
    fields = ", ".join([f"{key} = ?" for key in kwargs])
    values = list(kwargs.values())
    values.append(email)
    query = f"UPDATE users SET {fields} WHERE email = ?"
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(query, values)

# === ПРОВЕРКА: ЗАБАНЕН ЛИ ПОЛЬЗОВАТЕЛЬ ===
def is_user_banned(email):
    user = get_user(email)
    if not user:
        return False
    if user['banned_until']:
        try:
            banned_until = datetime.fromisoformat(user['banned_until'])
            if datetime.now() >= banned_until:
                update_user(email, banned=False, banned_until=None, ban_reason=None)
                return False
            return True
        except ValueError:
            pass
    return user['banned']

# === РАБОТА С ПОСТАМИ ===

def create_post(title, image, specs, pros, cons, author, category=None, images=None, tags=None, 
                price=None, year=None, power=None, fuel_consumption=None, video_url=None):
    specs_str = '|'.join([f"{k}:{v}" for k, v in specs.items()])
    pros_str = '|'.join(pros)
    cons_str = '|'.join(cons)
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO posts (title, image, specs, pros, cons, author, created_at, category, 
                             price, year, power, fuel_consumption, video_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, image, specs_str, pros_str, cons_str, author, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
              category, price, year, power, fuel_consumption, video_url))
        post_id = cursor.lastrowid
        
        # Добавляем дополнительные изображения
        if images:
            for idx, img_url in enumerate(images):
                if img_url.strip():
                    cursor.execute("""
                        INSERT INTO post_images (post_id, image_url, display_order)
                        VALUES (?, ?, ?)
                    """, (post_id, img_url.strip(), idx))
        
        # Добавляем теги
        if tags:
            for tag_name in tags:
                if tag_name.strip():
                    # Получаем или создаем тег
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name.strip(),))
                    tag_row = cursor.fetchone()
                    if tag_row:
                        tag_id = tag_row[0]
                    else:
                        cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name.strip(),))
                        tag_id = cursor.lastrowid
                    
                    # Связываем тег с постом
                    try:
                        cursor.execute("INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)", (post_id, tag_id))
                    except sqlite3.IntegrityError:
                        pass  # Тег уже связан
        
        conn.commit()
        return post_id

def update_post(post_id, title, image, specs, pros, cons, category=None, images=None, tags=None):
    specs_str = '|'.join([f"{k}:{v}" for k, v in specs.items()])
    pros_str = '|'.join(pros)
    cons_str = '|'.join(cons)
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE posts SET title=?, image=?, specs=?, pros=?, cons=?, category=?
            WHERE id=?
        """, (title, image, specs_str, pros_str, cons_str, category, post_id))
        
        # Удаляем старые изображения и добавляем новые
        cursor.execute("DELETE FROM post_images WHERE post_id = ?", (post_id,))
        if images:
            for idx, img_url in enumerate(images):
                if img_url.strip():
                    cursor.execute("""
                        INSERT INTO post_images (post_id, image_url, display_order)
                        VALUES (?, ?, ?)
                    """, (post_id, img_url.strip(), idx))
        
        # Удаляем старые теги и добавляем новые
        cursor.execute("DELETE FROM post_tags WHERE post_id = ?", (post_id,))
        if tags:
            for tag_name in tags:
                if tag_name.strip():
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name.strip(),))
                    tag_row = cursor.fetchone()
                    if tag_row:
                        tag_id = tag_row[0]
                    else:
                        cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name.strip(),))
                        tag_id = cursor.lastrowid
                    
                    try:
                        cursor.execute("INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)", (post_id, tag_id))
                    except sqlite3.IntegrityError:
                        pass
        
        conn.commit()

def get_all_posts(tag_filter=None, category_filter=None):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        query = "SELECT DISTINCT p.* FROM posts p"
        params = []
        
        if tag_filter:
            query += " INNER JOIN post_tags pt ON p.id = pt.post_id INNER JOIN tags t ON pt.tag_id = t.id WHERE t.name = ?"
            params.append(tag_filter)
            if category_filter:
                query += " AND p.category = ?"
                params.append(category_filter)
        elif category_filter:
            query += " WHERE p.category = ?"
            params.append(category_filter)
        
        query += " ORDER BY p.created_at DESC"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        posts = []
        for row in rows:
            specs = dict(item.split(":", 1) for item in row['specs'].split("|") if ":" in item)
            pros = [p.strip() for p in row['pros'].split("|") if p.strip()]
            cons = [c.strip() for c in row['cons'].split("|") if c.strip()]
            
            # Получаем дополнительные изображения
            cur.execute("SELECT image_url FROM post_images WHERE post_id = ? ORDER BY display_order", (row['id'],))
            additional_images = [img['image_url'] for img in cur.fetchall()]
            
            # Получаем теги
            cur.execute("""
                SELECT t.name FROM tags t
                INNER JOIN post_tags pt ON t.id = pt.tag_id
                WHERE pt.post_id = ?
            """, (row['id'],))
            tags = [tag['name'] for tag in cur.fetchall()]
            
            posts.append({
                'id': row['id'],
                'name': row['title'],
                'image': row['image'],
                'images': additional_images,
                'specs': specs,
                'pros': pros,
                'cons': cons,
                'author': row['author'],
                'created_at': row['created_at'],
                'category': dict(row).get('category'),
                'tags': tags,
                'price': dict(row).get('price'),
                'year': dict(row).get('year'),
                'power': dict(row).get('power'),
                'fuel_consumption': dict(row).get('fuel_consumption'),
                'video_url': dict(row).get('video_url')
            })
        return posts

def get_post_by_id(post_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cur.fetchone()
        if not row:
            return None
        specs = dict(item.split(":", 1) for item in row['specs'].split("|") if ":" in item)
        pros = [p.strip() for p in row['pros'].split("|") if p.strip()]
        cons = [c.strip() for c in row['cons'].split("|") if c.strip()]
        
        # Получаем дополнительные изображения
        cur.execute("SELECT image_url FROM post_images WHERE post_id = ? ORDER BY display_order", (post_id,))
        additional_images = [img['image_url'] for img in cur.fetchall()]
        
        # Получаем теги
        cur.execute("""
            SELECT t.name FROM tags t
            INNER JOIN post_tags pt ON t.id = pt.tag_id
            WHERE pt.post_id = ?
        """, (post_id,))
        tags = [tag['name'] for tag in cur.fetchall()]
        
        return {
            'id': row['id'],
            'name': row['title'],
            'image': row['image'],
            'images': additional_images,
            'specs': specs,
            'pros': pros,
            'cons': cons,
            'author': row['author'],
            'created_at': row['created_at'],
            'category': row['category'] if 'category' in row.keys() else None,
            'tags': tags,
            'price': dict(row).get('price'),
            'year': dict(row).get('year'),
            'power': dict(row).get('power'),
            'fuel_consumption': dict(row).get('fuel_consumption'),
            'video_url': dict(row).get('video_url')
        }

# === РАБОТА С КОММЕНТАРИЯМИ ===
def add_comment(post_id, author, text):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO comments (post_id, author, text, created_at)
            VALUES (?, ?, ?, ?)
        """, (post_id, author, text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

def get_comments_by_post_id(post_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT author, text, created_at FROM comments
            WHERE post_id = ? ORDER BY created_at
        """, (post_id,))
        return [dict(row) for row in cur.fetchall()]

# === РАБОТА С ЛАЙКАМИ ===
def add_like(post_id, email):
    with sqlite3.connect(DATABASE) as conn:
        try:
            conn.execute("INSERT INTO likes (post_id, user_email) VALUES (?, ?)", (post_id, email))
            return True
        except sqlite3.IntegrityError:
            return False  # Уже лайкнул

def remove_like(post_id, email):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM likes WHERE post_id = ? AND user_email = ?", (post_id, email))

def get_like_count(post_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,))
        return cur.fetchone()[0]

def has_liked(post_id, email):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM likes WHERE post_id = ? AND user_email = ?", (post_id, email))
        return cur.fetchone() is not None

# === РАБОТА С ТЕГАМИ И КАТЕГОРИЯМИ ===
def get_all_tags():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM tags ORDER BY name")
        return [row[0] for row in cur.fetchall()]

CATEGORIES = ['седан', 'купе', 'универсал', 'хэтчбек', 'кроссовер', 'внедорожник', 'кабриолет', 'пикап', 'микроавтобус']

# === РАБОТА С ИЗБРАННЫМ ===
def add_to_favorites(user_email, post_id):
    with sqlite3.connect(DATABASE) as conn:
        try:
            conn.execute("""
                INSERT INTO favorites (user_email, post_id, created_at)
                VALUES (?, ?, ?)
            """, (user_email, post_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            return True
        except sqlite3.IntegrityError:
            return False  # Уже в избранном

def remove_from_favorites(user_email, post_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM favorites WHERE user_email = ? AND post_id = ?", (user_email, post_id))

def is_favorite(user_email, post_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM favorites WHERE user_email = ? AND post_id = ?", (user_email, post_id))
        return cur.fetchone() is not None

def get_favorites(user_email):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT p.* FROM posts p
            INNER JOIN favorites f ON p.id = f.post_id
            WHERE f.user_email = ?
            ORDER BY f.created_at DESC
        """, (user_email,))
        rows = cur.fetchall()
        posts = []
        for row in rows:
            specs = dict(item.split(":", 1) for item in row['specs'].split("|") if ":" in item)
            pros = [p.strip() for p in row['pros'].split("|") if p.strip()]
            cons = [c.strip() for c in row['cons'].split("|") if c.strip()]
            
            cur.execute("SELECT image_url FROM post_images WHERE post_id = ? ORDER BY display_order", (row['id'],))
            additional_images = [img['image_url'] for img in cur.fetchall()]
            
            cur.execute("""
                SELECT t.name FROM tags t
                INNER JOIN post_tags pt ON t.id = pt.tag_id
                WHERE pt.post_id = ?
            """, (row['id'],))
            tags = [tag['name'] for tag in cur.fetchall()]
            
            posts.append({
                'id': row['id'],
                'name': row['title'],
                'image': row['image'],
                'images': additional_images,
                'specs': specs,
                'pros': pros,
                'cons': cons,
                'author': row['author'],
                'created_at': row['created_at'],
                'category': dict(row).get('category'),
                'tags': tags
            })
        return posts

# === РАБОТА С ПОДПИСКАМИ ===
def subscribe_to_author(subscriber_email, author_email):
    with sqlite3.connect(DATABASE) as conn:
        try:
            conn.execute("""
                INSERT INTO subscriptions (subscriber_email, author_email, created_at)
                VALUES (?, ?, ?)
            """, (subscriber_email, author_email, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            return True
        except sqlite3.IntegrityError:
            return False  # Уже подписан

def unsubscribe_from_author(subscriber_email, author_email):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            DELETE FROM subscriptions 
            WHERE subscriber_email = ? AND author_email = ?
        """, (subscriber_email, author_email))

def is_subscribed(subscriber_email, author_email):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM subscriptions 
            WHERE subscriber_email = ? AND author_email = ?
        """, (subscriber_email, author_email))
        return cur.fetchone() is not None

def get_subscriptions(user_email):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT author_email FROM subscriptions 
            WHERE subscriber_email = ?
        """, (user_email,))
        return [row[0] for row in cur.fetchall()]

def get_subscribers(author_email):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT subscriber_email FROM subscriptions 
            WHERE author_email = ?
        """, (author_email,))
        return [row[0] for row in cur.fetchall()]

# === РАБОТА С УВЕДОМЛЕНИЯМИ ===
def create_notification(user_email, notification_type, message, post_id=None, author_email=None):
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""
                INSERT INTO notifications (user_email, type, message, post_id, author_email, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_email, notification_type, message, post_id, author_email, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
    except Exception as e:
        print(f"Ошибка при создании уведомления: {e}")
        # Не прерываем выполнение, если уведомление не создалось

def get_notifications(user_email, unread_only=False):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if unread_only:
            cur.execute("""
                SELECT * FROM notifications 
                WHERE user_email = ? AND seen = 0
                ORDER BY created_at DESC
            """, (user_email,))
        else:
            cur.execute("""
                SELECT * FROM notifications 
                WHERE user_email = ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_email,))
        return [dict(row) for row in cur.fetchall()]

def mark_notification_seen(notification_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE notifications SET seen = 1 WHERE id = ?", (notification_id,))

# === СИСТЕМА ЕЖЕМЕСЯЧНЫХ ОТЧЕТОВ ===
def count_logs_in_month(month, year):
    """Подсчитать количество логов за месяц"""
    try:
        month_str = f"{year:04d}-{month:02d}"
        count = 0
        if os.path.exists("access.log"):
            with open("access.log", "r", encoding="utf-8") as f:
                for line in f:
                    if month_str in line:
                        count += 1
        return count
    except Exception as e:
        print(f"Ошибка при подсчете логов: {e}")
        return 0

def generate_monthly_report(month=None, year=None):
    """Генерировать месячный отчет о статистике сайта"""
    now = datetime.now()
    if month is None:
        month = now.month
    if year is None:
        year = now.year
    
    # Если это текущий месяц, берем предыдущий
    if month == now.month and year == now.year:
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
    
    month_names = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    
    report_month = month_names.get(month, f"Месяц {month}")
    
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Подсчет постов за месяц
        cur.execute("""
            SELECT COUNT(*) as count FROM posts
            WHERE strftime('%Y', created_at) = ? AND strftime('%m', created_at) = ?
        """, (str(year), f"{month:02d}"))
        total_posts = cur.fetchone()['count']
        
        # Подсчет пользователей (всего)
        cur.execute("SELECT COUNT(*) as count FROM users")
        total_users = cur.fetchone()['count']
        
        # Подсчет комментариев за месяц
        cur.execute("""
            SELECT COUNT(*) as count FROM comments
            WHERE strftime('%Y', created_at) = ? AND strftime('%m', created_at) = ?
        """, (str(year), f"{month:02d}"))
        total_comments = cur.fetchone()['count']
        
        # Подсчет лайков за месяц
        cur.execute("""
            SELECT COUNT(*) as count FROM likes
            WHERE EXISTS (
                SELECT 1 FROM posts 
                WHERE posts.id = likes.post_id 
                AND strftime('%Y', posts.created_at) = ? 
                AND strftime('%m', posts.created_at) = ?
            )
        """, (str(year), f"{month:02d}"))
        total_likes = cur.fetchone()['count']
        
        # Подсчет просмотров за месяц
        cur.execute("""
            SELECT COUNT(*) as count FROM view_history
            WHERE strftime('%Y', viewed_at) = ? AND strftime('%m', viewed_at) = ?
        """, (str(year), f"{month:02d}"))
        total_views = cur.fetchone()['count']
        
        # Подсчет обсуждений за месяц
        cur.execute("""
            SELECT COUNT(*) as count FROM discussions
            WHERE strftime('%Y', created_at) = ? AND strftime('%m', created_at) = ?
        """, (str(year), f"{month:02d}"))
        total_discussions = cur.fetchone()['count']
        
        # Подсчет сообщений за месяц
        cur.execute("""
            SELECT COUNT(*) as count FROM messages
            WHERE strftime('%Y', created_at) = ? AND strftime('%m', created_at) = ?
        """, (str(year), f"{month:02d}"))
        total_messages = cur.fetchone()['count']
        
        # Подсчет избранного (всего)
        cur.execute("SELECT COUNT(*) as count FROM favorites")
        total_favorites = cur.fetchone()['count']
        
        # Подсчет подписок (всего)
        cur.execute("SELECT COUNT(*) as count FROM subscriptions")
        total_subscriptions = cur.fetchone()['count']
        
        # Подсчет логов за месяц
        total_logs = count_logs_in_month(month, year)
        
        return {
            'report_month': report_month,
            'month': month,
            'year': year,
            'total_logs': total_logs,
            'total_posts': total_posts,
            'total_users': total_users,
            'total_comments': total_comments,
            'total_likes': total_likes,
            'total_views': total_views,
            'total_discussions': total_discussions,
            'total_messages': total_messages,
            'total_favorites': total_favorites,
            'total_subscriptions': total_subscriptions
        }

def save_monthly_report(report_data):
    """Сохранить месячный отчет в базу данных"""
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cur.execute("""
                INSERT OR REPLACE INTO monthly_reports 
                (report_month, report_year, total_logs, total_posts, total_users, 
                 total_comments, total_likes, total_views, total_discussions, 
                 total_messages, total_favorites, total_subscriptions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_data['report_month'],
                report_data['year'],
                report_data['total_logs'],
                report_data['total_posts'],
                report_data['total_users'],
                report_data['total_comments'],
                report_data['total_likes'],
                report_data['total_views'],
                report_data['total_discussions'],
                report_data['total_messages'],
                report_data['total_favorites'],
                report_data['total_subscriptions'],
                now
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при сохранении отчета: {e}")
            conn.rollback()
            return False

def get_monthly_reports(limit=12):
    """Получить последние месячные отчеты"""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM monthly_reports
            ORDER BY report_year DESC, 
                     CASE report_month
                         WHEN 'Январь' THEN 1
                         WHEN 'Февраль' THEN 2
                         WHEN 'Март' THEN 3
                         WHEN 'Апрель' THEN 4
                         WHEN 'Май' THEN 5
                         WHEN 'Июнь' THEN 6
                         WHEN 'Июль' THEN 7
                         WHEN 'Август' THEN 8
                         WHEN 'Сентябрь' THEN 9
                         WHEN 'Октябрь' THEN 10
                         WHEN 'Ноябрь' THEN 11
                         WHEN 'Декабрь' THEN 12
                         ELSE 0
                     END DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]

def mark_all_notifications_seen(user_email):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE notifications SET seen = 1 WHERE user_email = ?", (user_email,))

def get_unread_notifications_count(user_email):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM notifications WHERE user_email = ? AND seen = 0", (user_email,))
        return cur.fetchone()[0]

# === РАБОТА С ТЕМОЙ ===
def set_user_theme(email, theme):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE users SET theme = ? WHERE email = ?", (theme, email))

def get_user_theme(email):
    try:
        user = get_user(email)
        if user:
            # Проверяем, есть ли поле theme
            if 'theme' in user:
                return user.get('theme', 'light')
            else:
                # Если поля нет, устанавливаем по умолчанию
                try:
                    set_user_theme(email, 'light')
                except:
                    pass
                return 'light'
        return 'light'
    except Exception as e:
        print(f"Ошибка в get_user_theme: {e}")
        return 'light'

# === РАБОТА С ПРОСМОТРАМИ ===
def add_post_view(post_id, user_email):
    with sqlite3.connect(DATABASE) as conn:
        try:
            conn.execute("""
                INSERT INTO post_views (post_id, user_email, viewed_at)
                VALUES (?, ?, ?)
            """, (post_id, user_email, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            # Обновляем счетчик просмотров
            conn.execute("UPDATE posts SET views_count = COALESCE(views_count, 0) + 1 WHERE id = ?", (post_id,))
        except sqlite3.IntegrityError:
            pass  # Уже просмотрен
        # Добавляем в историю
        conn.execute("""
            INSERT INTO view_history (user_email, post_id, viewed_at)
            VALUES (?, ?, ?)
        """, (user_email, post_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

def get_view_history(user_email, limit=20):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT p.*, vh.viewed_at 
            FROM view_history vh
            INNER JOIN posts p ON vh.post_id = p.id
            WHERE vh.user_email = ?
            ORDER BY vh.viewed_at DESC
            LIMIT ?
        """, (user_email, limit))
        rows = cur.fetchall()
        posts = []
        for row in rows:
            specs = dict(item.split(":", 1) for item in row['specs'].split("|") if ":" in item)
            pros = [p.strip() for p in row['pros'].split("|") if p.strip()]
            cons = [c.strip() for c in row['cons'].split("|") if c.strip()]
            posts.append({
                'id': row['id'],
                'name': row['title'],
                'image': row['image'],
                'specs': specs,
                'pros': pros,
                'cons': cons,
                'author': row['author'],
                'created_at': row['created_at'],
                'viewed_at': row['viewed_at']
            })
        return posts

def get_recommendations(user_email, limit=5):
    """Рекомендации на основе истории просмотров"""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Получаем категории и теги из просмотренных постов
        cur.execute("""
            SELECT DISTINCT p.category, pt.tag_id
            FROM view_history vh
            INNER JOIN posts p ON vh.post_id = p.id
            LEFT JOIN post_tags pt ON p.id = pt.post_id
            WHERE vh.user_email = ?
            LIMIT 50
        """, (user_email,))
        viewed_data = cur.fetchall()
        if not viewed_data:
            # Если нет истории, возвращаем популярные посты
            return get_popular_posts(limit)
        
        categories = [row['category'] for row in viewed_data if row['category']]
        tag_ids = [row['tag_id'] for row in viewed_data if row['tag_id']]
        
        # Получаем ID просмотренных постов
        cur.execute("SELECT DISTINCT post_id FROM view_history WHERE user_email = ?", (user_email,))
        viewed_ids = [row[0] for row in cur.fetchall()]
        
        # Ищем похожие посты
        if not viewed_ids:
            return get_popular_posts(limit)
        
        query = "SELECT DISTINCT p.* FROM posts p WHERE p.id NOT IN (" + ",".join(["?"] * len(viewed_ids)) + ")"
        params = list(viewed_ids)
        
        if categories:
            query += " AND p.category IN (" + ",".join(["?"] * len(categories)) + ")"
            params.extend(categories)
        
        if tag_ids:
            query += " AND EXISTS (SELECT 1 FROM post_tags pt WHERE pt.post_id = p.id AND pt.tag_id IN (" + ",".join(["?"] * len(tag_ids)) + "))"
            params.extend(tag_ids)
        
        query += " ORDER BY COALESCE(p.views_count, 0) DESC, p.created_at DESC LIMIT ?"
        params.append(limit)
        
        try:
            cur.execute(query, params)
        except:
            # Если запрос не работает, возвращаем популярные посты
            return get_popular_posts(limit)
        rows = cur.fetchall()
        posts = []
        for row in rows:
            specs = dict(item.split(":", 1) for item in row['specs'].split("|") if ":" in item)
            pros = [p.strip() for p in row['pros'].split("|") if p.strip()]
            cons = [c.strip() for c in row['cons'].split("|") if c.strip()]
            posts.append({
                'id': row['id'],
                'name': row['title'],
                'image': row['image'],
                'specs': specs,
                'pros': pros,
                'cons': cons,
                'author': row['author'],
                'created_at': row['created_at']
            })
        return posts

# === РАБОТА С ПОПУЛЯРНЫМИ ПОСТАМИ ===
def get_popular_posts(limit=10, sort_by='views'):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if sort_by == 'views':
            cur.execute("""
                SELECT p.*, 
                       COALESCE(p.views_count, 0) as views,
                       (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) as likes_count,
                       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comments_count
                FROM posts p
                ORDER BY (COALESCE(p.views_count, 0) * 0.3 + 
                         (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) * 0.5 + 
                         (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) * 0.2) DESC
                LIMIT ?
            """, (limit,))
        elif sort_by == 'likes':
            cur.execute("""
                SELECT p.*, 
                       COALESCE(p.views_count, 0) as views,
                       (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) as likes_count,
                       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comments_count
                FROM posts p
                ORDER BY (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) DESC
                LIMIT ?
            """, (limit,))
        else:
            cur.execute("""
                SELECT p.*, 
                       COALESCE(p.views_count, 0) as views,
                       (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) as likes_count,
                       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comments_count
                FROM posts p
                ORDER BY (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) DESC
                LIMIT ?
            """, (limit,))
        rows = cur.fetchall()
        posts = []
        for row in rows:
            specs = dict(item.split(":", 1) for item in row['specs'].split("|") if ":" in item)
            pros = [p.strip() for p in row['pros'].split("|") if p.strip()]
            cons = [c.strip() for c in row['cons'].split("|") if c.strip()]
            posts.append({
                'id': row['id'],
                'name': row['title'],
                'image': row['image'],
                'specs': specs,
                'pros': pros,
                'cons': cons,
                'author': row['author'],
                'created_at': row['created_at'],
                'views': row['views'],
                'likes_count': row['likes_count'],
                'comments_count': row['comments_count']
            })
        return posts

def get_top_authors(limit=10):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT author,
                   COUNT(*) as posts_count,
                   SUM(COALESCE(views_count, 0)) as total_views,
                   (SELECT COUNT(*) FROM likes l INNER JOIN posts p2 ON l.post_id = p2.id WHERE p2.author = p.author) as total_likes
            FROM posts p
            GROUP BY author
            ORDER BY (posts_count * 2 + total_views * 0.1 + total_likes * 0.5) DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]

# === РАБОТА С СОХРАНЕННЫМИ ПОИСКАМИ ===
def save_search(user_email, search_name, search_params):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO saved_searches (user_email, search_name, search_params, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_email, search_name, json.dumps(search_params), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

def get_saved_searches(user_email):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM saved_searches 
            WHERE user_email = ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (user_email,))
        return [dict(row) for row in cur.fetchall()]

# === РАБОТА С ОБСУЖДЕНИЯМИ ===
def create_discussion(title, content, author_email, category=None):
    with sqlite3.connect(DATABASE) as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO discussions (title, content, author_email, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, content, author_email, category, now, now))
        return cursor.lastrowid

def get_discussions(category=None, limit=50):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if category:
            cur.execute("""
                SELECT * FROM discussions 
                WHERE category = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (category, limit))
        else:
            cur.execute("""
                SELECT * FROM discussions 
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
        return [dict(row) for row in cur.fetchall()]

def get_discussion_by_id(discussion_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM discussions WHERE id = ?", (discussion_id,))
        row = cur.fetchone()
        if row:
            # Увеличиваем просмотры
            conn.execute("UPDATE discussions SET views = views + 1 WHERE id = ?", (discussion_id,))
        return dict(row) if row else None

def add_discussion_reply(discussion_id, author_email, content):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO discussion_replies (discussion_id, author_email, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (discussion_id, author_email, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        # Обновляем счетчик ответов и время обновления
        conn.execute("""
            UPDATE discussions 
            SET replies_count = replies_count + 1, 
                updated_at = ?
            WHERE id = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), discussion_id))

def get_discussion_replies(discussion_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM discussion_replies 
            WHERE discussion_id = ?
            ORDER BY created_at ASC
        """, (discussion_id,))
        return [dict(row) for row in cur.fetchall()]

def delete_discussion(discussion_id):
    """Удалить обсуждение и все его ответы"""
    with sqlite3.connect(DATABASE) as conn:
        # Удаляем ответы (каскадное удаление должно сработать автоматически)
        conn.execute("DELETE FROM discussion_replies WHERE discussion_id = ?", (discussion_id,))
        # Удаляем обсуждение
        conn.execute("DELETE FROM discussions WHERE id = ?", (discussion_id,))
        conn.commit()

# === РАБОТА С ЛИЧНЫМИ СООБЩЕНИЯМИ ===
def send_message(sender_email, recipient_email, subject, content):
    """Отправить сообщение пользователю"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            # Проверяем, что получатель существует
            cur = conn.cursor()
            cur.execute("SELECT email FROM users WHERE email = ?", (recipient_email,))
            if not cur.fetchone():
                raise ValueError(f"Пользователь с email {recipient_email} не найден")
            
            # Вставляем сообщение
            conn.execute("""
                INSERT INTO messages (sender_email, recipient_email, subject, content, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (sender_email, recipient_email, subject or '', content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            
            # Создаем уведомление (если получатель существует)
            try:
                recipient = get_user(recipient_email)
                if recipient:
                    create_notification(recipient_email, 'message', f'Новое сообщение от {sender_email}', None, sender_email)
            except Exception as e:
                print(f"Ошибка при создании уведомления: {e}")
                # Продолжаем выполнение, даже если уведомление не создалось
    except sqlite3.Error as e:
        print(f"Ошибка базы данных при отправке сообщения: {e}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")
        import traceback
        traceback.print_exc()
        raise

def get_messages(user_email, folder='inbox'):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if folder == 'inbox':
            cur.execute("""
                SELECT * FROM messages 
                WHERE recipient_email = ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_email,))
        else:  # sent
            cur.execute("""
                SELECT * FROM messages 
                WHERE sender_email = ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_email,))
        return [dict(row) for row in cur.fetchall()]

def get_unread_messages_count(user_email):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM messages WHERE recipient_email = ? AND read = 0", (user_email,))
        return cur.fetchone()[0]

def mark_message_read(message_id, user_email):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            UPDATE messages 
            SET read = 1, read_at = ?
            WHERE id = ? AND recipient_email = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message_id, user_email))

# === РАБОТА С ЖАЛОБАМИ ===
def create_report(reporter_email, target_type, target_id, reason):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO reports (reporter_email, type, target_type, target_id, reason, created_at)
            VALUES (?, 'report', ?, ?, ?, ?)
        """, (reporter_email, target_type, target_id, reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

def get_reports(status='pending'):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM reports 
            WHERE status = ?
            ORDER BY created_at DESC
        """, (status,))
        return [dict(row) for row in cur.fetchall()]

def update_report_status(report_id, status, reviewed_by):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            UPDATE reports 
            SET status = ?, reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        """, (status, reviewed_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), report_id))

# === ПОЛУЧЕНИЕ СПИСКА АДМИНИСТРАЦИИ И МОДЕРАЦИИ ===
def get_staff_list():
    """Получить список всех пользователей с рангами (администрация и модерация)"""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT email, rank FROM users WHERE rank IS NOT NULL ORDER BY rank DESC")
        rows = cur.fetchall()
        staff = []
        for row in rows:
            rank = row['rank']
            if rank in RANK_NAMES:
                staff.append({
                    'email': row['email'],
                    'rank': rank,
                    'rank_display': RANK_NAMES[rank],
                    'rank_level': RANKS.get(rank, 0)
                })
        # Сортируем по уровню ранга (от высшего к низшему)
        staff.sort(key=lambda x: x['rank_level'], reverse=True)
        return staff

# === РАБОТА С ОБЪЯВЛЕНИЯМИ О ПРОДАЖЕ ===
def create_sale(title, description, image, price, author, contact):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO sales (title, description, image, price, author, contact, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, description or '', image, price, author, contact or '', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

def get_all_sales():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM sales ORDER BY created_at DESC")
        return [dict(row) for row in cur.fetchall()]

def get_sale_by_id(sale_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
        row = cur.fetchone()
        return dict(row) if row else None

def add_sale_review(sale_id, author, text, rating=5):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO sale_reviews (sale_id, author, text, rating, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (sale_id, author, text, rating, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

def get_sale_reviews(sale_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM sale_reviews WHERE sale_id = ? ORDER BY created_at DESC", (sale_id,))
        return [dict(row) for row in cur.fetchall()]

def update_sale(sale_id, title, description, image, price, contact):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            UPDATE sales SET title=?, description=?, image=?, price=?, contact=?
            WHERE id=?
        """, (title, description or '', image, price, contact or '', sale_id))

def delete_post(post_id):
    with sqlite3.connect(DATABASE) as conn:
        # Удаляем связанные комментарии и лайки
        conn.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM likes WHERE post_id = ?", (post_id,))
        # Удаляем сам пост
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))

def delete_sale(sale_id):
    with sqlite3.connect(DATABASE) as conn:
        # Удаляем связанные отзывы
        conn.execute("DELETE FROM sale_reviews WHERE sale_id = ?", (sale_id,))
        # Удаляем само объявление
        conn.execute("DELETE FROM sales WHERE id = ?", (sale_id,))

def delete_user(email):
    """Удалить пользователя и все связанные с ним данные"""
    with sqlite3.connect(DATABASE) as conn:
        # Определяем имя автора из email (например, user@example.com -> User)
        author_name = email.split('@')[0].title()
        
        # Получаем все посты пользователя
        cur = conn.cursor()
        cur.execute("SELECT id FROM posts WHERE author = ?", (author_name,))
        post_ids = [row[0] for row in cur.fetchall()]
        
        # Удаляем комментарии и лайки для всех постов пользователя
        for post_id in post_ids:
            conn.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
            conn.execute("DELETE FROM likes WHERE post_id = ?", (post_id,))
        
        # Удаляем все посты пользователя
        conn.execute("DELETE FROM posts WHERE author = ?", (author_name,))
        
        # Получаем все объявления пользователя
        cur.execute("SELECT id FROM sales WHERE author = ?", (author_name,))
        sale_ids = [row[0] for row in cur.fetchall()]
        
        # Удаляем отзывы для всех объявлений пользователя
        for sale_id in sale_ids:
            conn.execute("DELETE FROM sale_reviews WHERE sale_id = ?", (sale_id,))
        
        # Удаляем все объявления пользователя
        conn.execute("DELETE FROM sales WHERE author = ?", (author_name,))
        
        # Удаляем все комментарии пользователя (как автора комментариев)
        conn.execute("DELETE FROM comments WHERE author = ?", (author_name,))
        
        # Удаляем все лайки пользователя
        conn.execute("DELETE FROM likes WHERE user_email = ?", (email,))
        
        # Удаляем все отзывы пользователя (как автора отзывов)
        conn.execute("DELETE FROM sale_reviews WHERE author = ?", (author_name,))
        
        # Удаляем самого пользователя
        conn.execute("DELETE FROM users WHERE email = ?", (email,))

# === ДАННЫЕ ОБ АВТОМОБИЛЯХ ===
cars = {
    "bmw_m5_f90": {
        "name": "BMW M5 F90",
        "image": "https://upload.wikimedia.org/wikipedia/commons/3/3d/2018_BMW_M5_F90.jpg",
        "specs": {
            "Двигатель": "4.4 л V8 твин-турбо",
            "Мощность": "600 л.с. (M5 Competition — 625 л.с.)",
            "Разгон 0-100 км/ч": "3.4 сек",
            "Коробка передач": "8-ступенчатая авто",
            "Привод": "Полный (xDrive, можно отключить)"
        },
        "pros": [
            "Отличная динамика и управляемость",
            "Роскошный и технологичный салон",
            "Возможность отключения полного привода — для дрифта",
            "Высокое качество сборки"
        ],
        "cons": [
            "Очень высокое потребление топлива",
            "Дорогое обслуживание и ремонт",
            "Тяжёлый автомобиль — не всегда ощущается как 'M'"
        ]
    },
    "g_class": {
        "name": "Mercedes-Benz G-Class",
        "image": "https://upload.wikimedia.org/wikipedia/commons/6/6d/2020_Mercedes-Benz_G_550_%28W463%29_front_view.jpg",
        "specs": {
            "Двигатель": "4.0 л V8 твин-турбо (G 500/G 63)",
            "Мощность": "425 л.с. (G 500), 585 л.с. (G 63)",
            "Разгон 0-100 км/ч": "4.5 сек (G 63)",
            "Коробка передач": "9-ступенчатая авто",
            "Привод": "Полный, три блокировки дифференциалов"
        },
        "pros": [
            "Легендарный внедорожник, узнаваемый стиль",
            "Отличная проходимость и надёжность",
            "Роскошный, премиальный салон",
            "Высокий статус и престиж"
        ],
        "cons": [
            "Очень высокая цена, особенно G 63",
            "Плохая манёвренность и высокий расход топлива",
            "Устаревшая подвеска — жёсткая на асфальте"
        ]
    },
    "e53_amg": {
        "name": "Mercedes-Benz E53 AMG",
        "image": "https://upload.wikimedia.org/wikipedia/commons/9/9d/2019_Mercedes-Benz_E53_AMG_%28W213%29_front_view.jpg",
        "specs": {
            "Двигатель": "3.0 л I6 турбо + электромотор (EQ Boost)",
            "Мощность": "435 л.с.",
            "Разгон 0-100 км/ч": "4.5 сек",
            "Коробка передач": "9-ступенчатая авто",
            "Привод": "Полный (4MATIC+)"
        },
        "pros": [
            "Отличный баланс комфорта и динамики",
            "Электромотор помогает в разгоне и экономит топливо",
            "Красивый и технологичный интерьер",
            "Хороший выбор для повседневной езды"
        ],
        "cons": [
            "Меньше мощности по сравнению с E63",
            "Не такой агрессивный характер, как у настоящего AMG",
            "Цена выше, чем у обычного E-Class"
        ]
    },
    "e63s_w213": {
        "name": "Mercedes-AMG E63 S W213",
        "image": "https://upload.wikimedia.org/wikipedia/commons/5/5d/2018_Mercedes-AMG_E63_S_%28W213%29_front_view.jpg",
        "specs": {
            "Двигатель": "4.0 л V8 твин-турбо",
            "Мощность": "612 л.с.",
            "Разгон 0-100 км/ч": "3.4 сек",
            "Коробка передач": "9-ступенчатая авто",
            "Привод": "Полный (можно переключить в задний)"
        },
        "pros": [
            "Один из самых быстрых седанов в мире",
            "Мощный и басовитый звук выхлопа",
            "AMG Ride Control — отличная подвеска",
            "Просторный салон и багажник"
        ],
        "cons": [
            "Очень высокий расход топлива",
            "Огромная цена и обслуживание",
            "Тяжёлый — чувствуется в поворотах"
        ]
    },
    "porsche_911": {
        "name": "Porsche 911 (992)",
        "image": "https://upload.wikimedia.org/wikipedia/commons/0/04/2020_Porsche_911_Turbo_S_%28992%29.jpg",
        "specs": {
            "Двигатель": "3.0 л H6 твин-турбо",
            "Мощность": "450 л.с. (Carrera S)",
            "Разгон 0-100 км/ч": "3.7 сек",
            "Коробка передач": "8-ступенчатая PDK",
            "Привод": "Задний / Полный (4S)"
        },
        "pros": [
            "Легендарный дизайн и звук",
            "Отличная управляемость и точность",
            "Высокое качество сборки",
            "Подходит и для города, и для трека"
        ],
        "cons": [
            "Ограниченное пространство для ног сзади",
            "Жёсткая подвеска — не для плохих дорог",
            "Опции очень дорогие"
        ]
    },
    "audi_rs6": {
        "name": "Audi RS6 Avant (C8)",
        "image": "https://upload.wikimedia.org/wikipedia/commons/5/5f/2020_Audi_RS6_Avant_%284K%29.jpg",
        "specs": {
            "Двигатель": "4.0 л V8 твин-турбо",
            "Мощность": "600 л.с.",
            "Разгон 0-100 км/ч": "3.6 сек",
            "Коробка передач": "8-ступенчатая авто",
            "Привод": "Полный (quattro)"
        },
        "pros": [
            "Самый быстрый универсал в мире",
            "Огромный багажник и практичность",
            "Комфортная подвеска с адаптивом",
            "Высокотехнологичный салон"
        ],
        "cons": [
            "Очень высокий расход топлива",
            "Огромные колёса — чувствительны к ямам",
            "Дорогой ремонт и страховка"
        ]
    },
    "tesla_model_s": {
        "name": "Tesla Model S Plaid",
        "image": "https://upload.wikimedia.org/wikipedia/commons/9/92/Tesla_Model_S_Plaid_01.jpg",
        "specs": {
            "Тип": "Электромобиль",
            "Мощность": "1020 л.с. (официально)",
            "Разгон 0-100 км/ч": "1.99 сек (по заявлениям Tesla)",
            "Запас хода": "около 600 км",
            "Привод": "Полный (три мотора)"
        },
        "pros": [
            "Невероятное ускорение — близко к суперкарам",
            "Тихая и плавная езда",
            "Автопилот и передовые технологии",
            "Низкие эксплуатационные расходы"
        ],
        "cons": [
            "Очень высокая цена",
            "Интерьер минималистичный — не всем нравится",
            "Зависимость от сети зарядок"
        ]
    },
    "lexus_lc": {
        "name": "Lexus LC 500",
        "image": "https://upload.wikimedia.org/wikipedia/commons/4/40/2018_Lexus_LC_500_%28US%29_front_view.jpg",
        "specs": {
            "Двигатель": "5.0 л V8 атмосферный",
            "Мощность": "477 л.с.",
            "Разгон 0-100 км/ч": "4.7 сек",
            "Коробка передач": "10-ступенчатая авто",
            "Привод": "Задний"
        },
        "pros": [
            "Потрясающий дизайн — как суперкар",
            "Роскошный и качественный салон",
            "Атмосферный V8 с басовитым звуком",
            "Отличная плавность хода"
        ],
        "cons": [
            "Очень высокий расход топлива",
            "Не самая острая управляемость",
            "Спорная внешность — не всем нравится"
        ]
    },
    "ford_shelby": {
        "name": "Ford Mustang Shelby GT500",
        "image": "https://upload.wikimedia.org/wikipedia/commons/3/39/2020_Ford_Mustang_SHELBY_GT500.jpg",
        "specs": {
            "Двигатель": "5.2 л V8 с приводным компрессором",
            "Мощность": "760 л.с.",
            "Разгон 0-100 км/ч": "3.5 сек",
            "Коробка передач": "7-ступенчатая DCT",
            "Привод": "Задний"
        },
        "pros": [
            "Один из самых мощных серийных V8",
            "Отличный звук двигателя",
            "Высокая производительность на треке",
            "Более доступная цена по сравнению с евро-аналогами"
        ],
        "cons": [
            "Салон — не на уровне премиум-брендов",
            "Жёсткая подвеска — не для повседневной езды",
            "Большой расход топлива"
        ]
    },
    "tesla_model_3": {
        "name": "Tesla Model 3",
        "image": "https://upload.wikimedia.org/wikipedia/commons/e/e7/Tesla_Model_3_Performance_AWD_December_2022.jpg",
        "specs": {
            "Тип": "Электромобиль",
            "Мощность": "283–450 л.с. (в зависимости от версии)",
            "Разгон 0-100 км/ч": "3.3–6.1 сек",
            "Запас хода": "до 580 км (Long Range)",
            "Привод": "Задний / Полный"
        },
        "pros": [
            "Отличный запас хода и низкие расходы",
            "Автопилот и OTA-обновления",
            "Просторный салон и багажник",
            "Быстрые зарядки на станциях Tesla"
        ],
        "cons": [
            "Минималистичный интерьер — не всем нравится",
            "Качество сборки — ниже, чем у премиум-брендов",
            "Ограниченная доступность сервисов"
        ]
    }
}

# === МАРШРУТЫ ===

@app.route('/')
def index():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))

    # Проверяем бан
    if is_user_banned(email):
        user = get_user(email)
        reason = user['ban_reason'] if user and user['ban_reason'] else 'Не указана'
        log_access(email, "ДОСТУП ЗАПРЕЩЕН (временный бан)")
        banned_until = datetime.fromisoformat(user['banned_until']) if user and user['banned_until'] else None
        until = banned_until.strftime('%Y-%m-%d %H:%M:%S') if banned_until else 'навсегда'
        return render_template('banned.html', email=email, until=until, reason=reason)

    user_data = get_user(email)
    if user_data and user_data['banned'] and not user_data['banned_until']:
        reason = user_data['ban_reason'] if user_data['ban_reason'] else 'Не указана'
        log_access(email, "ДОСТУП ЗАПРЕЩЕН (постоянный бан)")
        return render_template('banned.html', email=email, until='навсегда', reason=reason)

    log_access(email, "ДОСТУП РАЗРЕШЕН")
    selected_car = request.args.get('car', 'bmw_m5_f90')
    car_data = cars.get(selected_car, cars['bmw_m5_f90'])
    
    # Отладочная информация (можно убрать после проверки)
    if not car_data.get('image'):
        print(f"ВНИМАНИЕ: У автомобиля {car_data.get('name', 'Unknown')} нет изображения!")
    else:
        print(f"Автомобиль {car_data.get('name', 'Unknown')} имеет изображение: {car_data.get('image')}")

    # Фильтрация по тегам и категориям
    tag_filter = request.args.get('tag')
    category_filter = request.args.get('category')
    
    # Поиск постов
    search_query = request.args.get('q', '').lower()
    posts = get_all_posts(tag_filter=tag_filter, category_filter=category_filter)
    if search_query:
        posts = [p for p in posts if search_query in p['name'].lower() or search_query in p['author'].lower()]

    # Добавляем лайки, избранное и количество комментариев
    for post in posts:
        post['liked'] = has_liked(post['id'], email)
        post['favorited'] = is_favorite(email, post['id'])
        post['likes'] = get_like_count(post['id'])
        post['comments_count'] = len(get_comments_by_post_id(post['id']))
        # Проверяем подписку на автора
        author_email = post['author'].lower() + '@example.com'
        post['subscribed'] = is_subscribed(email, author_email)

    # Получаем список администрации и модерации
    staff_list = get_staff_list()
    
    # Получаем все теги и категории для фильтров
    all_tags = get_all_tags()
    
    # Получаем количество непрочитанных уведомлений
    unread_count = get_unread_notifications_count(email)
    
    # Получаем текущий язык
    current_lang = session.get('language', 'ru')
    
    # Получаем тему пользователя
    user_theme = get_user_theme(email)

    return render_template('index.html', car=car_data, cars=cars, selected=selected_car, posts=posts, 
                         search_query=search_query, staff_list=staff_list, all_tags=all_tags, 
                         categories=CATEGORIES, tag_filter=tag_filter, category_filter=category_filter,
                         unread_notifications=unread_count, lang=current_lang, t=get_translation, user_theme=user_theme)

@app.route('/create_post', methods=['GET', 'POST'])
def create_post_route():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))

    if is_user_banned(email):
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        image = request.form['image'].strip()
        category = request.form.get('category', '').strip() or None
        
        # Дополнительные изображения
        additional_images = [img.strip() for img in request.form.getlist('additional_images') if img.strip()]
        
        # Теги
        tags = [tag.strip() for tag in request.form.getlist('tags') if tag.strip()]

        # Характеристики
        spec_keys = request.form.getlist('spec_key')
        spec_values = request.form.getlist('spec_value')
        specs = {k: v for k, v in zip(spec_keys, spec_values) if k and v}

        # Плюсы и минусы
        pros = [p.strip() for p in request.form.getlist('pro') if p.strip()]
        cons = [c.strip() for c in request.form.getlist('con') if c.strip()]

        if not title or not image or not specs or not pros:
            return render_template('create_post.html', error="Заполните все обязательные поля", 
                                categories=CATEGORIES, all_tags=get_all_tags())

        # Новые поля для расширенного поиска
        price = request.form.get('price', '').strip() or None
        year = request.form.get('year', '').strip()
        year = int(year) if year and year.isdigit() else None
        power = request.form.get('power', '').strip()
        power = int(power) if power and power.isdigit() else None
        fuel_consumption = request.form.get('fuel_consumption', '').strip()
        fuel_consumption = float(fuel_consumption.replace(',', '.')) if fuel_consumption else None
        video_url = request.form.get('video_url', '').strip() or None

        author = email.split('@')[0].title()
        post_id = create_post(title, image, specs, pros, cons, author, category, additional_images, tags,
                             price, year, power, fuel_consumption, video_url)
        
        # Отправляем уведомления подписчикам
        author_email = email
        subscribers = get_subscribers(author_email)
        for subscriber in subscribers:
            create_notification(
                subscriber, 
                'new_post', 
                f'Новый пост от {author}: {title}',
                post_id=post_id,
                author_email=author_email
            )
        
        log_access(email, "СОЗДАН ПОСТ", title)
        return redirect(url_for('index'))

    return render_template('create_post.html', categories=CATEGORIES, all_tags=get_all_tags())


# ✅ ИСПРАВЛЕНО: переименовано в add_comment_route чтобы избежать конфликта с функцией add_comment
@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment_route(post_id):
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))

    text = request.form['text'].strip()
    if not text:
        return redirect(url_for('view_post', post_id=post_id))

    author = email.split('@')[0].title()
    add_comment(post_id, author, text)
    
    # Отправляем уведомление автору поста
    post = get_post_by_id(post_id)
    if post:
        post_author_email = post['author'].lower() + '@example.com'
        # Не отправляем уведомление, если комментирует сам автор
        if post_author_email != email:
            commenter_name = author
            create_notification(
                post_author_email,
                'comment',
                f'{commenter_name} прокомментировал ваш пост "{post["name"]}"',
                post_id=post_id,
                author_email=email
            )
    
    log_access(email, "КОММЕНТАРИЙ", f"к посту {post_id}")
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/like/<int:post_id>')
def like_post(post_id):
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))

    post = get_post_by_id(post_id)
    if not post:
        return "<h1>Пост не найден</h1>", 404

    if has_liked(post_id, email):
        remove_like(post_id, email)
        log_access(email, "УБРАЛ ЛАЙК", f"с поста {post_id}")
    else:
        add_like(post_id, email)
        # Отправляем уведомление автору поста
        post_author_email = post['author'].lower() + '@example.com'
        # Не отправляем уведомление, если лайкает сам автор
        if post_author_email != email:
            liker_name = email.split('@')[0].title()
            create_notification(
                post_author_email,
                'like',
                f'{liker_name} поставил лайк вашему посту "{post["name"]}"',
                post_id=post_id,
                author_email=email
            )
        log_access(email, "ПОСТАВИЛ ЛАЙК", f"на пост {post_id}")

    return redirect(url_for('index'))

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))

    post = get_post_by_id(post_id)
    if not post:
        return "<h1>Пост не найден</h1>", 404

    author_email_domain = post['author'].lower() + '@example.com'
    if email != author_email_domain and email.split('@')[0].title() != post['author']:
        return "<h1>Редактировать можно только свой пост</h1>", 403

    if request.method == 'POST':
        title = request.form['title'].strip()
        image = request.form['image'].strip()
        category = request.form.get('category', '').strip() or None
        
        # Дополнительные изображения
        additional_images = [img.strip() for img in request.form.getlist('additional_images') if img.strip()]
        
        # Теги
        tags = [tag.strip() for tag in request.form.getlist('tags') if tag.strip()]

        spec_keys = request.form.getlist('spec_key')
        spec_values = request.form.getlist('spec_value')
        specs = {k: v for k, v in zip(spec_keys, spec_values) if k and v}

        pros = [p.strip() for p in request.form.getlist('pro') if p.strip()]
        cons = [c.strip() for c in request.form.getlist('con') if c.strip()]

        if not title or not image or not specs or not pros:
            return render_template('edit_post.html', post=post, error="Заполните все обязательные поля",
                                categories=CATEGORIES, all_tags=get_all_tags())

        update_post(post_id, title, image, specs, pros, cons, category, additional_images, tags)
        log_access(email, "ОБНОВИЛ ПОСТ", f"ID {post_id}")
        return redirect(url_for('view_post', post_id=post_id))

    return render_template('edit_post.html', post=post, categories=CATEGORIES, all_tags=get_all_tags())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form.get('password', '')
        
        if not password:
            return render_template('login.html', error="Введите пароль")
        
        user = get_user(email)
        
        # Если пользователь не существует
        if not user:
            return render_template('login.html', error="Пользователь не найден. Зарегистрируйтесь пожалуйста.")
        
        # Проверяем пароль
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        stored_password = user.get('password')
        
        if not stored_password:
            return render_template('login.html', error="Пароль не установлен. Зарегистрируйтесь, пожалуйста.")
        
        if password_hash != stored_password:
            log_access(email, "НЕУДАЧНАЯ ПОПЫТКА ВХОДА (неверный пароль)", request.user_agent.string)
            return render_template('login.html', error="Неверный пароль")
        
        # Проверяем бан перед входом
        if is_user_banned(email):
            reason = user['ban_reason'] if user and user['ban_reason'] else 'Не указана'
            log_access(email, "ПОПЫТКА ВХОДА (временный бан)")
            banned_until = datetime.fromisoformat(user['banned_until']) if user and user['banned_until'] else None
            until = banned_until.strftime('%Y-%m-%d %H:%M:%S') if banned_until else 'навсегда'
            return render_template('banned.html', email=email, until=until, reason=reason)
        
        if user['banned'] and not user['banned_until']:
            reason = user['ban_reason'] if user['ban_reason'] else 'Не указана'
            log_access(email, "ПОПЫТКА ВХОДА (постоянный бан)")
            return render_template('banned.html', email=email, until='навсегда', reason=reason)
        
        # Успешный вход
        session['email'] = email
        try:
            update_user(email, verified=True, last_login=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            print(f"Ошибка при обновлении пользователя: {e}")
        log_access(email, "УСПЕШНЫЙ ВХОД")
        return redirect(url_for('index'))
    
    try:
        return render_template('login.html')
    except Exception as e:
        print(f"Ошибка при рендеринге login.html: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Ошибка сервера</h1><p>{str(e)}</p>", 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not email or not password:
            return render_template('register.html', error="Заполните все поля")
        
        if password != confirm_password:
            return render_template('register.html', error="Пароли не совпадают")
        
        if len(password) < 6:
            return render_template('register.html', error="Пароль должен содержать минимум 6 символов")
        
        # Проверяем, существует ли пользователь
        user = get_user(email)
        if user:
            return render_template('register.html', error="Пользователь с таким email уже существует")
        
        # Создаем пользователя с паролем
        try:
            create_user(email, password=password)
        except Exception as e:
            print(f"Ошибка при создании пользователя: {e}")
            return render_template('register.html', error=f"Ошибка при регистрации: {str(e)}")
        
        # Автоматически входим
        session['email'] = email
        try:
            update_user(email, verified=True, last_login=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            print(f"Ошибка при обновлении пользователя: {e}")
        log_access(email, "РЕГИСТРАЦИЯ")
        return redirect(url_for('index'))
    
    try:
        return render_template('register.html')
    except Exception as e:
        print(f"Ошибка при рендеринге register.html: {e}")
        return f"<h1>Ошибка сервера</h1><p>{str(e)}</p>", 500

@app.route('/logout')
def logout():
    email = session.get('email')
    if email:
        log_access(email, "ВЫХОД")
    session.clear()
    return redirect(url_for('login'))

@app.route('/check_rank_change')
def check_rank_change():
    """Проверить, было ли изменение ранга для текущего пользователя"""
    from flask import jsonify
    email = session.get('email')
    if not email:
        return jsonify({'has_change': False}), 200
    
    user_data = get_user(email)
    if not user_data:
        return jsonify({'has_change': False}), 200
    
    # Проверяем, есть ли непросмотренное уведомление об изменении ранга
    if user_data.get('rank_notification_seen') == False and user_data.get('rank_changed_at'):
        old_rank = user_data.get('old_rank')
        new_rank = user_data.get('rank')
        changed_by = user_data.get('rank_changed_by', 'Администратор')
        reason = user_data.get('rank_change_reason', 'Причина не указана')
        changed_at = user_data.get('rank_changed_at', '')
        
        # Определяем, было ли это повышение или понижение
        old_level = get_rank_level(old_rank) if old_rank else 0
        new_level = get_rank_level(new_rank) if new_rank else 0
        
        is_promotion = new_level > old_level
        is_demotion = new_level < old_level
        
        old_rank_display = RANK_NAMES.get(old_rank, 'Без ранга') if old_rank else 'Без ранга'
        new_rank_display = RANK_NAMES.get(new_rank, 'Без ранга') if new_rank else 'Без ранга'
        
        return jsonify({
            'has_change': True,
            'is_promotion': is_promotion,
            'is_demotion': is_demotion,
            'old_rank': old_rank_display,
            'new_rank': new_rank_display,
            'changed_by': changed_by,
            'reason': reason,
            'changed_at': changed_at
        }), 200
    
    return jsonify({'has_change': False}), 200

@app.route('/rank_notification')
def rank_notification():
    """Отобразить уведомление об изменении ранга"""
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    is_promotion = request.args.get('is_promotion') == '1'
    is_demotion = request.args.get('is_demotion') == '1'
    old_rank = request.args.get('old_rank', 'Без ранга')
    new_rank = request.args.get('new_rank', 'Без ранга')
    changed_by = request.args.get('changed_by', 'Администратор')
    reason = request.args.get('reason', 'Причина не указана')
    changed_at = request.args.get('changed_at', '')
    
    return render_template('rank_notification.html', 
                         is_promotion=is_promotion,
                         is_demotion=is_demotion,
                         old_rank=old_rank,
                         new_rank=new_rank,
                         changed_by=changed_by,
                         reason=reason,
                         changed_at=changed_at)

@app.route('/mark_rank_notification_seen', methods=['POST'])
def mark_rank_notification_seen():
    """Отметить уведомление об изменении ранга как просмотренное"""
    email = session.get('email')
    if not email:
        return jsonify({'success': False}), 403
    
    update_user(email, rank_notification_seen=True)
    return jsonify({'success': True}), 200

@app.route('/rules')
def rules():
    """Страница с правилами сайта"""
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('rules.html', lang=current_lang, t=get_translation, user_theme=user_theme)

@app.route('/profile')
def profile():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))

    user_data = get_user(email)
    if not user_data:
        return redirect(url_for('login'))
    
    # Если пользователь в сессии, значит он уже прошел аутентификацию (по паролю или OTP)
    # Разрешаем доступ к профилю независимо от статуса verified
    # verified используется только для первоначальной верификации через OTP

    # Проверка бана
    if is_user_banned(email):
        reason = user_data['ban_reason'] if user_data['ban_reason'] else 'Не указана'
        log_access(email, "ПОПЫТКА ПРОФИЛЯ (временный бан)")
        banned_until = datetime.fromisoformat(user_data['banned_until']) if user_data['banned_until'] else None
        until = banned_until.strftime('%Y-%m-%d %H:%M:%S') if banned_until else 'навсегда'
        return render_template('banned.html', email=email, until=until, reason=reason)

    if user_data['banned'] and not user_data['banned_until']:
        reason = user_data['ban_reason'] if user_data['ban_reason'] else 'Не указана'
        log_access(email, "ПОПЫТКА ПРОФИЛЯ (постоянный бан)")
        return render_template('banned.html', email=email, until='навсегда', reason=reason)

    # Получаем ранг пользователя
    user_rank = get_user_rank(email)
    rank_display = RANK_NAMES.get(user_rank, None) if user_rank else None

    profile_data = {
        'email': email,
        'verified': user_data['verified'],
        'banned': user_data['banned'],
        'banned_until': user_data['banned_until'],
        'ban_reason': user_data['ban_reason'],
        'last_login': user_data['last_login'] or 'Ещё не входил',
        'rank': user_rank,
        'rank_display': rank_display
    }

    # Проверяем, установлен ли пароль
    has_password = bool(user_data.get('password'))
    
    log_access(email, "ОТКРЫЛ ПРОФИЛЬ")
    return render_template('profile.html', profile=profile_data, has_password=has_password)

@app.route('/set_password', methods=['POST'])
def set_password():
    """Установить или изменить пароль"""
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    user_data = get_user(email)
    if not user_data or not user_data['verified']:
        return redirect(url_for('verify'))
    
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    
    if not new_password:
        return redirect(url_for('profile'))
    
    if new_password != confirm_password:
        return redirect(url_for('profile'))
    
    if len(new_password) < 6:
        return redirect(url_for('profile'))
    
    # Хешируем пароль
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    update_user(email, password=password_hash)
    
    log_access(email, "ИЗМЕНИЛ ПАРОЛЬ")
    return redirect(url_for('profile'))

# === АДМИНКА ===
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in admins and admins[username] == password:
            session['admin'] = username
            # Автоматически назначаем ранг админу
            admin_email = f"{username}@admin.local"
            if username == 'VladimirKhudyakov':
                # Создаём или обновляем пользователя с рангом главного админа
                if not get_user(admin_email):
                    create_user(admin_email, rank='главный_админ')
                else:
                    update_user(admin_email, rank='главный_админ')
            elif username == 'VladimirKhudyakov_moderator':
                # Назначаем ранг модератора
                if not get_user(admin_email):
                    create_user(admin_email, rank='модератор')
                else:
                    update_user(admin_email, rank='модератор')
            log_access(f"ADMIN:{username}", "АДМИН ВОШЁЛ")
            return redirect(url_for('admin_panel'))
        else:
            log_access(f"ADMIN:{username}", "ПОПЫТКА ВЗЛОМА", request.user_agent.string)
            return render_template('admin_login.html', error="Неверный логин или пароль")
    return render_template('admin_login.html')

@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    log_access(f"ADMIN:{session['admin']}", "ОТКРЫЛ ПАНЕЛЬ")

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users")
        users_db = [dict(row) for row in cur.fetchall()]

    users_with_status = []
    for user in users_db:
        if user['banned_until']:
            try:
                banned_until_dt = datetime.fromisoformat(user['banned_until'])
                if datetime.now() >= banned_until_dt:
                    update_user(user['email'], banned=False, banned_until=None, ban_reason=None)
                    user['banned'] = False
                    user['banned_until'] = None
                    user['ban_reason'] = None
            except ValueError:
                pass

        users_with_status.append({
            'email': user['email'],
            'banned': user['banned'],
            'banned_until': user['banned_until'],
            'ban_reason': user['ban_reason'],
            'verified': user['verified'],
            'last_login': user['last_login'],
            'rank': user.get('rank')
        })

    # Получаем все посты
    posts = get_all_posts()
    
    # Получаем все объявления
    sales = get_all_sales()
    
    # Получаем все обсуждения
    discussions_list = get_discussions(limit=1000)
    
    # Получаем статистику сайта
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Статистика пользователей
        cur.execute("SELECT COUNT(*) as count FROM users")
        total_users = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM users WHERE verified = 1")
        verified_users = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM users WHERE banned = 1 OR banned_until IS NOT NULL")
        banned_users = cur.fetchone()['count']
        
        # Статистика постов
        cur.execute("SELECT COUNT(*) as count FROM posts")
        total_posts = cur.fetchone()['count']
        
        # Статистика продаж
        cur.execute("SELECT COUNT(*) as count FROM sales")
        total_sales = cur.fetchone()['count']
        
        # Статистика обсуждений
        cur.execute("SELECT COUNT(*) as count FROM discussions")
        total_discussions = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM discussion_replies")
        total_replies = cur.fetchone()['count']
        
        # Статистика комментариев
        cur.execute("SELECT COUNT(*) as count FROM comments")
        total_comments = cur.fetchone()['count']
        
        # Статистика лайков
        cur.execute("SELECT COUNT(*) as count FROM likes")
        total_likes = cur.fetchone()['count']
        
        # Статистика сообщений
        cur.execute("SELECT COUNT(*) as count FROM messages")
        total_messages = cur.fetchone()['count']
        
        # Статистика входов (из логов)
        total_logins = 0
        if os.path.exists("access.log"):
            with open("access.log", "r", encoding="utf-8") as f:
                for line in f:
                    if "УСПЕШНЫЙ ВХОД" in line or "РЕГИСТРАЦИЯ" in line:
                        total_logins += 1
        
        # Статистика регистраций
        total_registrations = total_users
        
        # Статистика за сегодня
        today = datetime.now().strftime("%Y-%m-%d")
        cur.execute("SELECT COUNT(*) as count FROM posts WHERE DATE(created_at) = ?", (today,))
        posts_today = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM users WHERE DATE(last_login) = ?", (today,))
        logins_today = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM sales WHERE DATE(created_at) = ?", (today,))
        sales_today = cur.fetchone()['count']
    
    # Получаем пароли админов (для отображения в админ-панели)
    admins_list = [{'username': username, 'password': password} for username, password in admins.items()]
    
    # Получаем email текущего админа для проверки прав
    admin_username = session.get('admin')
    admin_email = f"{admin_username}@admin.local" if admin_username else None
    admin_rank = get_user_rank(admin_email) if admin_email else None
    
    # Формируем статистику
    stats = {
        'total_users': total_users,
        'verified_users': verified_users,
        'banned_users': banned_users,
        'total_posts': total_posts,
        'total_sales': total_sales,
        'total_discussions': total_discussions,
        'total_replies': total_replies,
        'total_comments': total_comments,
        'total_likes': total_likes,
        'total_messages': total_messages,
        'total_logins': total_logins,
        'total_registrations': total_registrations,
        'posts_today': posts_today,
        'logins_today': logins_today,
        'sales_today': sales_today
    }

    return render_template('admin.html', users=users_with_status, posts=posts, sales=sales, 
                          discussions=discussions_list, admins=admins_list, stats=stats,
                          ranks=RANKS, rank_names=RANK_NAMES, admin_rank=admin_rank, admin_email=admin_email)


@app.route('/admin/ban/<email>', methods=['GET', 'POST'])
def ban_user(email):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        duration = int(request.form['duration'])
        reason = request.form.get('reason', 'Не указана')
        
        banned_until = (datetime.now() + timedelta(minutes=duration)).isoformat()
        update_user(email, banned=True, banned_until=banned_until, ban_reason=reason)
        
        log_action = f"ЗАБАНИЛ на {duration} мин" + (f" ({reason})" if reason != 'Не указана' else "")
        log_access(f"ADMIN:{session['admin']}", log_action, email)
        
        return redirect(url_for('admin_panel'))
    
    return render_template('ban_form.html', email=email)


@app.route('/admin/unban/<email>')
def unban_user(email):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    update_user(email, banned=False, banned_until=None, ban_reason=None)
    log_access(f"ADMIN:{session['admin']}", f"РАЗБАНИЛ {email}")
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_user/<email>', methods=['GET', 'POST'])
def admin_delete_user(email):
    """Удалить пользователя (только для админов)"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    admin_username = session.get('admin')
    admin_email = f"{admin_username}@admin.local"
    admin_rank = get_user_rank(admin_email)
    
    # Получаем данные пользователя для проверки
    user = get_user(email)
    if not user:
        return "<h1>Пользователь не найден</h1>", 404
    
    # Проверяем права: нельзя удалять себя
    if email == admin_email:
        return "<h1>Нельзя удалить свой собственный аккаунт</h1>", 403
    
    # Проверяем права: нельзя удалять пользователей с равным или высшим рангом
    user_rank = user.get('rank')
    if user_rank:
        admin_level = get_rank_level(admin_rank) if admin_rank else 0
        user_level = get_rank_level(user_rank)
        if admin_level <= user_level:
            return "<h1>Недостаточно прав для удаления этого пользователя</h1>", 403
    
    if request.method == 'POST':
        # Подтверждение удаления
        confirm = request.form.get('confirm', '').strip().lower()
        if confirm == 'удалить':
            delete_user(email)
            log_access(f"ADMIN:{admin_username}", f"УДАЛИЛ ПОЛЬЗОВАТЕЛЯ {email}")
            return redirect(url_for('admin_panel'))
        else:
            return render_template('delete_user_confirm.html', email=email, error="Подтверждение неверно. Введите 'удалить' для подтверждения.")
    
    return render_template('delete_user_confirm.html', email=email)


@app.route('/admin/delete_post/<int:post_id>')
def admin_delete_post(post_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    delete_post(post_id)
    log_access(f"ADMIN:{session['admin']}", f"УДАЛИЛ ПОСТ ID {post_id}")
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_sale/<int:sale_id>')
def admin_delete_sale(sale_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    delete_sale(sale_id)
    log_access(f"ADMIN:{session['admin']}", f"УДАЛИЛ ОБЪЯВЛЕНИЕ ID {sale_id}")
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_discussion/<int:discussion_id>')
def admin_delete_discussion(discussion_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    delete_discussion(discussion_id)
    log_access(f"ADMIN:{session['admin']}", f"УДАЛИЛ ОБСУЖДЕНИЕ ID {discussion_id}")
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_discussion/<int:discussion_id>')
def admin_delete_discussion(discussion_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    delete_discussion(discussion_id)
    log_access(f"ADMIN:{session['admin']}", f"УДАЛИЛ ОБСУЖДЕНИЕ ID {discussion_id}")
    return redirect(url_for('admin_panel'))

@app.route('/admin/edit_post/<int:post_id>', methods=['GET', 'POST'])
def admin_edit_post(post_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    post = get_post_by_id(post_id)
    if not post:
        return "<h1>Пост не найден</h1>", 404

    if request.method == 'POST':
        title = request.form['title'].strip()
        image = request.form['image'].strip()

        spec_keys = request.form.getlist('spec_key')
        spec_values = request.form.getlist('spec_value')
        specs = {k: v for k, v in zip(spec_keys, spec_values) if k and v}

        pros = [p.strip() for p in request.form.getlist('pro') if p.strip()]
        cons = [c.strip() for c in request.form.getlist('con') if c.strip()]

        if not title or not image or not specs or not pros:
            return render_template('edit_post.html', post=post, error="Заполните все обязательные поля", admin_mode=True)

        update_post(post_id, title, image, specs, pros, cons)
        log_access(f"ADMIN:{session['admin']}", f"ОБНОВИЛ ПОСТ ID {post_id}")
        return redirect(url_for('admin_panel'))

    return render_template('edit_post.html', post=post, admin_mode=True)

@app.route('/admin/edit_sale/<int:sale_id>', methods=['GET', 'POST'])
def admin_edit_sale(sale_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    sale = get_sale_by_id(sale_id)
    if not sale:
        return "<h1>Объявление не найдено</h1>", 404

    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form.get('description', '').strip()
        image = request.form['image'].strip()
        price = request.form['price'].strip()
        contact = request.form.get('contact', '').strip()
        
        if not title or not image or not price:
            return render_template('edit_sale.html', sale=sale, error="Заполните все обязательные поля", admin_mode=True)
        
        update_sale(sale_id, title, description, image, price, contact)
        log_access(f"ADMIN:{session['admin']}", f"ОБНОВИЛ ОБЪЯВЛЕНИЕ ID {sale_id}")
        return redirect(url_for('admin_panel'))
    
    return render_template('edit_sale.html', sale=sale, admin_mode=True)

@app.route('/admin/set_rank/<email>', methods=['GET', 'POST'])
def admin_set_rank(email):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    admin_username = session.get('admin')
    admin_email = f"{admin_username}@admin.local"
    
    if request.method == 'POST':
        new_rank = request.form.get('rank')
        reason = request.form.get('reason', '').strip() or 'Причина не указана'
        
        if new_rank and new_rank in RANKS:
            # Получаем текущий ранг пользователя
            user = get_user(email)
            old_rank = user.get('rank') if user else None
            
            # Проверяем права: высшая администрация и главный админ могут всё, остальные только нижестоящие ранги
            admin_rank_obj = get_user_rank(admin_email)
            if admin_rank_obj == 'высшая_администрация' or admin_rank_obj == 'вторые_аккаунты' or admin_rank_obj == 'главный_админ' or admin_username == 'VladimirKhudyakov':
                # Высшая администрация, вторые аккаунты и главный админ могут управлять всеми рангами
                # Сохраняем информацию об изменении ранга
                update_user(
                    email, 
                    rank=new_rank,
                    old_rank=old_rank,
                    rank_changed_by=admin_username,
                    rank_change_reason=reason,
                    rank_changed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    rank_notification_seen=False
                )
                log_access(f"ADMIN:{admin_username}", f"ИЗМЕНИЛ РАНГ {email} на {RANK_NAMES[new_rank]} (причина: {reason})")
                return redirect(url_for('admin_panel'))
            elif can_manage_rank(admin_email, new_rank):
                # Остальные могут управлять только рангами ниже своего
                update_user(
                    email, 
                    rank=new_rank,
                    old_rank=old_rank,
                    rank_changed_by=admin_username,
                    rank_change_reason=reason,
                    rank_changed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    rank_notification_seen=False
                )
                log_access(f"ADMIN:{admin_username}", f"ИЗМЕНИЛ РАНГ {email} на {RANK_NAMES[new_rank]} (причина: {reason})")
                return redirect(url_for('admin_panel'))
            else:
                return "<h1>Недостаточно прав для изменения этого ранга</h1>", 403
    
    user = get_user(email)
    current_rank = user.get('rank') if user else None
    return render_template('set_rank.html', email=email, current_rank=current_rank, ranks=RANKS, rank_names=RANK_NAMES)

@app.route('/admin/logout')
def admin_logout():
    admin = session.get('admin')
    if admin:
        log_access(f"ADMIN:{admin}", "АДМИН ВЫШЕЛ")
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


@app.route('/contact_admin', methods=['POST'])
def contact_admin():
    email = request.form.get('email')
    if email:
        log_access(email, "ХОЧЕТ СВЯЗАТЬСЯ С АДМИНОМ", request.user_agent.string)
    return redirect(url_for('login'))

@app.route('/about')
def about():
    """Страница 'О нас'"""
    return render_template('about.html')

@app.route('/career', methods=['GET', 'POST'])
def career():
    """Страница 'Карьера' с формой заявки"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        full_name = request.form.get('full_name', '').strip()
        bio = request.form.get('bio', '').strip()
        
        if not email or not phone or not full_name or not bio:
            return render_template('career.html', error="Заполните все поля")
        
        # Сохраняем заявку в базу данных
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""
                INSERT INTO career_applications (email, phone, full_name, bio, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (email, phone, full_name, bio, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        log_access(email if email else "GUEST", "ПОДАЛ ЗАЯВКУ НА КАРЬЕРУ")
        return render_template('career.html', success=True)
    
    return render_template('career.html')

@app.route('/terms_of_service')
def terms_of_service():
    """Страница 'Условия использования'"""
    return render_template('terms_of_service.html')

@app.route('/privacy_policy')
def privacy_policy():
    """Страница 'Политика конфиденциальности'"""
    return render_template('privacy_policy.html')

@app.route('/cookie_policy')
def cookie_policy():
    """Страница 'Политика использования файлов cookie'"""
    return render_template('cookie_policy.html')

# === ПРОДАЖА АВТОМОБИЛЕЙ ===
@app.route('/sales')
def sales():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if is_user_banned(email):
        return redirect(url_for('index'))
    
    sales_list = get_all_sales()
    log_access(email, "ОТКРЫЛ РАЗДЕЛ ПРОДАЖ")
    return render_template('sales.html', sales=sales_list)

@app.route('/create_sale', methods=['GET', 'POST'])
def create_sale_route():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if is_user_banned(email):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form.get('description', '').strip()
        image = request.form['image'].strip()
        price = request.form['price'].strip()
        contact = request.form.get('contact', '').strip()
        
        if not title or not image or not price:
            return render_template('create_sale.html', error="Заполните все обязательные поля")
        
        author = email.split('@')[0].title()
        create_sale(title, description, image, price, author, contact)
        log_access(email, "СОЗДАЛ ОБЪЯВЛЕНИЕ", title)
        return redirect(url_for('sales'))
    
    return render_template('create_sale.html')

@app.route('/sale/<int:sale_id>')
def view_sale(sale_id):
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if is_user_banned(email):
        return redirect(url_for('index'))
    
    sale = get_sale_by_id(sale_id)
    if not sale:
        return "<h1>Объявление не найдено</h1>", 404
    
    reviews = get_sale_reviews(sale_id)
    log_access(email, "ОТКРЫЛ ОБЪЯВЛЕНИЕ", f"ID {sale_id}")
    return render_template('sale.html', sale=sale, reviews=reviews)

@app.route('/add_sale_review/<int:sale_id>', methods=['POST'])
def add_sale_review_route(sale_id):
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    text = request.form['text'].strip()
    rating = int(request.form.get('rating', 5))
    
    if not text:
        return redirect(url_for('view_sale', sale_id=sale_id))
    
    author = email.split('@')[0].title()
    add_sale_review(sale_id, author, text, rating)
    log_access(email, "ОТЗЫВ НА ОБЪЯВЛЕНИЕ", f"ID {sale_id}")
    return redirect(url_for('view_sale', sale_id=sale_id))

# === СРАВНЕНИЕ АВТОМОБИЛЕЙ ===
@app.route('/compare')
def compare_posts():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if is_user_banned(email):
        return redirect(url_for('index'))
    
    post1_id = request.args.get('post1')
    post2_id = request.args.get('post2')
    
    if not post1_id or not post2_id:
        return render_template('compare.html', error="Выберите два поста для сравнения", posts=get_all_posts())
    
    post1 = get_post_by_id(int(post1_id))
    post2 = get_post_by_id(int(post2_id))
    
    if not post1 or not post2:
        return render_template('compare.html', error="Один из постов не найден", posts=get_all_posts())
    
    log_access(email, "СРАВНЕНИЕ", f"посты {post1_id} и {post2_id}")
    return render_template('compare.html', post1=post1, post2=post2, posts=get_all_posts())

# === ИЗБРАННОЕ ===
@app.route('/favorites')
def favorites():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if is_user_banned(email):
        return redirect(url_for('index'))
    
    favorites_list = get_favorites(email)
    
    # Добавляем информацию о лайках
    for post in favorites_list:
        post['liked'] = has_liked(post['id'], email)
        post['favorited'] = True
        post['likes'] = get_like_count(post['id'])
        post['comments_count'] = len(get_comments_by_post_id(post['id']))
    
    log_access(email, "ОТКРЫЛ ИЗБРАННОЕ")
    return render_template('favorites.html', posts=favorites_list)

@app.route('/toggle_favorite/<int:post_id>', methods=['POST'])
def toggle_favorite(post_id):
    email = session.get('email')
    if not email:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 403
    
    if is_favorite(email, post_id):
        remove_from_favorites(email, post_id)
        action = 'removed'
    else:
        add_to_favorites(email, post_id)
        action = 'added'
    
    log_access(email, f"{'ДОБАВИЛ' if action == 'added' else 'УДАЛИЛ'} ИЗ ИЗБРАННОГО", f"пост {post_id}")
    return jsonify({'success': True, 'action': action})

# === ПОДПИСКИ ===
@app.route('/toggle_subscription/<author_email>', methods=['POST'])
def toggle_subscription(author_email):
    email = session.get('email')
    if not email:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 403
    
    if is_subscribed(email, author_email):
        unsubscribe_from_author(email, author_email)
        action = 'unsubscribed'
    else:
        subscribe_to_author(email, author_email)
        action = 'subscribed'
        # Отправляем уведомление автору, на которого подписались
        # Не отправляем уведомление, если подписывается сам на себя
        if author_email != email:
            subscriber_name = email.split('@')[0].title()
            create_notification(
                author_email,
                'subscription',
                f'{subscriber_name} подписался на вас',
                post_id=None,
                author_email=email
            )
    
    log_access(email, f"{'ПОДПИСАЛСЯ' if action == 'subscribed' else 'ОТПИСАЛСЯ'}", f"на {author_email}")
    return jsonify({'success': True, 'action': action})

@app.route('/subscriptions')
def subscriptions():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if is_user_banned(email):
        return redirect(url_for('index'))
    
    subscribed_authors = get_subscriptions(email)
    # Получаем посты от подписок
    all_posts = get_all_posts()
    subscribed_posts = [p for p in all_posts if (p['author'].lower() + '@example.com') in subscribed_authors]
    
    for post in subscribed_posts:
        post['liked'] = has_liked(post['id'], email)
        post['favorited'] = is_favorite(email, post['id'])
        post['likes'] = get_like_count(post['id'])
        post['comments_count'] = len(get_comments_by_post_id(post['id']))
    
    log_access(email, "ОТКРЫЛ ПОДПИСКИ")
    return render_template('subscriptions.html', posts=subscribed_posts, subscribed_authors=subscribed_authors)

# === УВЕДОМЛЕНИЯ ===
@app.route('/notifications')
def notifications():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if is_user_banned(email):
        return redirect(url_for('index'))
    
    notifications_list = get_notifications(email)
    log_access(email, "ОТКРЫЛ УВЕДОМЛЕНИЯ")
    return render_template('notifications.html', notifications=notifications_list)

@app.route('/notifications/mark_seen/<int:notification_id>', methods=['POST'])
def mark_notification_seen_route(notification_id):
    email = session.get('email')
    if not email:
        return jsonify({'success': False}), 403
    
    mark_notification_seen(notification_id)
    return jsonify({'success': True})

@app.route('/notifications/mark_all_seen', methods=['POST'])
def mark_all_notifications_seen_route():
    email = session.get('email')
    if not email:
        return jsonify({'success': False}), 403
    
    mark_all_notifications_seen(email)
    return jsonify({'success': True})

@app.route('/notifications/count')
def notifications_count():
    email = session.get('email')
    if not email:
        return jsonify({'count': 0})
    
    count = get_unread_notifications_count(email)
    return jsonify({'count': count})

# === ЖАЛОБЫ ===
@app.route('/report', methods=['POST'])
def report():
    email = session.get('email')
    if not email:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 403
    
    target_type = request.form.get('target_type')  # 'post' или 'comment'
    target_id = int(request.form.get('target_id'))
    reason = request.form.get('reason', '').strip()
    
    if not target_type or not target_id:
        return jsonify({'success': False, 'error': 'Неверные параметры'}), 400
    
    create_report(email, target_type, target_id, reason)
    log_access(email, "ПОДАЛ ЖАЛОБУ", f"{target_type} {target_id}")
    return jsonify({'success': True, 'message': 'Жалоба отправлена модераторам'})

# === ОБНОВЛЕНИЕ ПРОСМОТРА ПОСТА ===
@app.route('/post/<int:post_id>')
def view_post(post_id):
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))

    if is_user_banned(email):
        return redirect(url_for('index'))

    # Добавляем просмотр
    add_post_view(post_id, email)

    post = get_post_by_id(post_id)
    if not post:
        return "<h1>Пост не найден</h1>", 404

    # Добавляем информацию о лайках и избранном
    post['liked'] = has_liked(post_id, email)
    post['favorited'] = is_favorite(email, post_id)
    post['likes'] = get_like_count(post_id)
    
    # Проверяем подписку на автора
    author_email = post['author'].lower() + '@example.com'
    post['subscribed'] = is_subscribed(email, author_email)

    comments = get_comments_by_post_id(post_id)
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    log_access(email, "ОТКРЫЛ ПОСТ", f"ID {post_id}")
    return render_template('post.html', post=post, comments=comments, lang=current_lang, 
                         t=get_translation, user_theme=user_theme)

# === ЗАПУСК ПРИЛОЖЕНИЯ ===
#if __name__ == '__main__':
 #init_db()  # Создаём БД при старте
#app.run(debug=True, host='127.0.0.1', port=5000)

# === PWA МАРШРУТЫ ===
@app.route('/manifest.json')
def manifest():
    try:
        return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')
    except Exception as e:
        print(f"Error loading manifest.json: {e}")
        return jsonify({'error': 'Manifest not found'}), 404

@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory('static', 'favicon.ico', mimetype='image/x-icon')
    except Exception as e:
        print(f"Error loading favicon.ico: {e}")
        try:
            # Если favicon.ico не найден, используем PNG иконку
            return send_from_directory('static', 'icon-192x192.png', mimetype='image/png')
        except:
            return '', 204  # No Content

@app.route('/sw.js')
def service_worker():
    try:
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')
    except Exception as e:
        print(f"Error loading sw.js: {e}")
        return '', 204  # No Content

# === ПЕРЕКЛЮЧЕНИЕ ТЕМЫ ===
@app.route('/set_theme/<theme>', methods=['POST'])
def set_theme(theme):
    email = session.get('email')
    if email and theme in ['light', 'dark']:
        set_user_theme(email, theme)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

# === ПОПУЛЯРНЫЕ ПОСТЫ ===
@app.route('/popular_posts')
def popular_posts():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    sort_by = request.args.get('sort', 'views')
    posts = get_popular_posts(limit=20, sort_by=sort_by)
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('popular_posts.html', posts=posts, sort_by=sort_by, 
                         lang=current_lang, t=get_translation, user_theme=user_theme)

# === ИСТОРИЯ ПРОСМОТРОВ ===
@app.route('/view_history')
def view_history():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    history = get_view_history(email)
    recommendations = get_recommendations(email)
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('view_history.html', history=history, recommendations=recommendations,
                         lang=current_lang, t=get_translation, user_theme=user_theme)

# === ОБСУЖДЕНИЯ ===
@app.route('/discussions')
def discussions():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    category = request.args.get('category')
    discussions_list = get_discussions(category=category)
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('discussions.html', discussions=discussions_list, category=category,
                         lang=current_lang, t=get_translation, user_theme=user_theme)

@app.route('/discussion/<int:discussion_id>')
def discussion_detail(discussion_id):
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    discussion = get_discussion_by_id(discussion_id)
    if not discussion:
        return redirect(url_for('discussions'))
    
    replies = get_discussion_replies(discussion_id)
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('discussion_detail.html', discussion=discussion, replies=replies,
                         lang=current_lang, t=get_translation, user_theme=user_theme)

@app.route('/create_discussion', methods=['GET', 'POST'])
def create_discussion_route():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        
        if title and content:
            discussion_id = create_discussion(title, content, email, category)
            return redirect(url_for('discussion_detail', discussion_id=discussion_id))
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('create_discussion.html', lang=current_lang, t=get_translation, user_theme=user_theme)

@app.route('/add_discussion_reply/<int:discussion_id>', methods=['POST'])
def add_discussion_reply_route(discussion_id):
    email = session.get('email')
    if not email:
        return jsonify({'success': False}), 403
    
    content = request.form.get('content')
    if content:
        add_discussion_reply(discussion_id, email, content)
        return redirect(url_for('discussion_detail', discussion_id=discussion_id))
    
    return redirect(url_for('discussions'))

# === ЛИЧНЫЕ СООБЩЕНИЯ ===
@app.route('/messages')
def messages():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    folder = request.args.get('folder', 'inbox')
    messages_list = get_messages(email, folder)
    unread_count = get_unread_messages_count(email)
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('messages.html', messages=messages_list, folder=folder, 
                         unread_count=unread_count, lang=current_lang, t=get_translation, user_theme=user_theme)

@app.route('/send_message', methods=['GET', 'POST'])
def send_message_route():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            recipient_email = request.form.get('recipient_email', '').strip()
            subject = request.form.get('subject', '').strip()
            content = request.form.get('content', '').strip()
            
            if not recipient_email:
                return render_template('send_message.html', 
                                     error='Введите email получателя',
                                     recipient=recipient_email,
                                     lang=session.get('language', 'ru'),
                                     t=get_translation,
                                     user_theme=get_user_theme(email))
            
            if not content:
                return render_template('send_message.html', 
                                     error='Введите текст сообщения',
                                     recipient=recipient_email,
                                     lang=session.get('language', 'ru'),
                                     t=get_translation,
                                     user_theme=get_user_theme(email))
            
            # Проверяем, существует ли получатель
            recipient = get_user(recipient_email)
            if not recipient:
                return render_template('send_message.html', 
                                     error='Пользователь с таким email не найден',
                                     recipient=recipient_email,
                                     lang=session.get('language', 'ru'),
                                     t=get_translation,
                                     user_theme=get_user_theme(email))
            
            # Отправляем сообщение
            try:
                send_message(email, recipient_email, subject, content)
                return redirect(url_for('messages', folder='sent'))
            except Exception as send_error:
                print(f"Ошибка при отправке сообщения: {send_error}")
                import traceback
                traceback.print_exc()
                return render_template('send_message.html', 
                                     error=f'Ошибка при отправке сообщения: {str(send_error)}',
                                     recipient=recipient_email,
                                     lang=session.get('language', 'ru'),
                                     t=get_translation,
                                     user_theme=get_user_theme(email))
            
        except Exception as e:
            print(f"Ошибка при обработке формы: {e}")
            import traceback
            traceback.print_exc()
            return render_template('send_message.html', 
                                 error=f'Ошибка при обработке запроса: {str(e)}',
                                 recipient=request.form.get('recipient_email', ''),
                                 lang=session.get('language', 'ru'),
                                 t=get_translation,
                                 user_theme=get_user_theme(email))
    
    recipient = request.args.get('recipient')
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('send_message.html', recipient=recipient, lang=current_lang, 
                         t=get_translation, user_theme=user_theme)

@app.route('/message/<int:message_id>')
def view_message(message_id):
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        row = cur.fetchone()
        message = dict(row) if row else None
    
    if not message or (message['recipient_email'] != email and message['sender_email'] != email):
        return redirect(url_for('messages'))
    
    if message['recipient_email'] == email:
        mark_message_read(message_id, email)
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('view_message.html', message=message, lang=current_lang, 
                         t=get_translation, user_theme=user_theme)

# === РАСШИРЕННЫЙ ПОИСК ===
@app.route('/advanced_search', methods=['GET', 'POST'])
def advanced_search():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Сохраняем поиск
        search_name = request.form.get('search_name')
        if search_name:
            search_params = {
                'price_min': request.form.get('price_min'),
                'price_max': request.form.get('price_max'),
                'year_min': request.form.get('year_min'),
                'year_max': request.form.get('year_max'),
                'power_min': request.form.get('power_min'),
                'power_max': request.form.get('power_max'),
                'fuel_max': request.form.get('fuel_max'),
                'category': request.form.get('category')
            }
            save_search(email, search_name, search_params)
    
    # Выполняем поиск
    price_min = request.args.get('price_min') or request.form.get('price_min')
    price_max = request.args.get('price_max') or request.form.get('price_max')
    year_min = request.args.get('year_min') or request.form.get('year_min')
    year_max = request.args.get('year_max') or request.form.get('year_max')
    power_min = request.args.get('power_min') or request.form.get('power_min')
    power_max = request.args.get('power_max') or request.form.get('power_max')
    fuel_max = request.args.get('fuel_max') or request.form.get('fuel_max')
    category = request.args.get('category') or request.form.get('category')
    
    posts = get_all_posts(category_filter=category)
    
    # Фильтруем по параметрам
    filtered_posts = []
    for post in posts:
        # Здесь нужно добавить поля price, year, power, fuel_consumption в посты
        # Пока просто возвращаем все посты
        filtered_posts.append(post)
    
    saved_searches = get_saved_searches(email)
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('advanced_search.html', posts=filtered_posts, saved_searches=saved_searches,
                         price_min=price_min, price_max=price_max, year_min=year_min, year_max=year_max,
                         power_min=power_min, power_max=power_max, fuel_max=fuel_max, category=category,
                         categories=CATEGORIES, lang=current_lang, t=get_translation, user_theme=user_theme)

# === СТАТИСТИКА ===
@app.route('/statistics')
def statistics():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    # Проверяем права администратора
    user = get_user(email)
    if not user or user.get('rank') not in ['admin', 'moderator']:
        return redirect(url_for('index'))
    
    top_authors = get_top_authors(10)
    popular = get_popular_posts(10)
    
    # Статистика по дням (последние 30 дней)
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM posts
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        daily_stats = [dict(row) for row in cur.fetchall()]
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('statistics.html', top_authors=top_authors, popular=popular, 
                         daily_stats=daily_stats, lang=current_lang, t=get_translation, user_theme=user_theme)

@app.route('/admin/reports')
def monthly_reports():
    """Просмотр ежемесячных отчетов"""
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    # Проверяем права администратора
    user = get_user(email)
    if not user or user.get('rank') not in ['admin', 'moderator']:
        return redirect(url_for('index'))
    
    reports = get_monthly_reports(24)  # Последние 24 месяца
    
    current_lang = session.get('language', 'ru')
    user_theme = get_user_theme(email)
    
    return render_template('monthly_reports.html', reports=reports, 
                         lang=current_lang, t=get_translation, user_theme=user_theme)

@app.route('/admin/generate_report', methods=['POST'])
def generate_report_manual():
    """Ручная генерация отчета (для тестирования)"""
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))
    
    # Проверяем права администратора
    user = get_user(email)
    if not user or user.get('rank') not in ['admin', 'moderator']:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    month = request.form.get('month', type=int)
    year = request.form.get('year', type=int)
    
    report_data = generate_monthly_report(month, year)
    if save_monthly_report(report_data):
        return jsonify({'success': True, 'message': 'Отчет успешно создан'})
    else:
        return jsonify({'error': 'Ошибка при создании отчета'}), 500

# === ПЕРЕКЛЮЧЕНИЕ ЯЗЫКА ===
@app.route('/set_language/<lang>')
def set_language(lang):
    """Установить язык интерфейса"""
    if lang in ['ru', 'en']:
        session['language'] = lang
    return redirect(request.referrer or url_for('index'))

# === ОТКЛЮЧЕНИЕ КЕШИРОВАНИЯ ДЛЯ HTML ===
@app.after_request
def add_no_cache_headers(response):
    """Добавляет заголовки для предотвращения кеширования HTML страниц"""
    # Для HTML страниц отключаем кеширование
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        # Добавляем версию для предотвращения кеширования
        response.headers['ETag'] = str(time.time())
    # Для статических файлов (CSS, JS, изображения) разрешаем кеширование, но с версионированием
    elif response.content_type and any(x in response.content_type for x in ['text/css', 'application/javascript', 'image/', 'font/']):
        # Кешируем на 1 день, но с проверкой обновлений
        response.headers['Cache-Control'] = 'public, max-age=86400, must-revalidate'
    return response

# === ОБРАБОТКА ОШИБОК 404 ===
@app.errorhandler(404)
def not_found(error):
    """Обработка 404 ошибок"""
    print(f"404 Error: {request.url}")
    if request.path.startswith('/static/'):
        # Для статических файлов возвращаем пустой ответ
        return '', 204
    # Для других маршрутов перенаправляем на главную
    return redirect(url_for('index'))

def schedule_monthly_reports():
    """Планировщик для автоматической генерации отчетов каждый месяц"""
    last_check = None
    
    def check_and_generate():
        nonlocal last_check
        while True:
            try:
                now = datetime.now()
                # Проверяем в первый день месяца в 00:00
                # Используем last_check чтобы не генерировать отчет несколько раз
                if (now.day == 1 and now.hour == 0 and 
                    (last_check is None or last_check.day != 1 or last_check.month != now.month)):
                    print(f"[{now}] Генерация месячного отчета...")
                    report_data = generate_monthly_report()
                    if save_monthly_report(report_data):
                        print(f"[{now}] Отчет за {report_data['report_month']} {report_data['year']} успешно создан")
                    else:
                        print(f"[{now}] Ошибка при создании отчета")
                    last_check = now
                time.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                print(f"Ошибка в планировщике отчетов: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(3600)  # При ошибке ждем час
    
    thread = threading.Thread(target=check_and_generate, daemon=True)
    thread.start()
    print("Планировщик ежемесячных отчетов запущен")

if __name__ == '__main__':
    try:
        init_db()  # Создаём БД при старте
        schedule_monthly_reports()  # Запускаем планировщик отчетов
        app.run(debug=False, host='0.0.0.0', port=8000)
    except Exception as e:
        print(f"Ошибка при запуске приложения: {e}")
        raise