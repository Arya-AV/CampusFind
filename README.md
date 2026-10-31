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

## Database and local data storage

### Database location and persistence

CampusFind uses SQLite for local data storage. The SQLite database is stored in a file named `campusfind.db` located at the root of the project directory.

- **Persistence**: Because SQLite stores data in this local file, all newly created listings, status changes (such as marking an item as returned), and updates persist between application restarts. Stopping and restarting the Flask server does not wipe or overwrite your listings.
- **Git Ignore**: Per `.gitignore`, `campusfind.db` and uploaded images in `static/uploads/` (except `.gitkeep`) are excluded from version control so your local database entries and uploaded media are never accidentally committed.

### Database initialization and sample listings

The database is initialized automatically whenever the application is loaded or run (`init_db()` in `app.py` is invoked at startup):

1. **Table Creation**: `init_db()` establishes a connection to `campusfind.db` (creating the file automatically if it does not yet exist) and runs `CREATE TABLE IF NOT EXISTS items (...)` to ensure the required schema and table structure exist.
2. **Sample Data Seeding**:
   - The application checks the current number of rows in the `items` table using `SELECT COUNT(*) FROM items`.
   - **First Run**: If the count is `0` (an empty or freshly created database), the application automatically seeds four initial sample listings:
     - *Black Backpack* (Category: Bags, Status: Lost, Location: Central Library)
     - *Blue Water Bottle* (Category: Accessories, Status: Found, Location: Main Canteen)
     - *Student ID Card* (Category: ID Cards, Status: Found, Location: Electrical Department)
     - *Wireless Earbuds* (Category: Electronics, Status: Lost, Location: Lecture Hall 2)
   - **Subsequent Runs**: If the table already contains one or more records (`count > 0`), the seeding step is skipped to avoid inserting duplicate records or modifying existing data.

### Resetting local data safely

During development, you may want to reset the database back to its pristine default state with just the four sample listings.

> [!WARNING]
> **Warning**: Deleting or resetting the database removes all locally stored listings, reported items, and status changes permanently. If you have custom test entries or data you wish to keep, make a backup before proceeding.

Follow these step-by-step instructions to reset your local data safely:

1. **Stop the application server**:
   If the Flask development server is running in your terminal, stop it by pressing `Ctrl + C`.

2. **(Optional) Back up your current database**:
   If there is existing data you may want to preserve or restore later, copy `campusfind.db` to a backup file:
   - **Windows (PowerShell)**:
     ```powershell
     Copy-Item campusfind.db campusfind.db.bak
     ```
   - **macOS / Linux**:
     ```bash
     cp campusfind.db campusfind.db.bak
     ```

3. **Delete the database file (`campusfind.db`)**:
   Remove the local SQLite database file from the project root:
   - **Windows (PowerShell)**:
     ```powershell
     Remove-Item campusfind.db
     ```
   - **Windows (Command Prompt)**:
     ```cmd
     del campusfind.db
     ```
   - **macOS / Linux**:
     ```bash
     rm campusfind.db
     ```

4. **(Optional) Clean up uploaded images**:
   If you also want to remove locally uploaded item images while keeping the uploads directory tracked in Git:
   - **Windows (PowerShell)**:
     ```powershell
     Get-ChildItem static\uploads -Exclude .gitkeep | Remove-Item
     ```
   - **macOS / Linux**:
     ```bash
     find static/uploads -type f ! -name '.gitkeep' -delete
     ```

5. **Restart the application**:
   Start the application again:
   ```bash
   python app.py
   ```
   On startup, `init_db()` will automatically re-create `campusfind.db`, create the `items` table, and reseed the default four sample listings.

## Development notes

This is a learning/demo project, not a production deployment. Before deploying publicly, set a secure `SECRET_KEY`, add authentication and authorization, add CSRF protection, and review contact-data privacy and upload handling.

## License

MIT. See [LICENSE](LICENSE).
