import csv
import io
import json
from flask import Flask, render_template, request, redirect, url_for, Response, flash

from database import init_db, insert_course, list_courses, get_course, update_course, delete_course
from extractor import extract_course_data

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("course_url", "").strip()

        try:
            data = extract_course_data(url)
            return render_template("result.html", data=data)
        except Exception as e:
            flash(f"Could not extract data: {e}", "error")
            return redirect(url_for("index"))

    return render_template("index.html")


@app.route("/save", methods=["POST"])
def save():
    data = dict(request.form)
    data["raw_confidence_json"] = request.form.get("raw_confidence_json", "{}")
    data["raw_snippets_json"] = request.form.get("raw_snippets_json", "{}")
    data["verified_status"] = request.form.get("verified_status", "draft")

    new_id = insert_course(data)
    flash("Course saved successfully.", "success")
    return redirect(url_for("edit_course", course_id=new_id))


@app.route("/records")
def records():
    courses = list_courses()
    return render_template("records.html", courses=courses)


@app.route("/edit/<int:course_id>", methods=["GET", "POST"])
def edit_course(course_id):
    if request.method == "POST":
        update_course(course_id, dict(request.form))
        flash("Course updated successfully.", "success")
        return redirect(url_for("edit_course", course_id=course_id))

    course = get_course(course_id)
    if not course:
        flash("Course not found.", "error")
        return redirect(url_for("records"))

    try:
        confidence = json.loads(course["raw_confidence_json"] or "{}")
        snippets = json.loads(course["raw_snippets_json"] or "{}")
    except Exception:
        confidence = {}
        snippets = {}

    return render_template("edit.html", course=course, confidence=confidence, snippets=snippets)


@app.route("/delete/<int:course_id>", methods=["POST"])
def delete(course_id):
    delete_course(course_id)
    flash("Course deleted.", "success")
    return redirect(url_for("records"))


@app.route("/export.csv")
def export_csv():
    courses = list_courses()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id", "source_url", "university_name", "course_name", "country", "level",
        "tuition_fee", "currency", "ielts_requirement", "pte_requirement",
        "toefl_requirement", "duration", "intake", "application_fee",
        "deposit", "scholarship_info", "entry_requirement_snippet",
        "verified_status", "last_checked"
    ])

    for row in courses:
        writer.writerow([
            row["id"], row["source_url"], row["university_name"], row["course_name"],
            row["country"], row["level"], row["tuition_fee"], row["currency"],
            row["ielts_requirement"], row["pte_requirement"], row["toefl_requirement"],
            row["duration"], row["intake"], row["application_fee"], row["deposit"],
            row["scholarship_info"], row["entry_requirement_snippet"],
            row["verified_status"], row["last_checked"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=course_data_export.csv"}
    )


if __name__ == "__main__":
    app.run(debug=True)
