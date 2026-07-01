import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name="psycho_bot.db"):
        """Инициализация базы данных"""
        self.db_name = db_name
        self.conn = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Подключение к базе данных"""
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info("Подключение к базе данных установлено")
    
    def create_tables(self):
        """Создание всех необходимых таблиц"""
        cursor = self.conn.cursor()
        
        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # Таблица статистики (общая)
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
        
        # Таблица диалогов с ИИ
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
    
    # ===== Функции для пользователей =====
    def add_user(self, user_id, username=None, first_name=None, last_name=None):
        """Добавление нового пользователя или обновление существующего"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, last_name))
        
        # Если пользователь новый, создаем для него статистику
        if cursor.rowcount > 0:
            cursor.execute("""
                INSERT OR IGNORE INTO stats (user_id, meditations_count, exercises_count, ai_messages_count, total_messages)
                VALUES (?, 0, 0, 0, 0)
            """, (user_id,))
        
        self.conn.commit()
    
    def update_last_active(self, user_id):
        """Обновление времени последней активности"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users SET last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        self.conn.commit()
    
    # ===== Функции для дневника =====
    def add_diary_entry(self, user_id, entry, mood=None):
        """Добавление записи в дневник"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO diary_entries (user_id, entry, mood)
            VALUES (?, ?, ?)
        """, (user_id, entry, mood))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_diary_entries(self, user_id, limit=10):
        """Получение последних записей из дневника"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM diary_entries
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        return cursor.fetchall()
    
    # ===== Функции для статистики =====
    def increment_stat(self, user_id, stat_name):
        """Увеличение статистики (meditations_count, exercises_count, ai_messages_count, total_messages)"""
        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE stats SET {stat_name} = {stat_name} + 1
            WHERE user_id = ?
        """, (user_id,))
        self.conn.commit()
    
    def get_stats(self, user_id):
        """Получение статистики пользователя"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM stats WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()
    
    # ===== Функции для истории ИИ =====
    def add_ai_message(self, user_id, role, message):
        """Сохранение сообщения в историю ИИ"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ai_history (user_id, role, message)
            VALUES (?, ?, ?)
        """, (user_id, role, message))
        self.conn.commit()
    
    def get_ai_history(self, user_id, limit=10):
        """Получение последних сообщений с ИИ"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT role, message FROM ai_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        # Возвращаем в обратном порядке (от старых к новым)
        return list(reversed(cursor.fetchall()))
    
    # ===== Вспомогательные функции =====
    def close(self):
        """Закрытие подключения к базе данных"""
        if self.conn:
            self.conn.close()
            logger.info("Подключение к базе данных закрыто")
