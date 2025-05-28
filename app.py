import os
from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

@app.route("/api/generate-quote", methods=["POST"])
def generate_quote():
    print("DocRaptor API Key from env:", docraptor_api_key)
    data = request.json

    html = render_template("fleet_quote_template.html", **data)

    docraptor_api_key = os.environ.get("EeI9dejUc2V-gqqHpxpi")
    if not docraptor_api_key:
        return jsonify({"error": "Missing DocRaptor API key"}), 500
    data = request.json

    html = render_template("fleet_quote_template.html", **data)

    docraptor_api_key = os.environ.get("DOCRAPTOR_API_KEY")
    print("DocRaptor API Key from env:", docraptor_api_key)  # 👈 Add this line

    if not docraptor_api_key:
        return jsonify({"error": "Missing DocRaptor API key"}), 500

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
