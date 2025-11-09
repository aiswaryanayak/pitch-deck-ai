from flask import Blueprint, request, jsonify
import time

presenton_app = Blueprint("presenton_app", __name__)

@presenton_app.route("/api/v1/ppt/presentation/generate", methods=["POST"])
def generate_presentation():
    """Local simulation of Presenton API – no external call, no payment."""
    data = request.get_json() or {}
    content = data.get("content", "")
    n_slides = data.get("n_slides", 10)
    export_as = data.get("export_as", "pdf")

    print("🎨 Local Presenton generator called!")

    # Simulate slide creation delay
    time.sleep(2)

    fake_id = str(int(time.time()))
    return jsonify({
        "success": True,
        "presentation_id": fake_id,
        "path": f"/downloads/{fake_id}.{export_as}",
        "edit_path": f"/edit/{fake_id}"
    })

