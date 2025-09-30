
from flask import Flask, render_template, request
import json, os, hashlib, datetime, argparse, sys

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "db.json")

def load_db():
    if not os.path.exists(DB_PATH):
        return {"issuer":{"name":"Demo Issuer, Ltd.","created_at":datetime.datetime.utcnow().isoformat()+"Z"}, "documents":{}}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def register_pdf(pdf_path, title="Registered Document"):
    db = load_db()
    sha = sha256_of(pdf_path)
    doc_id = "demo-" + sha[:8]
    db["documents"][doc_id] = {
        "doc_id": doc_id,
        "sha256": sha,
        "issued_at": datetime.datetime.utcnow().isoformat()+"Z",
        "revoked_at": None,
        "title": title,
        "pages": 1,
        "scans": 0
    }
    save_db(db)
    return doc_id, sha

app = Flask(__name__)

@app.route("/")
def index():
    db = load_db()
    docs = list(db.get("documents", {}).values())
    return render_template("index.html", docs=docs, issuer=db.get("issuer", {}))

@app.route("/d/<doc_id>", methods=["GET", "POST"])
def verify(doc_id):
    db = load_db()
    doc = db["documents"].get(doc_id)
    if not doc:
        return render_template("not_found.html", doc_id=doc_id), 404

    if request.method == "GET":
        doc["scans"] = int(doc.get("scans", 0)) + 1
        save_db(db)

    result, uploaded_hash = None, None
    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename.lower().endswith(".pdf"):
            content = file.read()
            uploaded_hash = hashlib.sha256(content).hexdigest()
            result = "exact" if uploaded_hash.lower() == doc["sha256"].lower() else "mismatch"
        else:
            result = "invalid_upload"

    issuer = db.get("issuer", {})
    return render_template("verify.html", issuer=issuer, doc=doc, result=result, uploaded_hash=uploaded_hash)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", metavar="PDF_PATH", help="Register a PDF into the verifier DB and print its Doc ID.")
    args = parser.parse_args()
    if args.init:
        if not os.path.exists(args.init):
            print(f"File not found: {args.init}", file=sys.stderr); sys.exit(1)
        doc_id, sha = register_pdf(args.init, title=os.path.basename(args.init))
        print(f"Registered.\nDoc ID: {doc_id}\nSHA-256: {sha}")
    else:
        app.run(host="0.0.0.0", port=5000)
