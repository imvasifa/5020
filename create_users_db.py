import sqlite3
import bcrypt

# ---------- CONFIG ----------
DB_NAME = "users.db"
USERNAME = "admin"
PASSWORD = "Vankai88&88"   # change if you want
# ----------------------------

# Create database
conn = sqlite3.connect(DB_NAME)
c = conn.cursor()

# Create table
c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT
    )
""")

# Hash password
password_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

# Delete old user if exists
c.execute("DELETE FROM users WHERE username=?", (USERNAME,))

# Insert new admin user
c.execute("""
    INSERT INTO users (username, password_hash)
    VALUES (?, ?)
""", (USERNAME, password_hash))

conn.commit()
conn.close()

print("users.db created successfully!")
print("Username:", USERNAME)
print("Password:", PASSWORD)
