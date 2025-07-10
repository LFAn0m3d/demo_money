### app.py (Production-ready Enhancements with CSRF)

from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os, random, re
import cv2
import pytesseract
from uuid import uuid4
from werkzeug.utils import secure_filename
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from pdf2image import convert_from_path
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import CSRFProtect  # ✅ เพิ่ม CSRF protection

# === CONFIG ===
UPLOAD_FOLDER = 'uploads'
DB_PATH = 'sqlite:///database.db'
SECRET_KEY = 'supersecretkey'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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

# === OCR Utility ===
def process_slip_with_tesseract(image_path):
    img = cv2.imread(image_path)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 10
    )
    config = r'--oem 3 --psm 6 -l tha+eng'
    text = pytesseract.image_to_string(thresh, config=config)
    return extract_transaction_info(text)

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
    try: data['amount'] = re.search(r'จำนวนเงิน[:\s]+([\d,\.]+)', text).group(1)
    except: data['amount'] = None
    data['raw_text'] = text
    return data

# === ROUTES ===
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    result = {}
    if request.method == 'POST':
        file = request.files['file']
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid4().hex}_{original_filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        data = process_slip_with_tesseract(filepath)
        dummy_risk_score = round(random.uniform(0.1, 0.99), 2)
        user_id = session.get("user_id")

        session_db = Session()
        tx = Transaction(
            user_id=user_id,
            sender=data.get("sender_name"),
            receiver=data.get("receiver_name"),
            amount=float(data["amount"].replace(',', '')) if data.get("amount") else None,
            date_str=data.get("date"),
            raw_text=data.get("raw_text"),
            risk_score=dummy_risk_score,
            filename=unique_filename
        )
        session_db.add(tx)
        session_db.commit()
        session_db.close()

        result = {
            'filename': unique_filename,
            'risk_score': dummy_risk_score,
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

    return render_template('index.html', result=result)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    session_db = Session()
    user_id = session.get('user_id')
    is_admin = session.get('is_admin')
    if is_admin:
        transactions = session_db.query(Transaction).order_by(Transaction.created_at.desc()).all()
    else:
        transactions = session_db.query(Transaction).filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).all()
    session_db.close()
    return render_template('dashboard.html', transactions=transactions)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    user_id = session.get("user_id")
    session_db = Session()
    tx = session_db.query(Transaction).filter_by(filename=filename).first()
    user = session_db.query(User).filter_by(id=user_id).first()
    session_db.close()

    if not tx:
        return "ไม่พบสลิปนี้", 404
    if user is None or (not user.is_admin and tx.user_id != user.id):
        return "คุณไม่มีสิทธิ์เข้าถึงไฟล์นี้", 403

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/users')
def user_list():
    user_id = session.get("user_id")
    session_db = Session()
    user = session_db.query(User).filter_by(id=user_id).first()
    if not user or not user.is_admin:
        session_db.close()
        return "คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
    users = session_db.query(User).order_by(User.created_at.desc()).all()
    session_db.close()
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
        session_db = Session()
        existing_user = session_db.query(User).filter_by(username=username).first()
        if existing_user:
            session_db.close()
            return 'Username already exists!'
        new_user = User(username=username, password=hashed_pw, email=email, is_admin=False)
        session_db.add(new_user)
        session_db.commit()
        session_db.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        session_db = Session()
        user = session_db.query(User).filter_by(username=username).first()
        session_db.close()
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
