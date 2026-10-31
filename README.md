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

| Method | Endpoint | Description | Parameters / Payload |
|---|---|---|---|
| `GET` | `/` | Browse and search lost/found listings | Query params: `q` (search term), `category` (category filter), `status` (`Lost`, `Found`, `Returned`), `sort` (`newest`, `oldest`) |
| `GET` | `/item/<item_id>` | View details of a specific item | URL param: `item_id` (integer). Returns 404 if not found. |
| `GET` | `/report` | Display the report form for lost or found items | None |
| `POST` | `/report` | Submit a report for a lost or found item | Form fields: `title`, `category`, `item_status`, `description`, `location`, `item_date`, `contact_name`, `contact_email`, optional `image` (multipart). Redirects to `/item/<id>` on success. |
| `POST` | `/item/<item_id>/returned` | Mark an existing found item as returned | URL param: `item_id` (integer). Returns 404 if item does not exist; redirects to `/item/<item_id>`. |

## Data and uploads

The local SQLite database (`campusfind.db`) and uploaded images are generated locally. They are excluded from Git. The app seeds four sample listings on its first run.

## Development notes

This is a learning/demo project, not a production deployment. Before deploying publicly, set a secure `SECRET_KEY`, add authentication and authorization, add CSRF protection, and review contact-data privacy and upload handling.

## License

MIT. See [LICENSE](LICENSE).
