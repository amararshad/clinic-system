from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from db import get_db_connection
import bcrypt

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user and bcrypt.checkpw(password, user['password_hash'].encode('utf-8')):
                session['user_id'] = user['user_id']
                session['role'] = user['role']
                session['username'] = user['username']

                # Redirect based on role
                if user['role'] == 'Patient':
                    cursor.execute("SELECT patient_id FROM patients WHERE user_id = %s", (user['user_id'],))
                    patient = cursor.fetchone()
                    if patient:
                        session['patient_id'] = patient['patient_id']
                    return redirect(url_for('patient_bp.dashboard'))
                elif user['role'] == 'Doctor':
                    cursor.execute("SELECT doctor_id, full_name FROM doctors WHERE user_id = %s", (user['user_id'],))
                    doctor = cursor.fetchone()
                    if doctor:
                        session['doctor_id'] = doctor['doctor_id']
                        session['doctor_name'] = doctor['full_name']
                    return redirect(url_for('doctor_bp.doctor_dashboard'))
                elif user['role'] == 'Admin':
                    cursor.execute("SELECT admin_id FROM admin_staff WHERE user_id = %s", (user['user_id'],))
                    admin = cursor.fetchone()
                    if admin:
                        session['admin_id'] = admin['admin_id']
                    return redirect(url_for('admin_bp.dashboard'))
            else:
                flash('Invalid email or password.', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')