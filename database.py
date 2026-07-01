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
        
        # Таблица пользователей (добавляем subscription_status)
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
        
        self.conn.commit()
    
    def update_last_active(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users SET last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        self.conn.commit()
    
    def get_user_subscription(self, user_id):
        """Получает статус подписки пользователя"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT subscription_status, subscription_expires_at FROM users
            WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()
    
    def set_subscription(self, user_id, status, expires_at=None):
        """Устанавливает статус подписки"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET subscription_status = ?, subscription_expires_at = ?
            WHERE user_id = ?
        """, (status, expires_at, user_id))
        self.conn.commit()
    
    # ===== Дневное использование (лимиты) =====
    def get_daily_usage(self, user_id):
        """Получает количество сообщений пользователя за сегодня"""
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT messages_count FROM daily_usage
            WHERE user_id = ? AND date = ?
        """, (user_id, today))
        row = cursor.fetchone()
        return row['messages_count'] if row else 0
    
    def increment_daily_usage(self, user_id):
        """Увеличивает счётчик сообщений за сегодня"""
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
        """Проверяет, может ли пользователь отправить сообщение"""
        # Получаем статус подписки
        sub = self.get_user_subscription(user_id)
        if not sub:
            return True  # Если пользователя нет в БД — разрешаем
        
        status = sub['subscription_status']
        
        # Премиум-пользователи без ограничений
        if status == 'premium':
            return True
        
        # Бесплатные пользователи — проверяем лимит
        daily_messages = self.get_daily_usage(user_id)
        FREE_LIMIT = 20  # 20 сообщений в день
        
        return daily_messages < FREE_LIMIT
    
    def get_remaining_messages(self, user_id):
        """Возвращает оставшееся количество сообщений на сегодня"""
        sub = self.get_user_subscription(user_id)
        if sub and sub['subscription_status'] == 'premium':
            return -1  # Бесконечность
        
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
    
    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Подключение к базе данных закрыто")
