import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from analyzer import run_analysis

app = Flask(__name__)
CORS(app)

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


# Railway対応（重要）
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
