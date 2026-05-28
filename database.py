import sqlite3
from datetime import datetime
from cryptography.fernet import Fernet
import os

class Database:
    def __init__(self, db_name='clients.db'):
        self.db_name = db_name
        self.key_file = 'secret.key'
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)
        self._create_tables()

    def _load_or_create_key(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key

    def _get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                notes TEXT,
                is_vip INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                site_name TEXT NOT NULL,
                site_url TEXT,
                login_email TEXT,
                password TEXT,
                notes TEXT,
                category TEXT,
                created_at TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer'
            )
        ''')
        conn.commit()
        conn.close()

    def encrypt_password(self, password):
        if not password:
            return ''
        return self.cipher.encrypt(password.encode()).decode()

    def decrypt_password(self, encrypted_password):
        if not encrypted_password:
            return ''
        try:
            return self.cipher.decrypt(encrypted_password.encode()).decode()
        except Exception:
            return encrypted_password

    # ═══════ العملاء ═══════
    def add_client(self, name, phone='', email='', notes='', is_vip=0):
        conn = self._get_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.execute(
            'INSERT INTO clients (name,phone,email,notes,is_vip,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',
            (name, phone, email, notes, is_vip, now, now)
        )
        client_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return client_id

    def get_all_clients(self, search_term=''):
        conn = self._get_connection()
        if search_term:
            like = f'%{search_term}%'
            rows = conn.execute(
                'SELECT * FROM clients WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? ORDER BY updated_at DESC',
                (like, like, like)
            ).fetchall()
        else:
            rows = conn.execute('SELECT * FROM clients ORDER BY updated_at DESC').fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_client(self, client_id):
        conn = self._get_connection()
        row = conn.execute('SELECT * FROM clients WHERE id=?', (client_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_client(self, client_id, name, phone, email, notes, is_vip):
        conn = self._get_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            'UPDATE clients SET name=?,phone=?,email=?,notes=?,is_vip=?,updated_at=? WHERE id=?',
            (name, phone, email, notes, is_vip, now, client_id)
        )
        conn.commit()
        conn.close()

    def delete_client(self, client_id):
        conn = self._get_connection()
        conn.execute('DELETE FROM clients WHERE id=?', (client_id,))
        conn.commit()
        conn.close()

    # ═══════ المواقع ═══════
    def add_website(self, client_id, site_name, site_url='', login_email='',
                    password='', notes='', category=''):
        conn = self._get_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        encrypted_pwd = self.encrypt_password(password)
        conn.execute(
            'INSERT INTO websites (client_id,site_name,site_url,login_email,password,notes,category,created_at) VALUES (?,?,?,?,?,?,?,?)',
            (client_id, site_name, site_url, login_email, encrypted_pwd, notes, category, now)
        )
        conn.commit()
        conn.close()

    def get_websites_by_client(self, client_id):
        conn = self._get_connection()
        rows = conn.execute(
            'SELECT * FROM websites WHERE client_id=? ORDER BY created_at DESC', (client_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_websites_by_client(self, client_id):
        conn = self._get_connection()
        conn.execute('DELETE FROM websites WHERE client_id=?', (client_id,))
        conn.commit()
        conn.close()

    def get_stats(self):
        conn = self._get_connection()
        clients_count = conn.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
        websites_count = conn.execute('SELECT COUNT(*) FROM websites').fetchone()[0]
        vip_count = conn.execute('SELECT COUNT(*) FROM clients WHERE is_vip=1').fetchone()[0]
        conn.close()
        return clients_count, websites_count, vip_count

    # ═══════ المستخدمون ═══════
    def create_user(self, username, password, role='admin'):
        from werkzeug.security import generate_password_hash
        conn = self._get_connection()
        try:
            conn.execute(
                'INSERT INTO users (username,password_hash,role) VALUES (?,?,?)',
                (username, generate_password_hash(password), role)
            )
            conn.commit()
        except Exception:
            pass
        conn.close()

    def verify_user(self, username, password):
        from werkzeug.security import check_password_hash
        conn = self._get_connection()
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            return dict(user)
        return None