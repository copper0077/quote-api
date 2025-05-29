from flask import Flask, jsonify, request
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

        # Fill default dates
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

        # Calculate grand total
        vehicles_total = sum(v.get("totalPrice", 0) for v in data.get("vehicles", []))
        upgrades_total = sum(u.get("total", 0) for u in data.get("upgrades", []))
        upfitter_total = data.get("upfitter", {}).get("total", 0)
        transport_total = data.get("transport", {}).get("total", 0)

        grand_total = vehicles_total + upgrades_total + upfitter_total + transport_total
        data["grandTotal"] = grand_total

        # Optional: pass subtotals into the template
        data["totals"] = {
            "vehicles": vehicles_total,
            "upgrades": upgrades_total,
            "upfitter": upfitter_total,
            "transport": transport_total
        }

        # Render HTML using Jinja2
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("fleet_quote_template.html")
        html_content = template.render(data)

        # Generate PDF asynchronously via DocRaptor
        filename = f"{data['customer'].replace(' ', '_')}_{data['quoteNumber']}.pdf"
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

        poll_url = f"https://docraptor.com/status/{status_id}"
        status_resp = requests.get(poll_url, auth=(docraptor_api_key, ""))
        return jsonify(status_resp.json())

    except Exception as e:
        return jsonify({"error": "Failed to get job status", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
