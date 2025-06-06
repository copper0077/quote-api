from flask import Flask, jsonify, request, render_template
import os
import requests
import time
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta
import json
import pprint
import re


def log_quote_to_google_sheets(data):
    """Append basic quote info to a Google Sheet if env vars are configured."""
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    access_token = os.environ.get("GOOGLE_SHEETS_TOKEN")
    range_name = os.environ.get("SHEETS_RANGE", "Sheet1!A1")
    if not spreadsheet_id or not access_token:
        # Skip logging if configuration is missing
        print("Google Sheets logging skipped: missing credentials")
        return

    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/"
        f"{range_name}:append?valueInputOption=USER_ENTERED"
    )
    body = {
        "values": [
            [
                data.get("quoteNumber"),
                data.get("customer"),
                data.get("grandTotal"),
                data.get("quoteDate"),
            ]
        ]
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            print("Google Sheets logging failed:", resp.text)
    except Exception as e:
        print("Error logging to Google Sheets:", e)

app = Flask(__name__)

@app.route("/api/generate-quote", methods=["POST"])
def generate_quote():
    try:
        docraptor_api_key = os.environ.get("DOCRAPTOR_API_KEY")
        if not docraptor_api_key:
            return jsonify({"error": "Missing DocRaptor API key"}), 500

        # Parse JSON with fallback
        data = request.get_json(silent=True) or json.loads(request.data)

        # Debug log
        print("\n========== RAW PAYLOAD ==========")
        print(request.data.decode("utf-8"))
        print("========== JSON PARSED ==========")
        pprint.pprint(data)
        print("========== END DEBUG ==========\n")

        # Set dates if missing
        if not data.get("quoteDate"):
            data["quoteDate"] = datetime.now().strftime("%Y-%m-%d")
        if not data.get("quoteExpires"):
            data["quoteExpires"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        # Generate quote number
        if not data.get("quoteNumber"):
            counter_path = "quote_counter.txt"
            current = 1000
            if os.path.exists(counter_path):
                with open(counter_path, "r") as f:
                    current = int(f.read().strip())
            data["quoteNumber"] = f"SAG-{current}-AI"
            with open(counter_path, "w") as f:
                f.write(str(current + 1))

        # Grand total
        grand_total = sum(v.get("totalPrice", 0) for v in data.get("vehicles", []))
        for u in data.get("upgrades", []):
            grand_total += u.get("total", 0)
        if data.get("transport"):
            grand_total += data["transport"].get("total", 0)
        if data.get("upfitter"):
            grand_total += data["upfitter"].get("total", 0)
        data["grandTotal"] = grand_total

        # Log to Google Sheets if configured
        log_quote_to_google_sheets(data)

        # Render HTML
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("fleet_quote_template.html")
        html_content = template.render(data)

        # Submit to DocRaptor
        safe_customer = re.sub(r'[^A-Za-z0-9_-]+', '_', data['customer']).strip('_')
        filename = f"{safe_customer}_{data['quoteNumber']}.pdf"
        create_resp = requests.post(
            "https://docraptor.com/async_docs",
            auth=(docraptor_api_key, ""),
            json={
                "test": False,
                "document_type": "pdf",
                "name": filename,
                "document_content": html_content,
                "async": True
            },
            headers={"Content-Type": "application/json"}
        )

        job_data = create_resp.json()
        status_id = job_data.get("status_id")
        if not status_id:
            return jsonify({"error": "DocRaptor did not return a valid status_id", "response": job_data}), 500

        return jsonify({
            "quoteNumber": data["quoteNumber"],
            "statusId": status_id,
            "filename": filename
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/api/quote-status/<status_id>", methods=["GET"])
def quote_status(status_id):
    try:
        docraptor_api_key = os.environ.get("DOCRAPTOR_API_KEY")
        if not docraptor_api_key:
            return jsonify({"error": "Missing DocRaptor API key"}), 500

        response = requests.get(
            f"https://docraptor.com/status/{status_id}",
            auth=(docraptor_api_key, "")
        )
        status_json = response.json()

        return jsonify({
            "done": status_json.get("done", False),
            "download_url": status_json.get("download_url"),
            "status": status_json.get("status"),
            "number_of_pages": status_json.get("number_of_pages")
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to check status", "details": str(e)}), 500


@app.route("/")
def index():
    """Serve a basic interface for generating quotes."""
    return render_template("index.html")
