from flask import Blueprint, render_template, request, redirect, session, url_for,flash
from db import get_db_connection
import bcrypt

doctor_bp = Blueprint('doctor_bp', __name__)

@doctor_bp.route('/')
def home():
    if 'user_id' in session and session.get('role') == 'Doctor':
        return redirect(url_for('doctor_bp.doctor_dashboard'))
    return redirect(url_for('doctor_bp.doctor_login'))

@doctor_bp.route('/login', methods=['GET', 'POST'])
def doctor_login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT u.user_id, u.password_hash, d.doctor_id, d.full_name 
                FROM users u 
                JOIN doctors d ON u.user_id = d.user_id 
                WHERE u.email = %s AND u.role = 'Doctor'
            """, (email,))
            doctor = cursor.fetchone()

            if doctor and bcrypt.checkpw(password, doctor['password_hash'].encode('utf-8')):
                session['user_id'] = doctor['user_id']
                session['doctor_id'] = doctor['doctor_id']
                session['doctor_name'] = doctor['full_name']
                session['role'] = 'Doctor'
                return redirect(url_for('doctor_bp.doctor_dashboard'))
            else:
                error = "Invalid email or password"
        finally:
            cursor.close()
            conn.close()

    return render_template('doctor/login.html', error=error)

@doctor_bp.route('/logout')
def doctor_logout():
    session.clear()
    return redirect(url_for('doctor_bp.doctor_login'))

@doctor_bp.route('/dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session.get('role') != 'Doctor':
        return redirect(url_for('doctor_bp.doctor_login'))
    return render_template('doctor/docDash.html', doctor=session['doctor_name'])

@doctor_bp.route('/appointments')
def view_appointments():
    if 'user_id' not in session or session.get('role') != 'Doctor':
        return redirect(url_for('doctor_bp.doctor_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                a.appointment_id,
                a.patient_id,  -- 👈 ADD THIS LINE
                p.full_name AS patient_name,
                DATE(a.appointment_datetime) AS appointment_date,
                TIME(a.appointment_datetime) AS appointment_time,
                a.notes,
                a.status
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            WHERE a.doctor_id = %s
            ORDER BY a.appointment_datetime
        """, (session['doctor_id'],))
        appointments = cursor.fetchall()
        return render_template('doctor/appointments.html',
                             appointments=appointments,
                             doctor_name=session['doctor_name'])
    finally:
        cursor.close()
        conn.close()

@doctor_bp.route('/patients')
def doctor_patients():
    if 'user_id' not in session or session.get('role') != 'Doctor':
        return redirect(url_for('doctor_bp.doctor_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('''
            SELECT DISTINCT p.* FROM patients p 
            JOIN appointments a ON p.patient_id = a.patient_id 
            WHERE a.doctor_id = %s
        ''', (session['doctor_id'],))
        patients = cursor.fetchall()
        return render_template('doctor/patients.html', patients=patients)
    finally:
        cursor.close()
        conn.close()

@doctor_bp.route('/medical/<int:patient_id>', methods=['GET', 'POST'])
def doctor_medical_history(patient_id):
    if 'user_id' not in session or session.get('role') != 'Doctor':
        return redirect(url_for('doctor_bp.doctor_login'))

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)  # <-- add buffered=True
    try:
        # Check authorization
        cursor.execute('''
            SELECT * FROM appointments 
            WHERE patient_id = %s AND doctor_id = %s
        ''', (patient_id, session['doctor_id']))
        auth_check = cursor.fetchone()
        if not auth_check:
            return "Unauthorized access", 403

        if request.method == 'POST':
            diagnosis = request.form.get('diagnosis', '')
            treatment = request.form.get('treatment', '')
            notes = request.form.get('notes', '')

            cursor.execute('''
                INSERT INTO medical_history 
                (patient_id, doctor_id, diagnosis, treatment, notes, visit_date) 
                VALUES (%s, %s, %s, %s, %s, CURDATE())
            ''', (patient_id, session['doctor_id'], diagnosis, treatment, notes))
            conn.commit()

            cursor.execute('''
                INSERT INTO MedHistoryAccessLog (doctorID, patientID, action)
                VALUES (%s, %s, 'UPDATE')
            ''', (session['doctor_id'], patient_id))
            conn.commit()

            return redirect(url_for('doctor_bp.doctor_patients'))

        cursor.execute('''
            INSERT INTO MedHistoryAccessLog (doctorID, patientID, action)
            VALUES (%s, %s, 'VIEW')
        ''', (session['doctor_id'], patient_id))
        conn.commit()

        cursor.execute('''
            SELECT * FROM medical_history 
            WHERE patient_id = %s AND doctor_id = %s
            ORDER BY visit_date DESC
        ''', (patient_id, session['doctor_id']))
        history = cursor.fetchall()

        return render_template('doctor/medical_history.html',
                             history=history,
                             patient_id=patient_id)
    finally:
        cursor.close()
        conn.close()
