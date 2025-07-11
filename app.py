### app.py (Production-ready Enhancements with CSRF)

from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, make_response
import os, re
import csv
import io
import cv2
import pytesseract
import magic
from uuid import uuid4
from werkzeug.utils import secure_filename
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from pdf2image import convert_from_path


class OCRDependencyError(Exception):
    """Raised when system OCR dependencies are missing."""
    pass
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import CSRFProtect  # ✅ เพิ่ม CSRF protection
from risk_model import calculate_risk

# === CONFIG ===
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
DB_PATH = os.getenv('DB_URI', 'sqlite:///database.db')
SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/jpg', 'application/pdf'
}
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 5 * 1024 * 1024))  # 5MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = SECRET_KEY
csrf = CSRFProtect(app)  # ✅ ใช้งาน CSRF

# === DATABASE MODEL ===
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    email = Column(String, unique=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    sender = Column(String)
    receiver = Column(String)
    amount = Column(Float)
    date_str = Column(String)
    raw_text = Column(String)
    risk_score = Column(Float)
    filename = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(DB_PATH)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def parse_amount(raw):
    """Convert extracted amount string to a float."""
    if not raw:
        return None
    try:
        return float(raw.replace(',', ''))
    except Exception:
        return None

# === OCR Utility ===
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_slip_with_tesseract(image_path):
    temp_path = None
    try:
        path_to_read = image_path
        if image_path.lower().endswith('.pdf'):
            try:
                images = convert_from_path(image_path, dpi=300)
            except Exception as e:
                raise OCRDependencyError(
                    "Poppler is required to handle PDF files. Please install poppler-utils."
                ) from e
            if not images:
                return {}
            temp_path = image_path + '_tmp.png'
            images[0].save(temp_path, 'PNG')
            path_to_read = temp_path

        img = cv2.imread(path_to_read)
        if img is None:
            return {}
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 10
        )
        config = r'--oem 3 --psm 6 -l tha+eng'
        try:
            text = pytesseract.image_to_string(thresh, config=config)
        except Exception as e:
            raise OCRDependencyError(
                "Tesseract OCR is required for text extraction. Please ensure it is installed and in your PATH."
            ) from e
        return extract_transaction_info(text)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

def extract_transaction_info(text):
    data = {}
    try: data['from_account'] = re.search(r'จากบัญชี[:\s]+([\d\-]+)', text).group(1)
    except: data['from_account'] = None
    try: data['to_account'] = re.search(r'ไปยังบัญชี[:\s]+([\d\-]+)', text).group(1)
    except: data['to_account'] = None
    try: data['sender_name'] = re.search(r'ชื่อผู้โอน[:\s]+(.+)', text).group(1).strip()
    except: data['sender_name'] = None
    try: data['receiver_name'] = re.search(r'ชื่อผู้รับ[:\s]+(.+)', text).group(1).strip()
    except: data['receiver_name'] = None
    try: data['bank_name'] = re.search(r'ธนาคาร[:\s]+(.+)', text).group(1).strip()
    except: data['bank_name'] = None
    try: data['date'] = re.search(r'วันที่[:\s]+([\d/]+)', text).group(1)
    except: data['date'] = None
    try: data['time'] = re.search(r'เวลา[:\s]+([\d:]+)', text).group(1)
    except: data['time'] = None
    try:
        data['amount'] = re.search(r'จำนวนเงิน[:\s]+([\d,\.]+)', text).group(1)
    except Exception:
        data['amount'] = None
    data['raw_text'] = text
    return data

# === ROUTES ===
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    result = {}
    error_msg = None
    if request.method == 'POST':
        if 'file' not in request.files:
            error_msg = 'ไม่พบไฟล์ที่อัปโหลด'
        else:
            file = request.files['file']
            if file.filename == '':
                error_msg = 'ไม่ได้เลือกไฟล์'
            elif not allowed_file(file.filename):
                error_msg = 'ประเภทไฟล์ไม่รองรับ'
            else:
                mime_type = magic.from_buffer(file.stream.read(2048), mime=True)
                file.stream.seek(0)
                if mime_type not in ALLOWED_MIME_TYPES:
                    error_msg = 'ประเภทไฟล์ไม่รองรับ'

        if error_msg is None:
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid4().hex}_{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)

            try:
                data = process_slip_with_tesseract(filepath)
            except OCRDependencyError as e:
                os.remove(filepath)
                error_msg = str(e)
                data = None
            if data is not None and error_msg is None:
                risk_score = calculate_risk(data)
                user_id = session.get("user_id")

                amount_val = parse_amount(data.get("amount"))

                with Session() as session_db:
                    tx = Transaction(
                        user_id=user_id,
                        sender=data.get("sender_name"),
                        receiver=data.get("receiver_name"),
                        amount=amount_val,
                        date_str=data.get("date"),
                        raw_text=data.get("raw_text"),
                        risk_score=risk_score,
                        filename=unique_filename
                    )
                    session_db.add(tx)
                    session_db.commit()

                result = {
                    'filename': unique_filename,
                    'risk_score': risk_score,
                    'amount': data.get('amount'),
                    'date': data.get('date'),
                    'time': data.get('time'),
                    'bank_name': data.get('bank_name'),
                    'sender_name': data.get('sender_name'),
                    'receiver_name': data.get('receiver_name'),
                    'from_account': data.get('from_account'),
                    'to_account': data.get('to_account'),
                    'raw_text': data.get('raw_text')
                }

    return render_template('index.html', result=result, error=error_msg)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    is_admin = session.get('is_admin')
    with Session() as session_db:
        if is_admin:
            transactions = session_db.query(Transaction).order_by(Transaction.created_at.desc()).all()
        else:
            transactions = session_db.query(Transaction).filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).all()
    return render_template('dashboard.html', transactions=transactions)


@app.route('/export')
def export_transactions():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    is_admin = session.get('is_admin')
    with Session() as session_db:
        if is_admin:
            transactions = session_db.query(Transaction).order_by(Transaction.created_at.desc()).all()
        else:
            transactions = session_db.query(Transaction).filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['date', 'sender', 'receiver', 'amount', 'risk_score'])
    for tx in transactions:
        writer.writerow([
            tx.date_str or '',
            tx.sender or '',
            tx.receiver or '',
            tx.amount or '',
            tx.risk_score or ''
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=transactions.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    user_id = session.get("user_id")
    with Session() as session_db:
        tx = session_db.query(Transaction).filter_by(filename=filename).first()
        user = session_db.query(User).filter_by(id=user_id).first()

    if not tx:
        return "ไม่พบสลิปนี้", 404
    if user is None or (not user.is_admin and tx.user_id != user.id):
        return "คุณไม่มีสิทธิ์เข้าถึงไฟล์นี้", 403

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/user')
def user_list():
    user_id = session.get("user_id")
    with Session() as session_db:
        user = session_db.query(User).filter_by(id=user_id).first()
        if not user or not user.is_admin:
            return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
        users = session_db.query(User).order_by(User.created_at.desc()).all()
    return render_template("user.html", users=users, is_admin=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']  # ✅ บังคับให้ต้องมีอีเมล
        if not email:
            return 'กรุณากรอกอีเมล'
        hashed_pw = generate_password_hash(password)
        with Session() as session_db:
            existing_user = session_db.query(User).filter_by(username=username).first()
            if existing_user:
                return 'Username already exists!'
            new_user = User(username=username, password=hashed_pw, email=email, is_admin=False)
            session_db.add(new_user)
            session_db.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with Session() as session_db:
            user = session_db.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# === RUN ===
if __name__ == '__main__':
    app.run(debug=True, port=5001)
