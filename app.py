from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
import string
from datetime import datetime, timedelta
import os
import sqlite3
import hashlib

app = Flask(__name__)
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
        conn.execute("""
            INSERT INTO users (email, verified, banned, banned_until, ban_reason, last_login, rank, 
                              rank_changed_by, rank_change_reason, rank_changed_at, old_rank, rank_notification_seen, password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (email, False, False, None, None, None, rank, None, None, None, None, True, password_hash))

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

def create_post(title, image, specs, pros, cons, author, category=None, images=None, tags=None):
    specs_str = '|'.join([f"{k}:{v}" for k, v in specs.items()])
    pros_str = '|'.join(pros)
    cons_str = '|'.join(cons)
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO posts (title, image, specs, pros, cons, author, created_at, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, image, specs_str, pros_str, cons_str, author, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), category))
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
                'tags': tags
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
            'tags': tags
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
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO notifications (user_email, type, message, post_id, author_email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_email, notification_type, message, post_id, author_email, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

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

def mark_all_notifications_seen(user_email):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE notifications SET seen = 1 WHERE user_email = ?", (user_email,))

def get_unread_notifications_count(user_email):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM notifications WHERE user_email = ? AND seen = 0", (user_email,))
        return cur.fetchone()[0]

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

    return render_template('index.html', car=car_data, cars=cars, selected=selected_car, posts=posts, 
                         search_query=search_query, staff_list=staff_list, all_tags=all_tags, 
                         categories=CATEGORIES, tag_filter=tag_filter, category_filter=category_filter,
                         unread_notifications=unread_count)

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

        author = email.split('@')[0].title()
        post_id = create_post(title, image, specs, pros, cons, author, category, additional_images, tags)
        
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
        login_method = request.form.get('login_method', 'otp')  # 'otp' или 'password'
        password = request.form.get('password', '')
        
        user = get_user(email)
        
        # Если пользователь не существует, создаем его
        if not user:
            create_user(email)
            user = get_user(email)
        
        # Если выбран вход по паролю
        if login_method == 'password':
            if not password:
                return render_template('login.html', error="Введите пароль")
            
            # Проверяем пароль
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            stored_password = user.get('password') if user else None
            
            if not stored_password:
                return render_template('login.html', error="Пароль не установлен. Используйте вход по OTP или установите пароль в профиле.")
            
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
            
            # Успешный вход по паролю
            session['email'] = email
            update_user(email, verified=True, last_login=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            log_access(email, "УСПЕШНЫЙ ВХОД (по паролю)")
            return redirect(url_for('index'))
        
        # Вход по OTP (старый способ)
        else:
            session['email'] = email
            session['otp'] = generate_otp()
            log_access(email, "НАЧАЛО ВХОДА (OTP)")
            return redirect(url_for('verify'))
    
    return render_template('login.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    email = session.get('email')
    if not email:
        return redirect(url_for('login'))

    user_data = get_user(email)

    # Проверяем временный бан
    if is_user_banned(email):
        reason = user_data['ban_reason'] if user_data and user_data['ban_reason'] else 'Не указана'
        log_access(email, "ПОПЫТКА ВХОДА (временный бан)")
        banned_until = datetime.fromisoformat(user_data['banned_until']) if user_data['banned_until'] else None
        until = banned_until.strftime('%H:%M:%S') if banned_until else 'навсегда'
        return render_template('banned.html', email=email, until=until, reason=reason)

    # Постоянный бан
    if user_data and user_data['banned'] and not user_data['banned_until']:
        reason = user_data['ban_reason'] if user_data['ban_reason'] else 'Не указана'
        log_access(email, "ПОПЫТКА ВХОДА (постоянный бан)")
        return render_template('banned.html', email=email, until='навсегда', reason=reason)

    # Обработка POST — ввод кода
    if request.method == 'POST':
        entered_otp = request.form['otp']
        if entered_otp == session.get('otp'):
            update_user(email, verified=True, last_login=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            log_access(email, "УСПЕШНЫЙ ВХОД")
            return redirect(url_for('index'))
        else:
            log_access(email, "ПОПЫТКА ВЗЛОМА", request.user_agent.string)
            return render_template('verify.html', error="Неверный код. Проверь терминал.", email=email)

    # Любой другой случай — показываем форму
    return render_template('verify.html', email=email, error=None)

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
    
    # Получаем пароли админов (для отображения в админ-панели)
    admins_list = [{'username': username, 'password': password} for username, password in admins.items()]
    
    # Получаем email текущего админа для проверки прав
    admin_username = session.get('admin')
    admin_email = f"{admin_username}@admin.local" if admin_username else None
    admin_rank = get_user_rank(admin_email) if admin_email else None

    return render_template('admin.html', users=users_with_status, posts=posts, sales=sales, admins=admins_list, 
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
    log_access(email, "ОТКРЫЛ ПОСТ", f"ID {post_id}")
    return render_template('post.html', post=post, comments=comments)

# === ЗАПУСК ПРИЛОЖЕНИЯ ===
if __name__ == '__main__':
    init_db()  # Создаём БД при старте
    app.run(debug=True, host='127.0.0.1', port=5000)




