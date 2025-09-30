import os
import hmac
import hashlib
import json
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename

# --- Config ---
HMAC_SECRET = os.getenv("QRV_HMAC_SECRET", "saxo-verify-9f4c2b7a1e84")  # set in Render env var
DOCS_DB_PATH = os.getenv("QRV_DOCS_DB", "docs_db.json")
UPLOAD_DIR = os.getenv("QRV_UPLOAD_DIR", "uploads")
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-me")  # for flash messages
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB
os.makedirs(UPLOAD_DIR, exist_ok=True)

def load_db():
    if not os.path.exists(DOCS_DB_PATH):
        return {}
    with open(DOCS_DB_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
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
        return redirect(url_for("verify", id=doc_id, sig=request.form.get("sig","")))
    file = request.files["file"]
    filename = secure_filename(file.filename or "")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        flash(f"Unsupported file type: {ext}", "error")
        return redirect(url_for("verify", id=doc_id, sig=request.form.get("sig","")))
    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{filename}")
    file.save(save_path)
    # Compute SHA256 of uploaded file
    uploaded_sha = sha256_file(save_path)
    db = load_db()
    record = db.get(doc_id)
    if record and "sha256" in record:
        match = (uploaded_sha.lower() == record["sha256"].lower())
    else:
        match = False
    return render_template("result.html", doc_id=doc_id, uploaded_sha=uploaded_sha, record=record, match=match, file_name=filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
