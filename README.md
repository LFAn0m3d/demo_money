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

