import os
import hmac
import hashlib
import json
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename

# --- Config (nezmenené hodnoty + robustné cesty) ---
HMAC_SECRET = os.getenv("QRV_HMAC_SECRET", "saxo-verify-9f4c2b7a1e84")  # Render env var
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

# Absolútna cesta k adresáru projektu a k docs_db.json (s možnosťou override cez env)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DB_PATH = os.getenv("QRV_DOCS_DB", os.path.join(BASE_DIR, "docs_db.json"))

# Uploads: ak je v env relatívna cesta, spravíme ju absolútnu voči BASE_DIR
UPLOAD_DIR_ENV = os.getenv("QRV_UPLOAD_DIR", "uploads")
UPLOAD_DIR = (
    UPLOAD_DIR_ENV if os.path.isabs(UPLOAD_DIR_ENV)
    else os.path.join(BASE_DIR, UPLOAD_DIR_ENV)
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-me")  # pre flash správy
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB
os.makedirs(UPLOAD_DIR, exist_ok=True)


def load_db():
    """Bezpečné načítanie databázy dokumentov pri každom volaní."""
    try:
        with open(DOCS_DB_PATH, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        app.logger.info(f"[QRV] Loaded docs_db.json from {DOCS_DB_PATH}; keys={list(data.keys())}")
        return data
    except Exception as e:
        app.logger.error(f"[QRV] Failed to load docs_db.json from {DOCS_DB_PATH}: {e}")
        return {}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_hmac(doc_id, sig_hex):
    expected = hmac.new(HMAC_SECRET.encode("utf-8"), doc_id.encode("utf-8"), hashlib.sha256).hexdigest()
    # constant-time compare
    return hmac.compare_digest(expected.lower(), (sig_hex or "").lower()), expected


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/verify")
def verify():
    # URL format: /verify?id=<DOC_ID>&sig=<HMAC_HEX>
    doc_id = request.args.get("id", "").strip()
    sig = request.args.get("sig", "").strip()
    ok, expected = verify_hmac(doc_id, sig)
    if not doc_id:
        flash("Missing parameter 'id'.", "error")
        return redirect(url_for("index"))
    return render_template("verify.html", doc_id=doc_id, sig_ok=ok, expected_sig=expected, provided_sig=sig)


@app.route("/verify", methods=["POST"])
def verify_upload():
    doc_id = request.form.get("doc_id", "").strip()
    if "file" not in request.files or not request.files["file"]:
        flash("No file provided.", "error")
        return redirect(url_for("verify", id=doc_id, sig=request.form.get("sig", "")))

    file = request.files["file"]
    filename = secure_filename(file.filename or "")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        flash(f"Unsupported file type: {ext}", "error")
        return redirect(url_for("verify", id=doc_id, sig=request.form.get("sig", "")))

    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{filename}")
    file.save(save_path)

    uploaded_sha = sha256_file(save_path)
    db = load_db()  # dôležité: čítame vždy čerstvú DB zo súboru
    record = db.get(doc_id)
    if record and "sha256" in record:
        match = (uploaded_sha.lower() == record["sha256"].lower())
    else:
        match = False

    app.logger.info(f"[QRV] verify_upload doc_id={doc_id} present_in_db={doc_id in db} match={match}")
    return render_template(
        "result.html",
        doc_id=doc_id,
        uploaded_sha=uploaded_sha,
        record=record,
        match=match,
        file_name=filename
    )


# Nenápadný debug endpoint – užitočné po deploy (môžeš si nechať)
@app.route("/_debug")
def _debug():
    try:
        mtime = os.path.getmtime(DOCS_DB_PATH)
    except Exception:
        mtime = None
    db = load_db()
    return {
        "db_path": DOCS_DB_PATH,
        "docs_count": len(db),
        "doc_ids": list(db.keys()),
        "db_mtime": mtime,
        "upload_dir": UPLOAD_DIR,
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
