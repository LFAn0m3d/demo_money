# Money Guardian

Money Guardian is a Flask application that extracts information from bank slip images using Tesseract OCR.

## Installation

1. Create a virtual environment and activate it (optional).
2. Install Python dependencies:

```bash
pip install -r requirements.txt
```
   The list includes `scikit-learn` and `tensorflow` which are required for the risk models.

3. Install the OCR system packages (`tesseract-ocr` and `poppler-utils`). These system tools are required by `pytesseract` and `pdf2image`.

### Required OCR System Packages

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

Ensure the `tesseract` executable is in your `PATH`. Alternatively set `TESSERACT_CMD` to the full executable path and the application will use it automatically.
If these packages are missing the upload page will display an error about missing OCR dependencies.

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

## Risk Scoring Models

Risk calculation combines an Isolation Forest and an Autoencoder model. Place trained model files in the `models/` directory as `isolation_forest.pkl` and `autoencoder.h5`. The application will fall back to a default score if the models or required machine learning libraries are unavailable.

## Configuration

The application reads several settings from environment variables:

- `UPLOAD_FOLDER` – directory for uploaded files (default: `uploads/`).
- `DB_URI` – SQLAlchemy database URI (default: `sqlite:///database.db`).
- `SECRET_KEY` – Flask secret key used for sessions.
- `MAX_CONTENT_LENGTH` – maximum allowed upload size in bytes (default: 5 MB).

If these variables are not provided the defaults above are used.

## Production Deployment

For a production environment run the Flask application with an application server such as **Gunicorn** or **uWSGI**. Place the server behind a reverse proxy (e.g. Nginx or Apache) and terminate TLS at the proxy.

### Example using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Example using uWSGI

```bash
uwsgi --http-socket 0.0.0.0:8000 --module app:app --master --processes 4 --threads 2
```

The reverse proxy should handle HTTPS and forward requests to the application server.
## Exporting Transactions

Users can download their transactions as a CSV file from the dashboard. Click the **"ดาวน์โหลด CSV"** button to export. Administrators receive all transactions while normal users only see their own.



## License

This project is licensed under the [MIT License](LICENSE).

