# CampusFind

CampusFind is a campus lost-and-found portal built with Python, Flask, SQLite, HTML, CSS, and JavaScript. Students can report lost or found items, search listings, filter by category/status, view item details, and mark an item as returned.

## Features

- Browse lost, found, and returned items
- Search titles, descriptions, and locations
- Filter by category and status
- Sort listings by date
- User authentication with encrypted passwords
- Report a lost or found item with contact details
- Optional image upload (PNG, JPG, JPEG, GIF, WEBP; maximum 5 MB)
- Mark an item as returned (strict post ownership authorization)
- Recently viewed items section on homepage for logged-in users
- SQLite database is created automatically with sample listings
- Responsive layout and friendly empty/error states

## Requirements

- Python 3.10 or newer
- pip

## Configuration and Environment Variables

CampusFind uses environment variables to configure sensitive settings like the Flask secret key and debug mode. Real secrets are kept out of version control.

### Available Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Secret key used for cryptographic session signing and cookie integrity. | Ephemeral random key generated at runtime |
| `FLASK_DEBUG` | Enable Flask debug mode (`1`, `true`, or `development`). | `0` (Disabled by default) |
| `HOST` / `FLASK_RUN_HOST` | Host address to bind the development server to. | `127.0.0.1` |
| `PORT` / `FLASK_RUN_PORT` | Port number to bind the development server to. | `5000` |

### Local Environment Setup

1. Copy the example configuration file:
   ```bash
   cp .env.example .env
   ```

2. Generate a secure random secret key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Paste the generated key into your `.env` file:
   ```env
   SECRET_KEY=your_generated_secret_key_here
   FLASK_DEBUG=1
   ```

> [!NOTE]
> If `SECRET_KEY` is not provided in your environment or `.env` file, the application handles it safely by generating an ephemeral cryptographic key at startup for local development. In production environments, always set `SECRET_KEY` explicitly. Debug mode is disabled by default and will only be activated when `FLASK_DEBUG` is explicitly set to `1` or `true`.

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

## Running Tests

To run the full automated test suite:

```bash
python -m unittest discover -s tests -v
```

## Data and uploads

The local SQLite database (`campusfind.db`) and uploaded images are generated locally. They are excluded from Git. The app seeds four sample listings on its first run.

## License

MIT. See [LICENSE](LICENSE).
