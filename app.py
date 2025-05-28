from flask import Flask, jsonify, request
import os
import requests
from jinja2 import Environment, FileSystemLoader
import re
import time

app = Flask(__name__)

# Generate the next quote number
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

# Sanitize customer name for filename
def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

@app.route("/api/generate-quote", methods=["POST"])
def generate_quote():
    try:
        docraptor_api_key = os.environ.get("DOCRAPTOR_API_KEY")
        if not docraptor_api_key:
            return jsonify({"error": "Missing DocRaptor API key"}), 500

        data = request.get_json() or {}

        # Generate quote number
        quote_number = get_next_quote_number()
        data["quoteNumber"] = quote_number

        # Create sanitized filename
        customer_name = data.get("customer", "Unnamed_Customer")
        safe_name = sanitize_filename(customer_name)
        filename = f"{safe_name}_{quote_number}.pdf"

        # Render HTML from template
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("fleet_quote_template.html")
        html_content = template.render(data)

        # Step 1: Submit DocRaptor async job
        create_resp = requests.post(
            "https://docraptor.com/async_docs",
            auth=(docraptor_api_key, ""),
            json={
                "test": False,
                "document_type": "pdf",
                "name": filename,
                "document_content": html_content
            },
            headers={"Content-Type": "application/json"}
        )

        if create_resp.status_code != 200:
            return jsonify({"error": "DocRaptor job submission failed", "details": create_resp.text}), 500

        job_data = create_resp.json()
        print("📦 DocRaptor response:", job_data)

        status_id = job_data.get("status_id")
        if not status_id:
            return jsonify({"error": "DocRaptor did not return a status_id", "docraptor_response": job_data}), 500

        # Step 2: Poll for download_url
        for _ in range(5):
            time.sleep(2)  # Wait 2 seconds between attempts
            poll_resp = requests.get(
                f"https://docraptor.com/status/{status_id}",
                auth=(docraptor_api_key, "")
            )
            if poll_resp.status_code != 200:
                continue

            poll_data = poll_resp.json()
            print("🔁 Polling result:", poll_data)
            if download_url := poll_data.get("download_url"):
                return jsonify({"downloadUrl": download_url})

        return jsonify({"error": "DocRaptor timed out before returning a download URL"}), 504

    except Exception as e:
        import traceback
        print("🔥 ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error"}), 500
