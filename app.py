import os
import re
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import requests
import sqlite3
import PyPDF2
import docx
from collections import Counter
import nltk
from nltk.corpus import stopwords

# NEW IMPORT
from keywords_config import TECH_SKILLS, ROLE_KEYWORDS, SYNONYMS

# ---------------- CITY LIST (NEW) ----------------
CITY_LIST = [
    "delhi", "new delhi", "noida", "gurgaon", "gurugram", "faridabad",
    "mumbai", "thane", "navi mumbai",
    "pune", "nagpur",
    "hyderabad",
    "bengaluru", "bangalore",
    "chennai",
    "kolkata", "howrah",
    "ahmedabad", "surat", "vadodara",
    "jaipur", "udaipur",
    "lucknow", "kanpur",
    "indore", "bhopal",
    "chandigarh", "mohali", "panchkula",
    "coimbatore", "kochi"
]

# Load env
load_dotenv()

# Ensure stopwords exist
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_COUNTRY = "in"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXT = {'pdf', 'docx', 'txt'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.getenv("SECRET_KEY", "change-me")


# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("joblens.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- TEXT EXTRACTION ----------------
# def extract_text_from_pdf(path):
#     text = []
#     with open(path, "rb") as f:
#         reader = PyPDF2.PdfReader(f)
#         for page in reader.pages:
#             text.append(page.extract_text() or "")
#     return "\n".join(text)
from pdfminer.high_level import extract_text as pdfminer_extract

def extract_text_from_pdf(path):
    try:
        text = pdfminer_extract(path)
        return text if text else ""
    except Exception as e:
        print("PDF ERROR:", e)
        return ""


def extract_text_from_docx(path):
    doc = docx.Document(path)
    return "\n".join([p.text for p in doc.paragraphs])


def extract_text_from_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# ---------------- SMART KEYWORDS ----------------
STOPWORDS = set(stopwords.words("english"))

def normalize_word(w):
    return re.sub(r"[^a-z0-9\s]", "", w.lower()).strip()

def generate_bigrams(words):
    return [" ".join([words[i], words[i+1]]) for i in range(len(words)-1)]

def expand_synonyms(term):
    t = term.lower()
    return SYNONYMS.get(t, t)

def extract_keywords(text, max_keywords=10):
    if not text or len(text) < 3:
        return []

    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    tokens = [x for x in t.split() if x not in STOPWORDS and len(x) > 2]

    if not tokens:
        return []

    unigrams = tokens
    bigrams = generate_bigrams(tokens)

    uni_counts = Counter(unigrams)
    bi_counts = Counter(bigrams)

    scores = {}

    for w, c in uni_counts.items():
        w = expand_synonyms(w)
        scores[w] = scores.get(w, 0) + c * 1.0

    for b, c in bi_counts.items():
        b = expand_synonyms(b)
        scores[b] = scores.get(b, 0) + c * 2.5

    full_text = " " + t + " "
    for skill in TECH_SKILLS:
        if skill in full_text:
            scores[skill] = scores.get(skill, 0) + 8.0

    for role in ROLE_KEYWORDS:
        if role in full_text:
            scores[role] = scores.get(role, 0) + 10.0

    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best = [k for k, v in sorted_items][:max_keywords]
    return best


# ---------------- LOCATION DETECTION (NEW) ----------------
def extract_location(text):
    text_lower = text.lower()
    for city in CITY_LIST:
        if city in text_lower:
            return city
    return ""


# ---------------- SAVE FUNCTIONS ----------------
def save_upload(user_id, filename, file_text, source):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO uploads (user_id, filename, file_text, source) VALUES (?, ?, ?, ?)",
        (user_id, filename, file_text, source)
    )
    conn.commit()
    conn.close()


def save_search(user_id, query_text, keywords, location, results_count):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO searches (user_id, query_text, keywords, location, results_count) VALUES (?, ?, ?, ?, ?)",
        (user_id, query_text, ",".join(keywords), location, results_count)
    )
    conn.commit()
    conn.close()


# ---------------- ADZUNA API ----------------
def adzuna_search(params):
    base = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
    q = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": 20,
        "what": params.get("what", ""),
        "where": params.get("where", "")
    }

    try:
        resp = requests.get(base, params=q, timeout=8)
    except Exception as e:
        return {"error": "request_failed", "details": str(e)}

    if resp.status_code == 200:
        return resp.json()
    else:
        return {"error": resp.status_code, "details": resp.text}


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        source_type = request.form.get("source_type")
        user_id = None

        if name or email:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
            conn.commit()
            user_id = cur.lastrowid
            conn.close()

        # LinkedIn paste
        if source_type == "linkedin":
            linkedin_text = request.form.get("linkedin_text", "")
            keywords = extract_keywords(linkedin_text)
            save_upload(user_id, "linkedin_paste", linkedin_text, "linkedin")

            kw_list = keywords[:2]
            return redirect(url_for("search_jobs") + "?kw=" + " ".join(kw_list))

        # Resume upload
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)

            ext = filename.split(".")[-1].lower()

            if ext == "pdf":
                txt = extract_text_from_pdf(path)
            elif ext == "docx":
                txt = extract_text_from_docx(path)
            else:
                txt = extract_text_from_txt(path)

            # Extract keywords
            keywords = extract_keywords(txt)

            # Extract location (NEW)
            detected_location = extract_location(txt)

            save_upload(user_id, filename, txt, "resume")

            # Redirect with auto-filled kw + location (NEW)
            return redirect(
                url_for("search_jobs") +
                f"?kw={' '.join(keywords[:2])}&loc={detected_location}"
            )

        flash("File not allowed!")
        return redirect(request.url)

    return render_template("upload.html")


@app.route("/search", methods=["GET", "POST"])
def search_jobs():
    if request.method == "POST":
        keywords = request.form.get("keywords", "")
        location = request.form.get("location", "")

        kw_list = keywords.split()
        kw = " ".join(kw_list[:2])   # Top-2 keywords

        data = adzuna_search({"what": kw, "where": location})
        results = data.get("results", [])
        save_search(None, kw, extract_keywords(kw), location, len(results))

        return render_template("results.html", results=results, keywords=kw, location=location)

    # GET auto-fill (NEW)
    kwq = request.args.get("kw", "")
    locq = request.args.get("loc", "")

    return render_template("search.html", suggested=kwq, suggested_loc=locq)


@app.route("/api/search", methods=["POST"])
def api_search():
    body = request.json or {}
    q = body.get("q", "")
    loc = body.get("location", "")
    data = adzuna_search({"what": q, "where": loc})
    return jsonify(data)

@app.route("/admin/uploads")
def admin_uploads():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM uploads")
    total = cur.fetchone()["total"]
    return f"<h1>Total Resumes Uploaded: {total}</h1>"

@app.route("/admin")
def admin_dashboard():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM uploads")
    uploads = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM searches")
    searches = cur.fetchone()[0]

    return f"""
    <h2>Admin Dashboard</h2>
    <p>Total Users: {users}</p>
    <p>Total Resume Uploads: {uploads}</p>
    <p>Total Job Searches: {searches}</p>
    """
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cur.fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password")
            return redirect(url_for("login"))

    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)

