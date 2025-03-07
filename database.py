import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    # Таблица для кошельков: user_id, адрес кошелька и зашифрованная мнемоника
    cur.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            wallet_address TEXT,
            encrypted_mnemonic TEXT
        )
    ''')
    # Таблица для пользовательских токенов – добавлена колонка token_name
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token_symbol TEXT,
            token_name TEXT,
            token_address TEXT,
            balance REAL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_wallet_by_user(user_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT wallet_address, encrypted_mnemonic FROM wallets WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result

def add_wallet(user_id, wallet_address, encrypted_mnemonic):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO wallets (user_id, wallet_address, encrypted_mnemonic) VALUES (?, ?, ?)",
        (user_id, wallet_address, encrypted_mnemonic)
    )
    conn.commit()
    conn.close()

def add_user_token(user_id, token_symbol, token_name, token_address):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_tokens (user_id, token_symbol, token_name, token_address) VALUES (?, ?, ?, ?)",
        (user_id, token_symbol, token_name, token_address)
    )
    conn.commit()
    conn.close()

def get_user_tokens(user_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT token_symbol, token_name, token_address FROM user_tokens WHERE user_id=?", (user_id,))
    tokens = cur.fetchall()
    conn.close()
    return tokens
