import sqlite3
import bcrypt

def check_login(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if row is None:
        return False

    stored_hash = row[0]
    return bcrypt.checkpw(password.encode(), stored_hash.encode())
