# Contributing to CampusFind

Thanks for contributing!

## Workflow

1. Fork the repository on GitHub.
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/campusfind.git
   cd campusfind
   ```
3. Create a focused branch:
   ```bash
   git checkout -b fix/short-description
   ```
4. Create and activate a virtual environment, then install dependencies:
   ```bash
   python -m venv .venv
   pip install -r requirements.txt
   ```
5. Run the app with `python app.py` and test your change in the browser.
6. Run the tests with `python -m unittest discover -s tests -v`.
7. Commit and push:
   ```bash
   git add .
   git commit -m "fix: describe your change"
   git push origin fix/short-description
   ```
8. Open a pull request against the source repository's `main` branch. Include `Closes #ISSUE_NUMBER`, explain what changed, and attach a screenshot for visible changes.

## Guidelines

- Work on one issue per pull request.
- Keep changes focused and readable.
- Do not commit `.env`, local databases, uploaded images, virtual environments, or secrets.
- Describe how you tested the change.
- Be respectful and ask questions when an issue is unclear.
