# ===================================================================
# BINGO PALACE – STREAMLIT VERSION (with unique keys fix)
# ===================================================================
import streamlit as st
import sqlite3
# For MySQL, uncomment the line below and install PyMySQL:
# import pymysql
import hashlib
import json
import random
import time
from datetime import datetime, timedelta
import pandas as pd

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="BINGO Palace",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- DATABASE SETUP (Switchable) ----------
# Set DB_TYPE to 'sqlite' or 'mysql'
DB_TYPE = 'sqlite'  # Change to 'mysql' for production

if DB_TYPE == 'sqlite':
    DB_FILE = "bingo.db"
    def get_db():
        return sqlite3.connect(DB_FILE)
else:
    # MySQL configuration (replace with your credentials)
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "246800"
    DB_NAME = "bingo"
    def get_db():
        return pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

def init_db():
    conn = get_db()
    c = conn.cursor()
    if DB_TYPE == 'sqlite':
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            balance REAL DEFAULT 0,
            role TEXT DEFAULT 'player'
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT DEFAULT 'waiting',
            selection_end_time TEXT,
            pot REAL DEFAULT 0,
            prize REAL DEFAULT 0,
            called_numbers TEXT DEFAULT '[]'
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS selected_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            user_id INTEGER,
            card_id INTEGER,
            FOREIGN KEY(game_id) REFERENCES games(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            user_id INTEGER,
            username TEXT,
            card_id INTEGER,
            prize REAL,
            pattern TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            phone TEXT,
            status TEXT,
            created_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            type TEXT,
            read INTEGER DEFAULT 0,
            created_at TEXT
        )''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(255),
            balance DECIMAL(10,2) DEFAULT 0,
            role VARCHAR(20) DEFAULT 'player'
        ) ENGINE=InnoDB''')
        c.execute('''CREATE TABLE IF NOT EXISTS games (
            id INT AUTO_INCREMENT PRIMARY KEY,
            status VARCHAR(20) DEFAULT 'waiting',
            selection_end_time DATETIME,
            pot DECIMAL(10,2) DEFAULT 0,
            prize DECIMAL(10,2) DEFAULT 0,
            called_numbers JSON DEFAULT '[]'
        ) ENGINE=InnoDB''')
        c.execute('''CREATE TABLE IF NOT EXISTS selected_cards (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id INT,
            user_id INT,
            card_id INT,
            FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id)
        ) ENGINE=InnoDB''')
        c.execute('''CREATE TABLE IF NOT EXISTS winners (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id INT,
            user_id INT,
            username VARCHAR(50),
            card_id INT,
            prize DECIMAL(10,2),
            pattern TEXT
        ) ENGINE=InnoDB''')
        c.execute('''CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            amount DECIMAL(10,2),
            phone VARCHAR(20),
            status VARCHAR(20),
            created_at DATETIME
        ) ENGINE=InnoDB''')
        c.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            message TEXT,
            type VARCHAR(20),
            read BOOLEAN DEFAULT 0,
            created_at DATETIME
        ) ENGINE=InnoDB''')
    conn.commit()
    conn.close()

init_db()

# ---------- UTILITY FUNCTIONS ----------
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_password(pw, hashed):
    return hash_password(pw) == hashed

def get_user(username):
    conn = get_db()
    c = conn.cursor()
    if DB_TYPE == 'sqlite':
        c.execute("SELECT id, username, password, balance, role FROM users WHERE username = ?", (username,))
    else:
        c.execute("SELECT id, username, password, balance, role FROM users WHERE username = %s", (username,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(username, password):
    conn = get_db()
    c = conn.cursor()
    try:
        if DB_TYPE == 'sqlite':
            c.execute("INSERT INTO users (username, password, balance) VALUES (?, ?, 0)", (username, hash_password(password)))
        else:
            c.execute("INSERT INTO users (username, password, balance) VALUES (%s, %s, 0)", (username, hash_password(password)))
        conn.commit()
        return True, "Registration successful!"
    except:
        return False, "Username already exists."
    finally:
        conn.close()

def update_balance(user_id, amount):
    conn = get_db()
    c = conn.cursor()
    if DB_TYPE == 'sqlite':
        c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    else:
        c.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = get_db()
    c = conn.cursor()
    if DB_TYPE == 'sqlite':
        c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    else:
        c.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
    bal = c.fetchone()[0]
    conn.close()
    return bal

# ---------- GAME STATE FUNCTIONS ----------
def get_current_game():
    conn = get_db()
    c = conn.cursor()
    if DB_TYPE == 'sqlite':
        c.execute("SELECT id, status, selection_end_time, pot, prize, called_numbers FROM games ORDER BY id DESC LIMIT 1")
    else:
        c.execute("SELECT id, status, selection_end_time, pot, prize, called_numbers FROM games ORDER BY id DESC LIMIT 1")
    game = c.fetchone()
    conn.close()
    return game

def create_new_game():
    conn = get_db()
    c = conn.cursor()
    end_time = (datetime.now() + timedelta(seconds=30)).isoformat()
    if DB_TYPE == 'sqlite':
        c.execute("INSERT INTO games (status, selection_end_time, pot) VALUES ('waiting', ?, 0)", (end_time,))
    else:
        c.execute("INSERT INTO games (status, selection_end_time, pot) VALUES ('waiting', %s, 0)", (end_time,))
    game_id = c.lastrowid
    conn.commit()
    conn.close()
    return game_id

def get_taken_cards(game_id):
    conn = get_db()
    c = conn.cursor()
    if DB_TYPE == 'sqlite':
        c.execute("SELECT card_id FROM selected_cards WHERE game_id = ?", (game_id,))
    else:
        c.execute("SELECT card_id FROM selected_cards WHERE game_id = %s", (game_id,))
    taken = [row[0] for row in c.fetchall()]
    conn.close()
    return taken

def get_user_cards(game_id, user_id):
    conn = get_db()
    c = conn.cursor()
    if DB_TYPE == 'sqlite':
        c.execute("SELECT card_id FROM selected_cards WHERE game_id = ? AND user_id = ?", (game_id, user_id))
    else:
        c.execute("SELECT card_id FROM selected_cards WHERE game_id = %s AND user_id = %s", (game_id, user_id))
    cards = [row[0] for row in c.fetchall()]
    conn.close()
    return cards

def join_game(game_id, user_id, card_ids):
    conn = get_db()
    c = conn.cursor()
    bal = get_balance(user_id)
    cost = len(card_ids) * 20
    if bal < cost:
        return False, f"Insufficient balance. Need {cost} ETB, you have {bal} ETB"
    if DB_TYPE == 'sqlite':
        c.execute("SELECT status FROM games WHERE id = ?", (game_id,))
    else:
        c.execute("SELECT status FROM games WHERE id = %s", (game_id,))
    status = c.fetchone()[0]
    if status != 'waiting':
        return False, "Game is not accepting players."
    for cid in card_ids:
        if DB_TYPE == 'sqlite':
            c.execute("INSERT INTO selected_cards (game_id, user_id, card_id) VALUES (?, ?, ?)", (game_id, user_id, cid))
        else:
            c.execute("INSERT INTO selected_cards (game_id, user_id, card_id) VALUES (%s, %s, %s)", (game_id, user_id, cid))
    if DB_TYPE == 'sqlite':
        c.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (cost, user_id))
        c.execute("UPDATE games SET pot = pot + ? WHERE id = ?", (cost * 0.85, game_id))
    else:
        c.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (cost, user_id))
        c.execute("UPDATE games SET pot = pot + %s WHERE id = %s", (cost * 0.85, game_id))
    conn.commit()
    conn.close()
    return True, f"Joined with {len(card_ids)} card(s)."

def get_players(game_id):
    conn = get_db()
    c = conn.cursor()
    if DB_TYPE == 'sqlite':
        c.execute("""
            SELECT u.username, COUNT(sc.card_id) as card_count
            FROM selected_cards sc
            JOIN users u ON sc.user_id = u.id
            WHERE sc.game_id = ?
            GROUP BY u.username
        """, (game_id,))
    else:
        c.execute("""
            SELECT u.username, COUNT(sc.card_id) as card_count
            FROM selected_cards sc
            JOIN users u ON sc.user_id = u.id
            WHERE sc.game_id = %s
            GROUP BY u.username
        """, (game_id,))
    players = c.fetchall()
    conn.close()
    return players

def add_notification(user_id, message, type="info"):
    conn = get_db()
    c = conn.cursor()
    if DB_TYPE == 'sqlite':
        c.execute("INSERT INTO notifications (user_id, message, type, created_at) VALUES (?, ?, ?, ?)",
                  (user_id, message, type, datetime.now().isoformat()))
    else:
        c.execute("INSERT INTO notifications (user_id, message, type, created_at) VALUES (%s, %s, %s, %s)",
                  (user_id, message, type, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ---------- BINGO CARD GENERATION ----------
def generate_card_numbers(card_id):
    columns = {
        'B': list(range(1, 16)),
        'I': list(range(16, 31)),
        'N': list(range(31, 46)),
        'G': list(range(46, 61)),
        'O': list(range(61, 76))
    }
    random.seed(card_id)
    card = [[None]*5 for _ in range(5)]
    col_names = ['B','I','N','G','O']
    for col, col_name in enumerate(col_names):
        pool = columns[col_name][:]
        random.shuffle(pool)
        for row in range(5):
            if col == 2 and row == 2:
                card[row][col] = 'F'
            else:
                card[row][col] = pool[row]
    random.seed()
    return card

# ---------- WIN DETECTION ----------
def check_bingo(card_numbers, called_numbers):
    if isinstance(called_numbers, str):
        called_numbers = json.loads(called_numbers)
    grid = [[False]*5 for _ in range(5)]
    for r in range(5):
        for c in range(5):
            val = card_numbers[r][c]
            if val == 'F' or val in called_numbers:
                grid[r][c] = True

    for r in range(5):
        if all(grid[r]):
            return {'type': 'row', 'index': r+1}
    for c in range(5):
        if all(grid[r][c] for r in range(5)):
            return {'type': 'column', 'letter': ['B','I','N','G','O'][c]}
    if all(grid[i][i] for i in range(5)):
        return {'type': 'diagonal', 'direction': 'main'}
    if all(grid[i][4-i] for i in range(5)):
        return {'type': 'diagonal', 'direction': 'anti'}
    if grid[0][0] and grid[0][4] and grid[4][0] and grid[4][4]:
        return {'type': 'four-corners'}
    if all(grid[r][c] for r in range(5) for c in range(5)):
        return {'type': 'blackout'}
    return None

# ---------- GRAPHICAL BINGO CARD RENDERER ----------
def render_bingo_card(card_id, card_numbers, called_numbers):
    """Display a beautiful BINGO card with called numbers highlighted."""
    st.markdown(f"""
    <div style="border: 2px solid #FFD700; border-radius: 12px; padding: 15px; background: linear-gradient(135deg, #ffffff, #f0f8ff); margin: 10px 0; display: inline-block;">
        <div style="text-align: center; font-weight: bold; font-size: 18px; margin-bottom: 8px; color: #000;">CARD #{card_id}</div>
        <table style="border-collapse: collapse; width: 100%; border: 2px solid #000;">
            <tr>
                <th style="border: 2px solid #000; padding: 8px; background: #FF3366; color: white;">B</th>
                <th style="border: 2px solid #000; padding: 8px; background: #00C9B7; color: white;">I</th>
                <th style="border: 2px solid #000; padding: 8px; background: #9C27B0; color: white;">N</th>
                <th style="border: 2px solid #000; padding: 8px; background: #4CAF50; color: white;">G</th>
                <th style="border: 2px solid #000; padding: 8px; background: #FF9800; color: white;">O</th>
            </tr>
    """, unsafe_allow_html=True)

    for row in range(5):
        html_row = "<tr>"
        for col in range(5):
            val = card_numbers[row][col]
            is_called = (val != 'F' and val in called_numbers) or (val == 'F')
            bg_color = "linear-gradient(135deg, #27ae60, #2ecc71)" if is_called else "#f0f8ff"
            color = "white" if is_called else "black"
            border = "2px solid #666"
            display_val = "⭐" if val == 'F' else str(val)
            html_row += f"""
                <td style="border: {border}; padding: 12px; text-align: center; font-weight: bold; font-size: 16px; 
                           background: {bg_color}; color: {color};">
                    {display_val}
                </td>
            """
        html_row += "</tr>"
        st.markdown(html_row, unsafe_allow_html=True)

    st.markdown("</table></div>", unsafe_allow_html=True)

# ---------- SESSION STATE INIT ----------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'balance' not in st.session_state:
    st.session_state.balance = 0
if 'selected_cards' not in st.session_state:
    st.session_state.selected_cards = []
if 'joined_cards' not in st.session_state:
    st.session_state.joined_cards = []
if 'notifications' not in st.session_state:
    st.session_state.notifications = []
if 'game_id' not in st.session_state:
    st.session_state.game_id = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'last_call_time' not in st.session_state:
    st.session_state.last_call_time = 0

# ---------- LOGIN / REGISTER ----------
def login_form():
    st.subheader("🔐 Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", key="login_button"):
        user = get_user(username)
        if user and verify_password(password, user[2]):
            st.session_state.logged_in = True
            st.session_state.user_id = user[0]
            st.session_state.username = user[1]
            st.session_state.balance = user[3]
            st.session_state.is_admin = (user[4] == 'admin')
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def register_form():
    st.subheader("📝 Register")
    username = st.text_input("Choose Username", key="reg_username")
    password = st.text_input("Password", type="password", key="reg_password")
    confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
    if st.button("Register", key="reg_button"):
        if password != confirm:
            st.error("Passwords do not match")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters")
        else:
            success, msg = create_user(username, password)
            if success:
                st.success(msg + " Please login.")
            else:
                st.error(msg)

# ---------- MAIN APP ----------
def main():
    if not st.session_state.logged_in:
        st.title("🎲 BINGO Palace")
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            login_form()
        with tab2:
            register_form()
        return

    # ---------- SIDEBAR ----------
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.write(f"💰 Balance: **{st.session_state.balance:.2f} ETB**")
        if st.button("🚪 Logout", key="logout_button"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.balance = 0
            st.session_state.selected_cards = []
            st.session_state.joined_cards = []
            st.rerun()
        st.markdown("---")
        st.write("### 🎯 Navigation")
        page = st.radio("Go to", ["🏠 Game Lobby", "📊 History", "💳 Add Funds"], key="nav_radio")

    # ---------- GAME LOBBY ----------
    if page == "🏠 Game Lobby":
        st.title("🎲 BINGO Palace")

        # Get current game
        game = get_current_game()
        if not game:
            st.info("No active game. Starting a new one...")
            game_id = create_new_game()
            st.rerun()
        else:
            game_id, status, selection_end_time, pot, prize, called_numbers_json = game
            called_numbers = json.loads(called_numbers_json) if called_numbers_json else []

        st.session_state.game_id = game_id

        # Timer display
        if status == 'waiting':
            if selection_end_time:
                end_time = datetime.fromisoformat(selection_end_time)
                now = datetime.now()
                remaining = (end_time - now).total_seconds()
                if remaining <= 0:
                    conn = get_db()
                    c = conn.cursor()
                    if DB_TYPE == 'sqlite':
                        c.execute("UPDATE games SET status = 'running' WHERE id = ?", (game_id,))
                    else:
                        c.execute("UPDATE games SET status = 'running' WHERE id = %s", (game_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()
                else:
                    st.info(f"⏳ Selection phase: {int(remaining)} seconds remaining")
            else:
                st.warning("Selection end time not set.")
        elif status == 'running':
            st.success("🎮 Game is running! Numbers are being called automatically every 5 seconds.")

            # ===== AUTO-CALL LOGIC (every 5 seconds) =====
            now = time.time()
            if now - st.session_state.last_call_time >= 5:
                all_nums = set(range(1, 76))
                called = set(called_numbers)
                available = list(all_nums - called)
                if available:
                    num = random.choice(available)
                    called_numbers.append(num)
                    conn = get_db()
                    c = conn.cursor()
                    if DB_TYPE == 'sqlite':
                        c.execute("UPDATE games SET called_numbers = ? WHERE id = ?", (json.dumps(called_numbers), game_id))
                    else:
                        c.execute("UPDATE games SET called_numbers = %s WHERE id = %s", (json.dumps(called_numbers), game_id))
                    conn.commit()
                    conn.close()
                    st.session_state.last_call_time = now
                    st.rerun()
                else:
                    st.warning("All numbers called.")
                    conn = get_db()
                    c = conn.cursor()
                    if DB_TYPE == 'sqlite':
                        c.execute("UPDATE games SET status = 'finished' WHERE id = ?", (game_id,))
                    else:
                        c.execute("UPDATE games SET status = 'finished' WHERE id = %s", (game_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()

        elif status == 'finished':
            st.warning("🏁 Game ended. Waiting for next game.")

        # Players
        players = get_players(game_id)
        st.write(f"👥 Players online: {len(players)}")
        if players:
            for p in players:
                st.text(f"{p[0]} – {p[1]} cards")

        # ---------- CARD SELECTION ----------
        if status == 'waiting':
            st.subheader("📋 Select your cards (max 2) – 20 ETB each")
            taken = get_taken_cards(game_id)
            user_joined = get_user_cards(game_id, st.session_state.user_id)
            if user_joined:
                st.success(f"You have already joined with cards: {', '.join(map(str, user_joined))}")
                st.session_state.joined_cards = user_joined
            else:
                cols = st.columns(5)
                selected = st.session_state.selected_cards
                for i in range(1, 202):
                    col = cols[i % 5]
                    with col:
                        disabled = (i in taken) or (i in selected) or (len(selected) >= 2 and i not in selected)
                        btn_label = f"Card {i}"
                        if i in selected:
                            btn_label = f"✅ Card {i}"
                        elif i in taken:
                            btn_label = f"❌ Card {i}"
                        if st.button(btn_label, key=f"card_{i}", disabled=disabled):
                            if i in selected:
                                selected.remove(i)
                            else:
                                if len(selected) < 2:
                                    selected.append(i)
                            st.rerun()
                st.write(f"Selected: {selected} (Cost: {len(selected)*20} ETB)")
                if st.button("✅ Join Game", key="join_game_button"):
                    if len(selected) == 0:
                        st.error("Select at least one card.")
                    else:
                        success, msg = join_game(game_id, st.session_state.user_id, selected)
                        if success:
                            st.session_state.joined_cards = selected
                            st.session_state.selected_cards = []
                            st.success(msg)
                            add_notification(st.session_state.user_id, f"Joined game with {len(selected)} cards")
                            st.rerun()
                        else:
                            st.error(msg)

        # ---------- BINGO BOARD (running) ----------
        if status == 'running' and st.session_state.joined_cards:
            st.subheader("🎯 Your BINGO Cards")
            for card_id in st.session_state.joined_cards:
                card = generate_card_numbers(card_id)
                render_bingo_card(card_id, card, called_numbers)

                win_pattern = check_bingo(card, called_numbers)
                if win_pattern:
                    st.balloons()
                    st.success(f"🎉 BINGO! You won! Pattern: {win_pattern}")
                    conn = get_db()
                    c = conn.cursor()
                    if DB_TYPE == 'sqlite':
                        c.execute("SELECT pot FROM games WHERE id = ?", (game_id,))
                    else:
                        c.execute("SELECT pot FROM games WHERE id = %s", (game_id,))
                    pot = c.fetchone()[0]
                    if DB_TYPE == 'sqlite':
                        c.execute("""
                            INSERT INTO winners (game_id, user_id, username, card_id, prize, pattern)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (game_id, st.session_state.user_id, st.session_state.username, card_id, pot, json.dumps(win_pattern)))
                        c.execute("UPDATE games SET status = 'finished', prize = ? WHERE id = ?", (pot, game_id))
                    else:
                        c.execute("""
                            INSERT INTO winners (game_id, user_id, username, card_id, prize, pattern)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (game_id, st.session_state.user_id, st.session_state.username, card_id, pot, json.dumps(win_pattern)))
                        c.execute("UPDATE games SET status = 'finished', prize = %s WHERE id = %s", (pot, game_id))
                    conn.commit()
                    conn.close()
                    update_balance(st.session_state.user_id, pot)
                    st.session_state.balance += pot
                    add_notification(st.session_state.user_id, f"🏆 You won {pot} ETB!", "success")
                    st.rerun()

            if st.session_state.is_admin:
                st.subheader("🛠️ Admin Controls")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📢 Call Next Number", key="admin_call"):
                        all_nums = set(range(1, 76))
                        called = set(called_numbers)
                        available = list(all_nums - called)
                        if available:
                            num = random.choice(available)
                            called_numbers.append(num)
                            conn = get_db()
                            c = conn.cursor()
                            if DB_TYPE == 'sqlite':
                                c.execute("UPDATE games SET called_numbers = ? WHERE id = ?", (json.dumps(called_numbers), game_id))
                            else:
                                c.execute("UPDATE games SET called_numbers = %s WHERE id = %s", (json.dumps(called_numbers), game_id))
                            conn.commit()
                            conn.close()
                            st.success(f"Called number {num}")
                            st.rerun()
                        else:
                            st.warning("All numbers called.")
                with col2:
                    if st.button("⏹️ End Game", key="admin_end"):
                        conn = get_db()
                        c = conn.cursor()
                        if DB_TYPE == 'sqlite':
                            c.execute("UPDATE games SET status = 'finished' WHERE id = ?", (game_id,))
                        else:
                            c.execute("UPDATE games SET status = 'finished' WHERE id = %s", (game_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()

        # ---------- GAME FINISHED ----------
        if status == 'finished':
            st.subheader("🏁 Game Over")
            conn = get_db()
            c = conn.cursor()
            if DB_TYPE == 'sqlite':
                c.execute("SELECT username, card_id, prize FROM winners WHERE game_id = ?", (game_id,))
            else:
                c.execute("SELECT username, card_id, prize FROM winners WHERE game_id = %s", (game_id,))
            winner = c.fetchone()
            conn.close()
            if winner:
                st.success(f"🏆 Winner: {winner[0]} (Card #{winner[1]}) – Prize: {winner[2]} ETB")
            else:
                st.warning("No winner declared.")
            if st.button("🔄 Next Game", key="next_game_button"):
                new_id = create_new_game()
                st.session_state.joined_cards = []
                st.session_state.selected_cards = []
                st.rerun()

    # ---------- HISTORY ----------
    elif page == "📊 History":
        st.subheader("📊 Your Game History")
        conn = get_db()
        c = conn.cursor()
        if DB_TYPE == 'sqlite':
            c.execute("""
                SELECT g.id, g.status, w.prize, w.card_id, w.pattern
                FROM games g
                LEFT JOIN winners w ON g.id = w.game_id AND w.user_id = ?
                ORDER BY g.id DESC
            """, (st.session_state.user_id,))
        else:
            c.execute("""
                SELECT g.id, g.status, w.prize, w.card_id, w.pattern
                FROM games g
                LEFT JOIN winners w ON g.id = w.game_id AND w.user_id = %s
                ORDER BY g.id DESC
            """, (st.session_state.user_id,))
        history = c.fetchall()
        conn.close()
        if history:
            for row in history:
                st.write(f"Game #{row[0]} – Status: {row[1]}, Prize: {row[2] if row[2] else '0'} ETB, Card: {row[3]}, Pattern: {row[4]}")
        else:
            st.info("No games played yet.")

    # ---------- ADD FUNDS ----------
    elif page == "💳 Add Funds":
        st.subheader("💳 Add Funds")
        with st.form("payment_form"):
            amount = st.number_input("Amount (ETB)", min_value=20, step=10, key="pay_amount")
            phone = st.text_input("Phone Number", key="pay_phone")
            code = st.text_input("Confirmation Code (demo: 2121)", key="pay_code")
            if st.form_submit_button("Pay", type="primary"):
                if code == "2121":
                    update_balance(st.session_state.user_id, amount)
                    st.session_state.balance += amount
                    st.success(f"Added {amount} ETB to your balance!")
                    add_notification(st.session_state.user_id, f"💳 Added {amount} ETB")
                    st.rerun()
                else:
                    st.error("Invalid confirmation code.")

    # ---------- NOTIFICATIONS ----------
    with st.expander("🔔 Notifications"):
        conn = get_db()
        c = conn.cursor()
        if DB_TYPE == 'sqlite':
            c.execute("SELECT id, message, type, read, created_at FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 10", (st.session_state.user_id,))
        else:
            c.execute("SELECT id, message, type, read, created_at FROM notifications WHERE user_id = %s ORDER BY id DESC LIMIT 10", (st.session_state.user_id,))
        notifs = c.fetchall()
        conn.close()
        if notifs:
            for nid, msg, typ, read, created in notifs:
                st.info(msg)
        else:
            st.write("No notifications.")

if __name__ == "__main__":
    main()
