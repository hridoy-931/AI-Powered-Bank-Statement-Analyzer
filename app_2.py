from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os
import csv
import re
from werkzeug.utils import secure_filename
from ocr_2 import ocr_pdf_to_text
from model import extract_transactions
import post_processing
import pytesseract
from pdf2image import convert_from_path

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure key
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}

# Set Tesseract and Poppler paths based on environment
if os.name == "nt":  # Windows
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    app.config['POPPLER_PATH'] = r"C:\Users\mosta\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"
else:  # Linux (Docker)
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
    app.config['POPPLER_PATH'] = None  # pdf2image finds Poppler automatically

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Simulated user database (replace with a real database in production)
# Store user data as a dictionary: {username: {'password': password, 'email': email, 'mobile': mobile}}
users = {
    'admin': {'password': 'password', 'email': 'admin@example.com', 'mobile': '+8801234567890'}
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']
        
        if username not in users:
            flash('Username not found')
            return redirect(url_for('forgot_password'))
        
        if new_password != confirm_new_password:
            flash('Passwords do not match')
            return redirect(url_for('forgot_password'))
        
        # Update the password in the users dictionary
        users[username]['password'] = new_password
        flash('Password reset successful! Please log in with your new password.')
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        mobile = request.form['mobile']
        
        # Validate mobile number: Optional country code (+ followed by 1-3 digits) and 9-15 digits
        if not re.match(r'^\+?\d{1,3}?\d{9,15}$', mobile):
            flash('Mobile number must be 9-15 digits, optionally starting with a country code (e.g., +12025550123)')
            return redirect(url_for('register'))
        
        if password == confirm_password:
            if username not in users:
                users[username] = {'password': password, 'email': email, 'mobile': mobile}
                flash('Registration successful! Please log in.')
                return redirect(url_for('login'))
            else:
                flash('Username already exists')
        else:
            flash('Passwords do not match')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_email = request.form.get('email')
        new_mobile = request.form.get('mobile')
        
        # Validate mobile number
        if not re.match(r'^\+?\d{1,3}?\d{9,15}$', new_mobile):
            flash('Mobile number must be 9-15 digits, optionally starting with a country code (e.g., +12025550123)')
            return redirect(url_for('profile'))
        
        # Update email if changed
        if new_email and new_email != users[session['username']]['email']:
            users[session['username']]['email'] = new_email
            flash('Profile updated successfully!')
        
        # Update mobile if changed
        if new_mobile and new_mobile != users[session['username']]['mobile']:
            users[session['username']]['mobile'] = new_mobile
            flash('Profile updated successfully!')
    
    return render_template('profile.html', username=session['username'], email=users[session['username']]['email'], mobile=users[session['username']]['mobile'])

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')
        if current_password == users[session['username']]['password']:
            if new_password == confirm_new_password:
                users[session['username']]['password'] = new_password
                flash('Password updated successfully!')
            else:
                flash('New passwords do not match')
        else:
            flash('Current password is incorrect')
    return render_template('settings.html', username=session['username'])

@app.route('/ocr', methods=['GET', 'POST'])
def ocr():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            try:
                # Perform OCR with Poppler path
                text = ocr_pdf_to_text(file_path, poppler_path=app.config['POPPLER_PATH'])
                # Extract transactions using LLM
                transactions = extract_transactions(text)
                # Clean and process the transactions
                cleaned_lines = post_processing.clean_bank_lines(transactions)
                cleaned_data = post_processing.clean_bank_statement(cleaned_lines)
                output_file = post_processing.process_and_validate_bank_statement(cleaned_data, f"validated_bank_statement_{session['username']}.csv")
                # Read CSV content for display
                with open(output_file, 'r') as f:
                    csv_reader = csv.DictReader(f)
                    validated_data = list(csv_reader)
                return render_template('ocr.html', username=session['username'], transactions=validated_data, csv_file=output_file)
            except Exception as e:
                flash(f'Error processing file: {str(e)}')
                return redirect(request.url)
    return render_template('ocr.html', username=session['username'])

@app.route('/download_file/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)