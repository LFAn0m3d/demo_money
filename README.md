# Money Guardian

Money Guardian is a Flask application that extracts information from bank slip images using Tesseract OCR.

## Installation

1. Create a virtual environment and activate it (optional).
2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

### System Dependencies

- **Tesseract OCR**: required for text extraction.
  - Ubuntu/Debian:
    ```bash
    sudo apt-get install tesseract-ocr
    ```
  - macOS (Homebrew):
    ```bash
    brew install tesseract
    ```
- **Poppler**: required by `pdf2image` to convert PDF files.
  - Ubuntu/Debian:
    ```bash
    sudo apt-get install poppler-utils
    ```
  - macOS (Homebrew):
    ```bash
    brew install poppler
    ```

Ensure the `tesseract` executable is in your `PATH`. On some systems you may need to specify the path in `pytesseract.pytesseract.tesseract_cmd`.

## Running the Application

1. Initialize the database if it does not exist:
   ```bash
   python app.py
   ```
   The app will automatically create `database.db` in the project directory.

2. Start the Flask development server:
   ```bash
   python app.py
   ```

   The application will be available at [http://localhost:5001](http://localhost:5001).

## File Uploads

Uploaded slip images are stored in the `uploads/` directory. The dashboard displays transactions extracted from these files.
Only image files (`.png`, `.jpg`, `.jpeg`) or PDF documents can be uploaded and files larger than the configured limit will be rejected.

## Configuration

The application reads several settings from environment variables:

- `UPLOAD_FOLDER` – directory for uploaded files (default: `uploads/`).
- `DB_URI` – SQLAlchemy database URI (default: `sqlite:///database.db`).
- `SECRET_KEY` – Flask secret key used for sessions.
- `MAX_CONTENT_LENGTH` – maximum allowed upload size in bytes (default: 5 MB).

If these variables are not provided the defaults above are used.

