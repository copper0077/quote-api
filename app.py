import os
from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

@app.route("/api/generate-quote", methods=["POST"])
def generate_quote():
    import os
    print("ENV VARS:", dict(os.environ))  # 🔍 See what env vars are set

    docraptor_api_key = os.environ.get("DOCRAPTOR_API_KEY")
    print("DocRaptor API Key from env:", docraptor_api_key)

    ...

    # Extract data from the incoming JSON request
    data = request.get_json() or {}

    if not docraptor_api_key:
        return jsonify({"error": "Missing DocRaptor API key"}), 500

    html = render_template("fleet_quote_template.html", **data)

    response = requests.post(
        "https://docraptor.com/docs",
        auth=(docraptor_api_key, ""),
        json={
            "document_type": "pdf",
            "test": True,  # Set to False in production
            "name": f"{data.get('quote_number', 'quote')}.pdf",
            "document_content": html,
        },
    )

    if response.status_code != 200:
        return jsonify({"error": "DocRaptor failed", "details": response.text}), 500

    return jsonify({"pdf_url": response.json().get("download_url", "PDF created (test mode)")})
