from flask import Flask, request, jsonify
from flask_cors import CORS
from analyzer import run_analysis

app = Flask(__name__)
CORS(app)  # ← CMSから叩くため必須

@app.route("/")
def home():
    return "Site Audit API Running"

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json

        url = data.get("url")
        username = data.get("username")
        password = data.get("password")
        mode = data.get("mode", "IPP")

        if not url:
            return jsonify({"error": "URLがありません"}), 400

        results = run_analysis(url, username, password, mode)

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Render用
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)