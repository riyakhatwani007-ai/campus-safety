"""Campus Safety System - Flask app.  Run:  python app.py"""
import os, re, io, csv, json
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash, jsonify, abort, Response, g)
from werkzeug.security import generate_password_hash, check_password_hash

import db
from models.triage import predict, detect_subtopic

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  PERMANENT_SESSION_LIFETIME=__import__("datetime").timedelta(days=14))

with open(os.path.join(db.BASE, "data", "first_aid.json"), encoding="utf-8") as f:
    FIRST_AID = json.load(f)

CATEGORIES = list(FIRST_AID["categories"].keys())
STATUSES = ("open", "responding", "resolved")


# ---------- helpers: login + roles ----------
@app.before_request
def load_user():
    uid = session.get("user_id")
    g.user = db.query("SELECT id,name,email,role,phone FROM users WHERE id=?", (uid,), one=True) if uid else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not g.user:
            if request.path.startswith("/api/"):
                return jsonify(error="login required"), 401
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapper


def security_only(fn):
    @wraps(fn)
    @login_required
    def wrapper(*a, **kw):
        if g.user["role"] != "security":
            abort(403)
        return fn(*a, **kw)
    return wrapper


@app.context_processor
def inject_user():
    return {"user": g.get("user")}


# ---------- auth ----------
@app.route("/")
def index():
    if g.user:
        return redirect(url_for("dashboard" if g.user["role"] == "security" else "sos"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        if role not in ("student", "faculty"):          # security accounts are never self-registered
            role = "student"
        if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter your name and a valid email.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif db.query("SELECT id FROM users WHERE email=?", (email,), one=True):
            flash("That email is already registered.", "error")
        else:
            db.execute("INSERT INTO users (name,email,password_hash,role,phone,created_at) VALUES (?,?,?,?,?,?)",
                       (name, email, generate_password_hash(password), role, phone, db.now()))
            flash("Account created. Please log in.", "ok")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        u = db.query("SELECT * FROM users WHERE email=?", (email,), one=True)
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session.clear()
            session.permanent = True        # stay logged in across browser restarts (14 days)
            session["user_id"] = u["id"]
            return redirect(url_for("index"))
        flash("Wrong email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- SOS flow ----------
@app.route("/sos")
@login_required
def sos():
    return render_template("sos.html")


def _num(v, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


@app.route("/api/sos", methods=["POST"])
@login_required
def api_sos():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()[:1000]
    if not text:
        return jsonify(error="Please describe what is happening."), 400
    result = predict(text)                                   # <-- AI triage
    t = db.now()
    incident_id = db.execute(
        "INSERT INTO incidents (user_id,message,category,severity,confidence,status,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (g.user["id"], text, result["category"], result["severity"], result["confidence"], "open", t, t))
    lat, lng = _num(data.get("lat"), -90, 90), _num(data.get("lng"), -180, 180)
    if lat is not None and lng is not None:
        db.execute("INSERT INTO incident_locations (incident_id,lat,lng,accuracy,recorded_at) VALUES (?,?,?,?,?)",
                   (incident_id, lat, lng, _num(data.get("accuracy"), 0, 1e7), t))
    return jsonify(id=incident_id, url=url_for("incident", incident_id=incident_id), **result)


def _get_incident_or_abort(incident_id):
    row = db.query("SELECT i.*, u.name AS user_name, u.phone AS user_phone FROM incidents i "
                   "JOIN users u ON u.id=i.user_id WHERE i.id=?", (incident_id,), one=True)
    if not row:
        abort(404)
    if row["user_id"] != g.user["id"] and g.user["role"] != "security":
        abort(403)
    return row


@app.route("/incident/<int:incident_id>")
@login_required
def incident(incident_id):
    inc = _get_incident_or_abort(incident_id)
    view_cat = request.args.get("as", inc["category"])           # lets the user switch if AI guessed wrong
    if view_cat not in FIRST_AID["categories"]:
        view_cat = inc["category"]
    sub = detect_subtopic(inc["message"]) if view_cat in ("medical", "accident", "unknown") else None
    contacts = [c for c in db.query("SELECT * FROM emergency_contacts ORDER BY is_national ASC, id ASC")
                if "all" in c["categories"].split(",") or view_cat in c["categories"].split(",")]
    for c in contacts:
        c["callable"] = bool(re.fullmatch(r"[0-9+\- ]{3,}", c["number"]))
    loc = db.query("SELECT lat,lng,accuracy,recorded_at FROM incident_locations WHERE incident_id=? "
                   "ORDER BY id DESC LIMIT 1", (incident_id,), one=True)
    return render_template("incident.html", inc=inc, guide=FIRST_AID["categories"][view_cat],
                           sub=FIRST_AID["subtopics"].get(sub), contacts=contacts, loc=loc,
                           view_cat=view_cat, categories=CATEGORIES, disclaimer=FIRST_AID["disclaimer"],
                           is_owner=inc["user_id"] == g.user["id"])


@app.route("/api/location/<int:incident_id>", methods=["POST"])
@login_required
def api_location(incident_id):
    inc = db.query("SELECT id,user_id,status FROM incidents WHERE id=?", (incident_id,), one=True)
    if not inc or inc["user_id"] != g.user["id"]:
        return jsonify(error="not found"), 404
    data = request.get_json(silent=True) or {}
    lat, lng = _num(data.get("lat"), -90, 90), _num(data.get("lng"), -180, 180)
    if lat is None or lng is None:
        return jsonify(error="bad coordinates"), 400
    if inc["status"] != "resolved":
        db.execute("INSERT INTO incident_locations (incident_id,lat,lng,accuracy,recorded_at) VALUES (?,?,?,?,?)",
                   (incident_id, lat, lng, _num(data.get("accuracy"), 0, 1e7), db.now()))
    return jsonify(status=inc["status"])


# ---------- security dashboard ----------
INCIDENT_SQL = (
    "SELECT i.id,i.message,i.category,i.severity,i.confidence,i.status,i.created_at,"
    "u.name AS user_name,u.phone AS user_phone,"
    "(SELECT l.lat FROM incident_locations l WHERE l.incident_id=i.id ORDER BY l.id DESC LIMIT 1) AS lat,"
    "(SELECT l.lng FROM incident_locations l WHERE l.incident_id=i.id ORDER BY l.id DESC LIMIT 1) AS lng "
    "FROM incidents i JOIN users u ON u.id=i.user_id WHERE 1=1")


def _list_incidents(status=None, severity=None, q=None, limit=300):
    sql, args = INCIDENT_SQL, []
    if status in STATUSES:
        sql += " AND i.status=?"; args.append(status)
    if severity in ("low", "medium", "high"):
        sql += " AND i.severity=?"; args.append(severity)
    if q:
        sql += " AND (i.message LIKE ? OR u.name LIKE ?)"; args += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY CASE i.status WHEN 'resolved' THEN 1 ELSE 0 END, " \
           "CASE i.severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, i.id DESC LIMIT " + str(int(limit))
    rows = db.query(sql, tuple(args))
    for r in rows:
        r["created_at"] = str(r["created_at"])
    return rows


@app.route("/dashboard")
@security_only
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/incidents")
@security_only
def api_incidents():
    return jsonify(_list_incidents(request.args.get("status"), request.args.get("severity"),
                                   request.args.get("q", "").strip()[:100]))


@app.route("/api/incident/<int:incident_id>/status", methods=["POST"])
@security_only
def api_status(incident_id):
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in STATUSES:
        return jsonify(error="bad status"), 400
    db.execute("UPDATE incidents SET status=?, updated_at=? WHERE id=?", (status, db.now(), incident_id))
    return jsonify(ok=True, status=status)


@app.route("/export.csv")
@security_only
def export_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "time", "reporter", "phone", "message", "category", "severity", "status", "lat", "lng"])
    for r in _list_incidents(limit=100000):
        w.writerow([r["id"], r["created_at"], r["user_name"], r["user_phone"], r["message"], r["category"],
                    r["severity"], r["status"], r["lat"], r["lng"]])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=incident_report.csv"})


db.init_db()

if __name__ == "__main__":
    # host 0.0.0.0 lets your phone (same Wi-Fi) open http://<laptop-ip>:5000
    # NOTE: phone GPS needs HTTPS - see README for the ngrok trick.
    app.run(host="0.0.0.0", port=5000, debug=True)
