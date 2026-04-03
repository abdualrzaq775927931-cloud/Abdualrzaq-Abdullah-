import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ---------- INIT DB ----------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # 👤 users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE,
        role TEXT DEFAULT 'user',
        is_banned BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 📢 channels
    cur.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        channel_id BIGINT,
        channel_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 📦 content
    cur.execute("""
    CREATE TABLE IF NOT EXISTS content (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        type TEXT,
        media_type TEXT,
        text TEXT,
        file_id TEXT,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 📊 queue
    cur.execute("""
    CREATE TABLE IF NOT EXISTS queue (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        content_id INT,
        channel_id BIGINT,
        scheduled_at TIMESTAMP,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

# ---------- USERS ----------
def create_user(telegram_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO users (telegram_id)
    VALUES (%s)
    ON CONFLICT (telegram_id) DO NOTHING
    """, (telegram_id,))

    conn.commit()
    cur.close()
    conn.close()

def get_user(telegram_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
    SELECT * FROM users WHERE telegram_id=%s
    """, (telegram_id,))

    user = cur.fetchone()

    cur.close()
    conn.close()

    return user
