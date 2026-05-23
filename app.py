from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash
import json

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)
app.config["SECRET_KEY"] = "replace-with-a-secure-secret"


def load_json(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as file:
        return json.load(file)


courses = load_json("courses.json")
roadmap = load_json("roadmap.json")
testimonials = load_json("testimonials.json")

contact = {
    "phone": "+91 97982-53860",
    "email": "info@devopsacademy.co",
    "address": "BTM Layout, Bengaluru, Karnataka 560076",
    "website": "www.devopsacademy.co",
}


@app.route("/")
def home():
    return render_template(
        "index.html",
        courses=courses,
        roadmap=roadmap,
        testimonials=testimonials,
        contact=contact,
    )


@app.route("/apply", methods=["POST"])
def apply():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email:
        flash("Name and email are required. Please complete the form.", "error")
        return redirect(url_for("home") + "#enroll")

    flash("Thank you! Your enrollment request has been received.", "success")
    app.logger.info("Enrollment request: %s, %s, %s, %s", name, email, phone, message)
    return redirect(url_for("home") + "#enroll")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
