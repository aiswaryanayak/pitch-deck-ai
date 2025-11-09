"""
AI Pitch Deck Generator (Gemini 2.0 + Local Presenton)
------------------------------------------------------
Fully self-hosted, free API for your Vercel frontend:
https://ai-fundraising-support.vercel.app
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import io
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from fpdf import FPDF
from presenton_core.app import presenton_app, generate_presentation as local_generate

# ---------------- FLASK APP ---------------- #
app = Flask(__name__)
CORS(app, origins=["https://ai-fundraising-support.vercel.app"])

# Register local Presenton simulation
app.register_blueprint(presenton_app)

# ---------------- CONFIG ---------------- #
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not set!")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# ---------------- GLOBAL MEMORY ---------------- #
last_generated_structure = None
last_company_info = None

# ---------------- SCRAPER ---------------- #
def fetch_company_info(url: str):
    """Extract company info from a given URL"""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.string if soup.title else "Untitled"
        description = (
            (soup.find("meta", {"name": "description"}) or {}).get("content", "")
        )

        print(f"✅ Scraped {url}: {title}")
        return {"url": url, "title": title, "description": description}

    except Exception as e:
        print(f"❌ Error fetching info: {str(e)}")
        return {"error": str(e)}

# ---------------- GEMINI STRUCTURE ---------------- #
def generate_pitch_deck(company_info):
    """Generate a 10-slide pitch deck in Markdown"""
    prompt = f"""
Create a 10-slide investor pitch deck in Markdown for:
Company: {company_info.get('title')}
Website: {company_info.get('url')}
Description: {company_info.get('description')}

Slides:
1. Title Slide
2. Problem
3. Solution
4. Market Opportunity
5. Business Model
6. Competitive Advantage
7. Go-to-Market Strategy
8. Financial Projections
9. Team
10. Funding Ask & Contact

Keep it concise, professional, and logically structured.
"""
    try:
        response = model.generate_content(prompt)
        print("✅ Gemini deck structure generated successfully.")
        return response.text.strip()
    except Exception as e:
        print(f"❌ Gemini Error: {str(e)}")
        return f"# Error generating structure: {str(e)}"

# ---------------- MAIN API ---------------- #
@app.route("/generate", methods=["POST"])
def generate_api():
    """Frontend endpoint to generate pitch decks"""
    global last_generated_structure, last_company_info

    try:
        data = request.get_json(force=True)
        company_url = data.get("url")

        if not company_url:
            return jsonify({"error": "Missing 'url' field"}), 400

        print(f"🚀 Generating pitch deck for {company_url}")
        company_info = fetch_company_info(company_url)
        if "error" in company_info:
            return jsonify({"error": company_info["error"]}), 400

        structure = generate_pitch_deck(company_info)

        print("🎨 Using internal Presenton simulation...")
        with app.test_request_context(json={
            "content": structure,
            "n_slides": 10,
            "export_as": "pdf"
        }):
            result = local_generate().get_json()

        # Save the latest generated output
        last_generated_structure = structure
        last_company_info = company_info

        return jsonify({
            "success": True,
            "company_info": company_info,
            "deck_structure": structure,
            "download_url": "https://pitch-deck-ai.onrender.com/downloads/latest.pdf",
            "edit_url": result.get("edit_path")
        })

    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ---------------- PDF GENERATOR ---------------- #
@app.route("/downloads/latest.pdf", methods=["GET"])
def download_generated_pdf():
    """Generate and return a downloadable PDF of the latest AI slides"""
    global last_generated_structure, last_company_info

    if not last_generated_structure or not last_company_info:
        return jsonify({"error": "No recent presentation found. Generate one first."}), 400

    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # ----------- Cover Slide ----------- #
        pdf.add_page()
        pdf.set_font("Arial", "B", 22)
        pdf.cell(0, 60, f"Pitch Deck for {last_company_info.get('title')}", ln=True, align="C")
        pdf.set_font("Arial", "", 14)
        pdf.multi_cell(0, 10, f"Website: {last_company_info.get('url')}\n\n{last_company_info.get('description', '')}", align="C")

        # ----------- Slides ----------- #
        slides = [s.strip() for s in last_generated_structure.split("\n\n") if s.strip()]
        total_slides = len(slides)

        for i, slide in enumerate(slides, start=1):
            pdf.add_page()
            lines = slide.split("\n")
            title = lines[0].strip("# ").strip()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, title, ln=True, align="C")
            pdf.ln(10)
            pdf.set_font("Arial", "", 12)
            for line in lines[1:]:
                pdf.multi_cell(0, 8, line)
            # Add slide number
            pdf.set_y(-20)
            pdf.set_font("Arial", "I", 10)
            pdf.cell(0, 10, f"Slide {i}/{total_slides}", 0, 0, "C")

        # ✅ Output to bytes (FPDF fix)
        pdf_bytes = pdf.output(dest="S").encode("latin1")

        print("✅ PDF generated successfully.")
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name="pitch_deck.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print(f"❌ PDF generation error: {str(e)}")
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500

# ---------------- ROOT ROUTE ---------------- #
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "✅ Free AI Pitch Deck Generator (Gemini 2.0 + Local Presenton) is live",
        "status": "running"
    })

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


