from flask import Flask, send_file, jsonify, request
import os
import requests
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route("/api/generate-quote", methods=["POST"])
def generate_quote():
    try:
        docraptor_api_key = os.environ.get("DOCRAPTOR_API_KEY")
        if not docraptor_api_key:
            return jsonify({"error": "Missing DocRaptor API key"}), 500

        data = request.get_json() or {}

        # Auto-generate quote number if not provided
        if not data.get("quoteNumber"):
            counter_path = "quote_counter.txt"
            current = 1001
            if os.path.exists(counter_path):
                with open(counter_path, "r") as f:
                    current = int(f.read().strip())
            quote_number = f"SAG-{current}-AI"
            data["quoteNumber"] = quote_number
            with open(counter_path, "w") as f:
                f.write(str(current + 1))
        else:
            quote_number = data["quoteNumber"]

        # Auto-fill quote date and expiration
        if not data.get("quoteDate"):
            data["quoteDate"] = datetime.now().strftime("%Y-%m-%d")
        if not data.get("quoteExpires"):
            data["quoteExpires"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        # Compute grandTotal
        grand_total = sum(v.get("totalPrice", 0) for v in data.get("vehicles", []))
        for u in data.get("upgrades", []):
            grand_total += u.get("total", 0)
        if data.get("transport"):
            grand_total += data["transport"].get("total", 0)
        if data.get("tradeIn"):
            grand_total -= data["tradeIn"].get("allowance", 0)
        data["grandTotal"] = round(grand_total, 2)

        # Render HTML from template
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("fleet_quote_template.html")
        html_content = template.render(data)

        # Build safe filename
        customer_clean = data.get("customer", "Quote").replace(" ", "_").replace(",", "")
        filename = f"{customer_clean}_{quote_number}.pdf"

        # Send to DocRaptor
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
            return jsonify({"error": "DocRaptor did not return a document ID", "docraptor_response": job_data}), 500

        # Poll for completion (synchronously)
        for _ in range(20):
            status_resp = requests.get(
                f"https://docraptor.com/status/{status_id}",
                auth=(docraptor_api_key, "")
            )
            status = status_resp.json()
            if status.get("status") == "completed":
                download_url = status.get("download_url")
                return jsonify({
                    "downloadUrl": download_url,
                    "quoteNumber": quote_number
                })
            elif status.get("status") == "failed":
                return jsonify({"error": "DocRaptor job failed", "details": status}), 500

        return jsonify({"error": "Timeout waiting for DocRaptor", "statusId": status_id}), 504

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
