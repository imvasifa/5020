import sqlite3
import bcrypt

def create_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT
    )
    """)

    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
              (username, password_hash))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_db()
    print("Database created.")
