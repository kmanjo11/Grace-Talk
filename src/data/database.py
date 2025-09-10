import sqlite3
import uuid
from contextlib import contextmanager
from src.data.models import Conversation, Chat

DATABASE_PATH = "chats.db"

@contextmanager
def create_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    try:
        yield cursor
    finally:
        connection.commit()
        connection.close()

def create_tables():
    with create_connection() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')

        # Lessons table for commit-learning (stores mined bug/fix pairs)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id TEXT PRIMARY KEY,
                repo TEXT,
                file_path TEXT,
                branch TEXT,
                commit_sha TEXT,
                commit_message TEXT,
                before_code TEXT,
                after_code TEXT,
                tags TEXT,
                language TEXT,
                framework TEXT,
                change_type TEXT,
                lines_changed INTEGER,
                tokens_changed INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migrate: add missing columns if the table already exists without them
        cursor.execute("PRAGMA table_info(lessons)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        add_columns = [
            ("branch", "TEXT"),
            ("language", "TEXT"),
            ("framework", "TEXT"),
            ("change_type", "TEXT"),
            ("lines_changed", "INTEGER"),
            ("tokens_changed", "INTEGER"),
        ]
        for col, col_type in add_columns:
            if col not in existing_cols:
                cursor.execute(f"ALTER TABLE lessons ADD COLUMN {col} {col_type}")

def save_conversation(conversation):
    with create_connection() as cursor:
        cursor.execute("INSERT INTO conversations (id, user_id, name) VALUES (?, ?, ?)", (conversation.id, conversation.user_id, conversation.name))

def save_chat(chat):
    with create_connection() as cursor:
        cursor.execute("INSERT INTO chats (id, conversation_id, role, content) VALUES (?, ?, ?, ?)", (str(uuid.uuid4()), chat.conversation_id, chat.role, chat.content))

def get_all_conversations(user_id):
    with create_connection() as cursor:
        cursor.execute("SELECT id, user_id, name FROM conversations WHERE user_id=?", (user_id,))
        result = cursor.fetchall()
        conversations = [Conversation(*row) for row in result]
        return [conversation.to_dict() for conversation in conversations]

def get_conversation_by_id(conversation_id):
    with create_connection() as cursor:
        cursor.execute("SELECT id, name FROM conversations WHERE id=?", (conversation_id,))
        result = cursor.fetchone()
        return Conversation(*result) if result else None

def get_chats_by_conversation_id(conversation_id):
    with create_connection() as cursor:
        cursor.execute("SELECT conversation_id, role, content FROM chats WHERE conversation_id=?", (conversation_id,))
        result = cursor.fetchall()
        chats = [Chat(conversation_id, *row[1:]) for row in result]
        return [chat.to_dict() for chat in chats]

def delete_conversation(conversation_id):
    with create_connection() as cursor:
        cursor.execute("DELETE FROM chats WHERE conversation_id=?", (conversation_id,))
        cursor.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))

# ----- Lessons CRUD -----
def save_lesson(lesson):
    """Save a lesson dict with keys: id, repo, file_path, branch, commit_sha, commit_message, before_code, after_code, tags, language, framework, change_type, lines_changed, tokens_changed"""
    with create_connection() as cursor:
        cursor.execute(
            """
            INSERT OR REPLACE INTO lessons (id, repo, file_path, branch, commit_sha, commit_message, before_code, after_code, tags, language, framework, change_type, lines_changed, tokens_changed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson.get('id'),
                lesson.get('repo'),
                lesson.get('file_path'),
                lesson.get('branch'),
                lesson.get('commit_sha'),
                lesson.get('commit_message'),
                lesson.get('before_code'),
                lesson.get('after_code'),
                lesson.get('tags', ''),
                lesson.get('language'),
                lesson.get('framework'),
                lesson.get('change_type'),
                int(lesson.get('lines_changed') or 0),
                int(lesson.get('tokens_changed') or 0),
            )
        )

def get_all_lessons(limit=200):
    with create_connection() as cursor:
        cursor.execute("SELECT id, repo, file_path, branch, commit_sha, commit_message, before_code, after_code, tags, language, framework, change_type, lines_changed, tokens_changed FROM lessons ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        lessons = []
        for r in rows:
            lessons.append({
                'id': r[0], 'repo': r[1], 'file_path': r[2], 'branch': r[3], 'commit_sha': r[4],
                'commit_message': r[5], 'before_code': r[6], 'after_code': r[7], 'tags': r[8],
                'language': r[9], 'framework': r[10], 'change_type': r[11], 'lines_changed': r[12], 'tokens_changed': r[13]
            })
        return lessons

def find_lessons_by_text(query, limit=5):
    """Very simple LIKE-based search as a fallback; more advanced retrieval in utils.lessons."""
    like = f"%{query}%"
    with create_connection() as cursor:
        cursor.execute(
            """
            SELECT id, repo, file_path, branch, commit_sha, commit_message, before_code, after_code, tags, language, framework, change_type, lines_changed, tokens_changed
            FROM lessons
            WHERE commit_message LIKE ? OR before_code LIKE ? OR after_code LIKE ? OR tags LIKE ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (like, like, like, like, limit)
        )
        rows = cursor.fetchall()
        lessons = []
        for r in rows:
            lessons.append({
                'id': r[0], 'repo': r[1], 'file_path': r[2], 'branch': r[3], 'commit_sha': r[4],
                'commit_message': r[5], 'before_code': r[6], 'after_code': r[7], 'tags': r[8],
                'language': r[9], 'framework': r[10], 'change_type': r[11], 'lines_changed': r[12], 'tokens_changed': r[13]
            })
        return lessons