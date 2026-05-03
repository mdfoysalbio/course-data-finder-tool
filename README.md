# Course Data Finder Tool

A small internal admin tool for extracting course data from official university course pages.

## What it does

- Paste an official university course URL
- Extracts draft data:
  - Course name
  - University/domain
  - Tuition fee
  - IELTS requirement
  - PTE/TOEFL if found
  - Duration
  - Intakes
  - Application fee
  - Deposit
  - Scholarship mention
  - Entry requirement snippet
- Shows confidence level and source snippets
- Lets admin edit/verify data
- Saves records into SQLite database
- Exports verified data to CSV

## Install on Windows

Open CMD inside this folder and run:

```bash
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Important

Use official university pages as the source. Do not bulk-copy data from platforms like Studyportals, IDP, QS, or Hotcourses without permission.

This tool creates draft data only. Always review and verify before using it for student recommendations.
