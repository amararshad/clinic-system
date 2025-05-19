from flask import Blueprint, request, render_template, redirect, session, url_for, flash
import bcrypt
import mysql.connector
from db import get_db_connection

patient_bp = Blueprint('patient_bp', __name__)


@patient_bp.route('/')
def home():
    return redirect(url_for('patient_bp.login'))


@patient_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        hashed_pw = bcrypt.hashpw(password, bcrypt.gensalt())

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'Patient')",
                           (username, hashed_pw))
            user_id = cursor.lastrowid

            cursor.execute("INSERT INTO patients (user_id, full_name) VALUES (%s, %s)",
                           (user_id, username))
            conn.commit()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('patient_bp.login'))
        except mysql.connector.IntegrityError:
            flash("Username already exists.", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('patient/signup.html')


@patient_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT u.user_id, u.password_hash, p.patient_id FROM users u JOIN patients p ON u.user_id = p.user_id WHERE u.username = %s",
                (username,))
            user = cursor.fetchone()

            if user and bcrypt.checkpw(password, user['password_hash'].encode('utf-8')):
                session['user_id'] = user['user_id']
                session['patient_id'] = user['patient_id']
                session['role'] = 'Patient'
                session['username'] = username
                return redirect(url_for('patient_bp.dashboard'))
            else:
                flash("Invalid credentials.", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('patient/login.html')


@patient_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Patient':
        return redirect(url_for('patient_bp.login'))
    return render_template('patient/dashboard.html', username=session['username'])


@patient_bp.route('/book', methods=['GET', 'POST'])
def book():
    if 'user_id' not in session or session.get('role') != 'Patient':
        return redirect(url_for('patient_bp.login'))

    message = ''

    # Always get the list of doctors to show in dropdown
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT doctor_id, full_name 
        FROM doctors 
        ORDER BY full_name
    """)
    doctors = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        date = request.form['date']
        time = request.form['time']

        if not doctor_id.isdigit():
            message = "Doctor ID must be a number."
            return render_template('patient/book.html', message=message, doctors=doctors)

        doctor_id = int(doctor_id)
        appointment_datetime = f"{date} {time}"

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO appointments (patient_id, doctor_id, appointment_datetime) VALUES (%s, %s, %s)",
                (session['patient_id'], doctor_id, appointment_datetime)
            )
            conn.commit()
            message = "Appointment booked successfully."
        except mysql.connector.Error as e:
            message = f"Database error: {e}"
        finally:
            cursor.close()
            conn.close()

    return render_template('patient/book.html', message=message, doctors=doctors)


@patient_bp.route('/view')
def view_appointments():
    if 'user_id' not in session or session.get('role') != 'Patient':
        return redirect(url_for('patient_bp.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.appointment_id, d.full_name AS doctor_name, 
                   DATE(a.appointment_datetime) AS date, 
                   TIME(a.appointment_datetime) AS time,
                   a.status
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.doctor_id
            WHERE a.patient_id = %s
            ORDER BY a.appointment_datetime
        """, (session['patient_id'],))
        appointments = cursor.fetchall()
        return render_template('patient/view.html', appointments=appointments)
    finally:
        cursor.close()
        conn.close()


@patient_bp.route('/billing')
def billing():
    if 'user_id' not in session or session.get('role') != 'Patient':
        return redirect(url_for('patient_bp.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT SUM(amount) FROM billing WHERE patient_id = %s", (session['patient_id'],))
        bill = cursor.fetchone()
        amount = f"RM{bill[0]:.2f}" if bill[0] else "RM0.00"
        return render_template('patient/billing.html', amount=amount)
    finally:
        cursor.close()
        conn.close()


@patient_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('patient_bp.login'))