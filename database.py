import sqlite3
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name="psycho_bot.db"):
        self.db_name = db_name
        self.conn = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info("Подключение к базе данных установлено")
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subscription_status TEXT DEFAULT 'free',
                subscription_expires_at TIMESTAMP
            )
        """)
        
        # Таблица для учёта дневных лимитов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                messages_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица дневника
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                entry TEXT NOT NULL,
                mood TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица статистики
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                meditations_count INTEGER DEFAULT 0,
                exercises_count INTEGER DEFAULT 0,
                ai_messages_count INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица истории ИИ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица настроек пользователя (для уведомлений)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                morning_enabled INTEGER DEFAULT 1,
                midday_enabled INTEGER DEFAULT 1,
                evening_enabled INTEGER DEFAULT 1,
                reminder_enabled INTEGER DEFAULT 1,
                timezone TEXT DEFAULT 'Europe/Moscow',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        self.conn.commit()
        logger.info("Все таблицы созданы")
    
    # ===== Пользователи =====
    def add_user(self, user_id, username=None, first_name=None, last_name=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, last_name))
        
        if cursor.rowcount > 0:
            cursor.execute("""
                INSERT OR IGNORE INTO stats (user_id, meditations_count, exercises_count, ai_messages_count, total_messages)
                VALUES (?, 0, 0, 0, 0)
            """, (user_id,))
            # Создаём настройки по умолчанию
            cursor.execute("""
                INSERT OR IGNORE INTO user_settings (user_id, morning_enabled, midday_enabled, evening_enabled, reminder_enabled)
                VALUES (?, 1, 1, 1, 1)
            """, (user_id,))
        
        self.conn.commit()
    
    def update_last_active(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users SET last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        self.conn.commit()
    
    def get_user_subscription(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT subscription_status, subscription_expires_at FROM users
            WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()
    
    def set_subscription(self, user_id, status, expires_at=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET subscription_status = ?, subscription_expires_at = ?
            WHERE user_id = ?
        """, (status, expires_at, user_id))
        self.conn.commit()
    
    # ===== Дневное использование (лимиты) =====
    def get_daily_usage(self, user_id):
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT messages_count FROM daily_usage
            WHERE user_id = ? AND date = ?
        """, (user_id, today))
        row = cursor.fetchone()
        return row['messages_count'] if row else 0
    
    def increment_daily_usage(self, user_id):
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO daily_usage (user_id, date, messages_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, date) DO UPDATE SET
            messages_count = messages_count + 1
        """, (user_id, today))
        self.conn.commit()
    
    # ===== Проверка лимита =====
    def can_send_message(self, user_id):
        sub = self.get_user_subscription(user_id)
        if not sub:
            return True
        status = sub['subscription_status']
        if status == 'premium':
            return True
        daily_messages = self.get_daily_usage(user_id)
        FREE_LIMIT = 20
        return daily_messages < FREE_LIMIT
    
    def get_remaining_messages(self, user_id):
        sub = self.get_user_subscription(user_id)
        if sub and sub['subscription_status'] == 'premium':
            return -1
        daily_messages = self.get_daily_usage(user_id)
        FREE_LIMIT = 20
        remaining = FREE_LIMIT - daily_messages
        return remaining if remaining > 0 else 0
    
    # ===== Дневник =====
    def add_diary_entry(self, user_id, entry, mood=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO diary_entries (user_id, entry, mood)
            VALUES (?, ?, ?)
        """, (user_id, entry, mood))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_diary_entries(self, user_id, limit=10):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM diary_entries
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        return cursor.fetchall()
    
    # ===== Статистика =====
    def increment_stat(self, user_id, stat_name):
        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE stats SET {stat_name} = {stat_name} + 1
            WHERE user_id = ?
        """, (user_id,))
        self.conn.commit()
    
    def get_stats(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM stats WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()
    
    # ===== История ИИ =====
    def add_ai_message(self, user_id, role, message):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ai_history (user_id, role, message)
            VALUES (?, ?, ?)
        """, (user_id, role, message))
        self.conn.commit()
    
    def get_ai_history(self, user_id, limit=10):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT role, message FROM ai_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        return list(reversed(cursor.fetchall()))
    
    # ===== Настройки пользователя (для уведомлений) =====
    def get_user_settings(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT morning_enabled, midday_enabled, evening_enabled, reminder_enabled, timezone
            FROM user_settings
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("""
                INSERT INTO user_settings (user_id, morning_enabled, midday_enabled, evening_enabled, reminder_enabled, timezone)
                VALUES (?, 1, 1, 1, 1, 'Europe/Moscow')
            """, (user_id,))
            self.conn.commit()
            return {'morning_enabled': 1, 'midday_enabled': 1, 'evening_enabled': 1, 'reminder_enabled': 1, 'timezone': 'Europe/Moscow'}
        
        return dict(row)
    
    def update_user_settings(self, user_id, **kwargs):
        cursor = self.conn.cursor()
        for key, value in kwargs.items():
            cursor.execute(f"""
                UPDATE user_settings SET {key} = ? WHERE user_id = ?
            """, (value, user_id))
        self.conn.commit()
    
    # ===== Получение всех пользователей =====
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return cursor.fetchall()
    
    # ===== Закрытие =====
    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Подключение к базе данных закрыто")
