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

## Application routes

| Route | HTTP method | Description |
|---|---|---|
| `/` | GET | Displays all reported items. Supports searching by title, description, or location, filtering by category and status, and sorting by date. |
| `/item/<int:item_id>` | GET | Displays the details of a specific item. Returns a 404 page if the item does not exist. |
| `/report` | GET | Displays the form for reporting a lost or found item. |
| `/report` | POST | Validates the submitted item details, optionally saves an uploaded image, stores the report in the SQLite database, and redirects to its detail page. |
| `/item/<int:item_id>/returned` | POST | Marks the specified item as returned and redirects to its detail page. |

### Error handling

- **404:** Displays a custom page when a requested item or route is not found.
- **413:** Handles image uploads exceeding the configured maximum request size.

## Project structure

```text
CampusFind/
│
├── app.py                  # Flask application, routes, database operations
├── campusfind.db           # Local SQLite database (generated locally)
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── CONTRIBUTING.md         # Contribution guidelines
├── LICENSE                 # MIT License
│
├── templates/              # HTML templates rendered by Flask
│   ├── base.html           # Shared page layout
│   ├── index.html          # Homepage and item listings
│   ├── detail.html         # Individual item details
│   ├── report.html         # Lost/found item reporting form
│   └── 404.html            # Custom not-found page
│
├── static/
│   ├── css/
│   │   └── styles.css      # Application styling
│   ├── js/
│   │   └── app.js          # Client-side JavaScript
│   └── uploads/            # Uploaded item images
│
├── tests/
│   └── test_app.py         # Automated application tests
│
└── .github/
    └── pull_request_template.md

## Database and data persistence

CampusFind uses SQLite to store reported items.

### Database setup

The database file is named `campusfind.db` and is located in the project root directory.

The database is initialized automatically when `app.py` runs. The application creates the `items` table if it does not already exist.

On the first initialization, if the table is empty, four sample listings are inserted automatically.

You do not need to install or configure a separate database server.

### Data persistence

The SQLite database stores item information, including:

- Item title and category
- Lost, Found, or Returned status
- Description and location
- Date the item was lost or found
- Contact name and email
- Uploaded image filename
- Record creation timestamp

Data is stored locally in `campusfind.db` and remains available when the Flask application is restarted.

Uploaded images are stored separately in `static/uploads/`.

Both the database and uploaded images are excluded from Git and are generated locally.

### Resetting the database

To reset the local database and restore the four sample listings:

1. Stop the Flask application using `Ctrl + C` in the terminal.
2. Delete the `campusfind.db` file from the project root directory.
3. Restart the application:

```bash
python app.py

## Running automated tests

CampusFind uses Python's built-in `unittest` framework and Flask's test client.

Make sure you are in the project's root directory and have activated your virtual environment.

Install the project dependencies:

```bash
pip install -r requirements.txt

## Development notes

This is a learning/demo project, not a production deployment. Before deploying publicly, set a secure `SECRET_KEY`, add authentication and authorization, add CSRF protection, and review contact-data privacy and upload handling.

## License

MIT. See [LICENSE](LICENSE).
