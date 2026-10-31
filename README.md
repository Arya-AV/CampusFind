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

CampusFind implements the following HTTP routes:

### `GET /`
- **Endpoint**: `index`
- **Purpose**: Home page displaying the campus community board, aggregate listing statistics, search and filtering controls, and listing cards.
- **Query Parameters**:
  - `q` *(optional string)*: Case-insensitive search string matched against item `title`, `description`, or `location`.
  - `category` *(optional string)*: Filters listings by category. Valid options: `Electronics`, `ID Cards`, `Bags`, `Books`, `Clothing`, `Keys`, `Accessories`, `Other`. If omitted or invalid, listings from all categories are returned.
  - `status` *(optional string)*: Filters listings by status. Valid options: `Lost`, `Found`, `Returned`. If omitted or invalid, listings of all statuses are returned.
  - `sort` *(optional string)*: Specifies ordering:
    - `"newest"` (default): Sorted by date descending (`item_date DESC, id DESC`).
    - `"oldest"`: Sorted by date ascending (`item_date ASC, id DESC`).
- **Success Behavior**: Returns HTTP 200 and renders `templates/index.html` with matching listings, listing counts (`all`, `lost`, `found`, `returned`), and active filter selections.
- **Edge Cases**: When no items match the query or filters, an empty-state message is shown with a prompt to clear filters or view all listings.

---

### `GET /item/<int:item_id>`
- **Endpoint**: `item_detail`
- **Purpose**: Displays the complete details for a single listing, including title, category, status, date, location, description, contact details, image (or category icon placeholder), and return status actions.
- **URL Parameters**:
  - `item_id` *(integer, required)*: The database primary key ID of the item.
- **Success Behavior**: Returns HTTP 200 and renders `templates/detail.html` with the item record.
- **Error Cases**:
  - If no item matches `item_id`, triggers HTTP 404 via `abort(404)` and renders `templates/404.html`.
  - Non-integer `item_id` values are rejected by Flask's routing and return HTTP 404.

---

### `GET /report`
- **Endpoint**: `report_item`
- **Purpose**: Displays the form used to report a lost or found item.
- **Success Behavior**: Returns HTTP 200 and renders `templates/report.html` with an empty form and the current date as the default `item_date`.

---

### `POST /report`
- **Endpoint**: `report_item`
- **Purpose**: Validates submitted form fields and optional image upload, saves the uploaded image to disk, stores the new listing in SQLite, and redirects to the item's detail page.
- **Request Format**: `multipart/form-data`
- **Form Inputs**:
  - `title` *(string, required)*: Title/name of the item (1–100 characters).
  - `category` *(string, required)*: Selected category; must match one of the defined `CATEGORIES` (`Electronics`, `ID Cards`, `Bags`, `Books`, `Clothing`, `Keys`, `Accessories`, `Other`).
  - `item_status` *(string, required)*: Report type; must be either `"Lost"` or `"Found"`.
  - `description` *(string, required)*: Identifying details and clues (1–1,000 characters).
  - `location` *(string, required)*: Location where the item was lost or found (1–120 characters).
  - `item_date` *(ISO date string `YYYY-MM-DD`, required)*: Date when the item was lost or found. Must be a valid date and cannot be in the future.
  - `contact_name` *(string, required)*: Reporter's name (1–80 characters).
  - `contact_email` *(string, required)*: Reporter's email address (must contain `@`, max 120 characters).
  - `image` *(file, optional)*: Image file. Allowed extensions: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`. Maximum file size: 5 MB (`MAX_CONTENT_LENGTH`).
- **Success Behavior**:
  - If an image was uploaded, saves it to `static/uploads/` with a UUID-based filename (`<uuid>.<ext>`).
  - Inserts the new listing into SQLite.
  - Flashes a success message: `"Your item has been reported successfully."`.
  - Redirects (HTTP 302) to `GET /item/<int:item_id>` for the created item.
- **Error Cases**:
  - **Validation Errors**: If any input fails validation (missing required fields, strings exceeding length limits, invalid category or status, future date, invalid email format, disallowed image extension), flashes one or more error messages and re-renders `templates/report.html` (HTTP 200) with previously submitted values preserved.
  - **File Too Large (HTTP 413)**: If an upload exceeds 5 MB, Flask invokes the 413 error handler, flashes `"Image is too large. Maximum upload size is 5 MB."`, and redirects (HTTP 302) back to `/report`.

---

### `POST /item/<int:item_id>/returned`
- **Endpoint**: `mark_returned`
- **Purpose**: Marks an item listing as returned / reunited with its owner.
- **URL Parameters**:
  - `item_id` *(integer, required)*: The primary key ID of the item.
- **Success Behavior**:
  - Updates `item_status` to `'Returned'` in SQLite (if not already `'Returned'`).
  - Flashes a success message: `"Item marked as returned. Great news!"`.
  - Redirects (HTTP 302) back to `GET /item/<int:item_id>`.
- **Error Cases**:
  - If no item matches `item_id`, triggers HTTP 404 via `abort(404)` and renders `templates/404.html`.
  - Non-POST requests (e.g. `GET`) to this URL are rejected with HTTP 405 (Method Not Allowed).

---

### Application error handlers
- **404 Not Found** (`@app.errorhandler(404)`): Renders `templates/404.html` with HTTP 404 status when a requested page or item does not exist.
- **413 Request Entity Too Large** (`@app.errorhandler(413)`): Flashes an error message and redirects back to `/report` whenever an uploaded file exceeds the 5 MB limit.

## Data and uploads

The local SQLite database (`campusfind.db`) and uploaded images are generated locally. They are excluded from Git. The app seeds four sample listings on its first run.

## Development notes

This is a learning/demo project, not a production deployment. Before deploying publicly, set a secure `SECRET_KEY`, add authentication and authorization, add CSRF protection, and review contact-data privacy and upload handling.

## License

MIT. See [LICENSE](LICENSE).
