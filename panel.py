import os
from dotenv import load_dotenv
from flask import Flask, request, session, redirect
from functools import wraps

from db import init_db, top10, all_users

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "pass")
FLASK_SECRET = os.getenv("FLASK_SECRET", "change_me")

app = Flask(__name__)
app.secret_key = FLASK_SECRET

init_db()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["logged_in"] = True
            return redirect("/")
        return "<h3>Hatalı giriş</h3><a href='/login'>Tekrar dene</a>"

    return """
    <h2>Admin Login</h2>
    <form method="POST">
      <input name="username" placeholder="Kullanıcı adı" />
      <br/><br/>
      <input name="password" type="password" placeholder="Şifre" />
      <br/><br/>
      <button type="submit">Giriş</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
@login_required
def index():
    rows = top10()
    html = "<h1>Top 10 Referans</h1><ol>"
    for uname, fname, cnt in rows:
        label = f"@{uname}"
        if fname:
            label += f" — {fname}"
        html += f"<li>{label} — {cnt}</li>"
    html += "</ol>"
    html += "<p><a href='/all'>Tüm kullanıcılar</a> | <a href='/logout'>Çıkış</a></p>"
    return html

@app.route("/all")
@login_required
def all_page():
    rows = all_users()
    html = "<h1>Tüm Kullanıcılar</h1>"
    html += "<p><a href='/'>Top 10</a> | <a href='/logout'>Çıkış</a></p>"
    html += "<table border='1' cellpadding='6' cellspacing='0'>"
    html += "<tr><th>User ID</th><th>Username</th><th>Ad Soyad</th><th>Referans</th><th>Link</th></tr>"
    for user_id, username, full_name, ref_count, link in rows:
        html += f"<tr><td>{user_id}</td><td>{username or ''}</td><td>{full_name or ''}</td><td>{ref_count}</td><td>{link or ''}</td></tr>"
    html += "</table>"
    return html

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
