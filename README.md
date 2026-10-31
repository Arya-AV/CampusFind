# CampusFind

CampusFind is a campus lost-and-found portal built with Python, Flask, SQLite, HTML, CSS, and JavaScript. Students can report lost or found items, search listings, filter by category/status, view item details, and mark an item as returned.

## Features

- Browse lost, found, and returned items
- Search titles, descriptions, and locations
- Filter by category and status
- Sort listings by date
- Report a lost or found item with contact details
- Optional image upload (PNG, JPG, JPEG, GIF, WEBP; maximum 5 MB)
- Mark an item as returned
- SQLite database is created automatically with sample listings
- Responsive layout and friendly empty/error states

## Requirements

- Python 3.10 or newer
- pip

## Run locally

```bash
python -m venv .venv
```

Activate the environment:

**Windows**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS/Linux**
```bash
source .venv/bin/activate
```

Install dependencies and run:

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Running tests

CampusFind uses Python's built-in `unittest` framework with isolated temporary databases.

### Prerequisites
Ensure dependencies are installed in your virtual environment:
```bash
pip install -r requirements.txt
```

### Run the test suite
Execute the test runner from the repository root:
```bash
python -m unittest discover -s tests -v
```

### Understanding test results
- Each test displays `... ok` when passing.
- A final line showing `OK` confirms all tests passed.
- A failed test will show `FAIL` or `ERROR` along with a traceback.

### Troubleshooting
- **ModuleNotFoundError: No module named 'flask'**: Make sure the virtual environment is activated before running the command.
- **ImportError: No module named 'app'**: Ensure you are running the test command from the repository root directory.

## Data and uploads

The local SQLite database (`campusfind.db`) and uploaded images are generated locally. They are excluded from Git. The app seeds four sample listings on its first run.

## Development notes

This is a learning/demo project, not a production deployment. Before deploying publicly, set a secure `SECRET_KEY`, add authentication and authorization, add CSRF protection, and review contact-data privacy and upload handling.

## License

MIT. See [LICENSE](LICENSE).
