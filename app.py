from flask import Flask, send_file, jsonify, request
import os
import requests
from jinja2 import Environment, FileSystemLoader

app = Flask(__name__)

@app.route("/api/generate-quote", methods=["POST"])
def generate_quote():
    try:
        docraptor_api_key = os.environ.get("DOCRAPTOR_API_KEY")
        if not docraptor_api_key:
            return jsonify({"error": "Missing DocRaptor API key"}), 500

        data = request.get_json() or {}

        # 1. Render the HTML with Jinja2
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("quote_template.html")
        html_content = template.render(data)

        # 2. Send to DocRaptor (set test to False for real PDF)
        response = requests.post(
            "https://docraptor.com/docs",
            auth=(docraptor_api_key, ""),
            json={
                "document_content": html_content,
                "name": "quote.pdf",
                "document_type": "pdf",
                "test": False,  # 🔥 switch to False to get binary content
            },
            headers={"Content-Type": "application/json"}
        )

        # 3. Save binary PDF locally
        if response.status_code == 200:
            output_path = "quote.pdf"
            with open(output_path, "wb") as f:
                f.write(response.content)
            return send_file(output_path, as_attachment=True)
        else:
            print("❌ DocRaptor error response:", response.text)
            return jsonify({"error": "DocRaptor PDF generation failed", "details": response.text}), 500

    except Exception as e:
        import traceback
        print("🔥 ERROR:", str(e))
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error"}), 500

