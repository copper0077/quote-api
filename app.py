from flask import Flask, jsonify, request
import os
import requests
from jinja2 import Environment, FileSystemLoader
import re

app = Flask(__name__)

# Util: Generate the next quote number
def get_next_quote_number():
    counter_file = "quote_counter.txt"
    prefix = "SAG-"
    suffix = "-AI"

    if not os.path.exists(counter_file):
        current = 1000
    else:
        with open(counter_file, "r") as f:
            current = int(f.read().strip())

    next_id = current + 1
    with open(counter_file, "w") as f:
        f.write(str(next_id))

    return f"{prefix}{next_id}{suffix}"

# Util: Sanitize customer name for filename
def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

@app.route("/api/generate-quote", methods=["POST"])
def generate_quote():
    try:
        docraptor_api_key = os.environ.get("DOCRAPTOR_API_KEY")
        if not docraptor_api_key:
            return jsonify({"error": "Missing DocRaptor API key"}), 500

        data = request.get_json() or {}

        # Generate or override quote number
        quote_number = get_next_quote_number()
        data["quoteNumber"] = quote_number

        # Sanitize filename from customer + quote number
        customer_name = data.get("customer", "Unnamed_Customer")
        safe_name = sanitize_filename(customer_name)
        filename = f"{safe_name}_{quote_number}.pdf"

        # Render HTML from Jinja template
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("fleet_quote_template.html")
        html_content = template.render(data)

        # Call DocRaptor with async mode
        response = requests.post(
            "https://docraptor.com/docs",
            auth=(docraptor_api_key, ""),
            json={
                "doc": {
                    "document_content": html_content,
                    "name": filename,
                    "document_type": "pdf",
                    "test": False,
                    "async": True
                }
            },
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            resp_json = response.json()
            download_url = resp_json.get("download_url")
            if download_url:
                return jsonify({"downloadUrl": download_url})
            else:
                return jsonify({"error": "DocRaptor returned no download URL"}), 500
        else:
            print("❌ DocRaptor error:", response.text)
            return jsonify({"error": "DocRaptor PDF generation failed", "details": response.text}), 500

    except Exception as e:
        import traceback
        print("🔥 ERROR:", str(e))
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error"}), 500
