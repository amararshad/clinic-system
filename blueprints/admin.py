from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from db import get_db_connection
import bcrypt
import mysql.connector
from flask import flash

admin_bp = Blueprint('admin_bp', __name__)


@admin_bp.route('/')
def home():
    return redirect(url_for('admin_bp.login'))


@admin_bp.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not email or not password or not confirm_password:
            error = "All fields are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        else:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
                existing = cursor.fetchone()
                if existing:
                    error = "Username or email already exists."
                else:
                    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    cursor.execute("""
                        INSERT INTO users (username, email, password_hash, role) 
                        VALUES (%s, %s, %s, 'Admin')
                    """, (username, email, hashed_pw))
                    user_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO admin_staff (user_id, full_name) 
                        VALUES (%s, %s)
                    """, (user_id, username))
                    conn.commit()
                    return redirect(url_for('admin_bp.login'))
            finally:
                cursor.close()
                conn.close()

    return render_template('admin/register.html', error=error)


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT u.user_id, u.password_hash, a.admin_id 
                FROM users u 
                JOIN admin_staff a ON u.user_id = a.user_id 
                WHERE u.username = %s AND u.role = 'Admin'
            """, (username,))
            result = cursor.fetchone()
            if result and bcrypt.checkpw(password.encode('utf-8'), result['password_hash'].encode('utf-8')):
                session['user_id'] = result['user_id']
                session['admin_id'] = result['admin_id']
                session['role'] = 'Admin'
                return redirect(url_for('admin_bp.dashboard'))
            else:
                error = "Invalid username or password."
        finally:
            cursor.close()
            conn.close()

    return render_template('admin/login.html', error=error)


@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('admin_bp.login'))
    return render_template('admin/dashboard.html')


@admin_bp.route('/doctors')
def view_doctors():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('admin_bp.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM doctors")
        doctors = cursor.fetchall()
        return render_template('admin/view_doctors.html', doctors=doctors)
    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('admin_bp.login'))

    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        contact_info = request.form['contact_info']
        specialization = request.form['specialization']
        license_number = request.form['license_number']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if user email already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already exists. Please use a different one.", "error")
                return redirect(url_for('admin_bp.add_doctor'))  # ✅ Moved inside the IF

            # Create user account
            password = bcrypt.hashpw("default123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'Doctor')
            """, (email, email, password))
            user_id = cursor.lastrowid

            # Create doctor profile
            cursor.execute("""
                INSERT INTO doctors (user_id, full_name, email, contact_info, specialization, license_number)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, full_name, email, contact_info, specialization, license_number))
            conn.commit()
            flash("Doctor added successfully!", "success")
            return redirect(url_for('admin_bp.view_doctors'))
        except mysql.connector.Error as e:
            flash(f"Error adding doctor: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('admin/add_doctor.html')

@admin_bp.route('/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_bp.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        full_name = request.form['full_name']
        specialization = request.form['specialization']
        email = request.form['email']
        contact_info = request.form['contact_info']

        cursor.execute("""
            UPDATE doctors
            SET full_name=%s, specialization=%s, email=%s, contact_info=%s
            WHERE doctor_id=%s
        """, (full_name, specialization, email, contact_info, doctor_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_bp.view_doctors'))

    cursor.execute("SELECT * FROM doctors WHERE doctor_id = %s", (doctor_id,))
    doctor = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('admin/edit_doctor.html', doctor=doctor)

@admin_bp.route('/delete_doctor/<int:doctor_id>')
def delete_doctor(doctor_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_bp.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        cursor.execute("DELETE FROM users WHERE user_id = (SELECT user_id FROM doctors WHERE doctor_id = %s)", (doctor_id,))
        conn.commit()
        flash("Doctor deleted successfully.", "success")
    except mysql.connector.Error as e:
        flash(f"Error deleting doctor: {e}", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_bp.view_doctors'))

@admin_bp.route('/patients')
def view_patients():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('admin_bp.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM patients")  # Assuming you have a patients table
        patients = cursor.fetchall()
        return render_template('admin/view_patients.html', patients=patients)
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO patients 
                (full_name, gender, date_of_birth, email, contact_info, address) 
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (request.form['full_name'], request.form['gender'], request.form['date_of_birth'],
                request.form['email'], request.form['contact_info'], request.form['address']))
            conn.commit()
            flash("Patient added successfully!", "success")
        except mysql.connector.Error as e:
            flash(f"Failed to add patient: {e}", "error")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('admin_bp.view_patients'))
    return render_template('admin/add_patient.html')

@admin_bp.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_bp.login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        full_name = request.form['full_name']
        gender = request.form['gender']
        date_of_birth = request.form['date_of_birth']
        email = request.form['email']
        contact_info = request.form['contact_info']
        address = request.form['address']
        cursor.execute("UPDATE patients SET full_name=%s, gender=%s, date_of_birth=%s, email=%s, contact_info=%s, address=%s WHERE patient_id=%s",
                       (full_name, gender, date_of_birth, email, contact_info, address, patient_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_bp.view_patients'))
    else:
        cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
        patient = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('admin/edit_patient.html', patient=patient)

@admin_bp.route('/delete_patient/<int:patient_id>')
def delete_patient(patient_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_bp.login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_bp.view_patients'))

@admin_bp.route('/billings')
def view_billing():
    if 'admin_id' not in session:
        return redirect(url_for('admin_bp.login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.billing_id, b.amount, b.status, b.billing_date,
               p.full_name AS patient_name, d.full_name AS doctor_name
        FROM billing b
        JOIN patients p ON b.patient_id = p.patient_id
        JOIN doctors d ON b.doctor_id = d.doctor_id
    """)
    billings = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/view_billing.html', billings=billings)

@admin_bp.route('/add_billings', methods=['GET', 'POST'])
def add_billing():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO billing (patient_id, doctor_id, amount, status)
            VALUES (%s, %s, %s, %s)
        """, (
            request.form['patient_id'],
            request.form['doctor_id'],
            request.form['amount'],
            request.form['status']
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_bp.view_billing'))

    cursor.execute("SELECT patient_id, full_name FROM patients")
    patients = cursor.fetchall()
    cursor.execute("SELECT doctor_id, full_name FROM doctors")
    doctors = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/add_billing.html', patients=patients, doctors=doctors)

@admin_bp.route('/edit_billings/<int:billing_id>', methods=['GET', 'POST'])
def edit_billing(billing_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_bp.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        cursor.execute("""
            UPDATE billing SET patient_id=%s, doctor_id=%s, amount=%s, status=%s WHERE billing_id=%s
        """, (
            request.form['patient_id'],
            request.form['doctor_id'],
            request.form['amount'],
            request.form['status'],
            billing_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_bp.view_billing'))
    else:
        cursor.execute("SELECT * FROM billing WHERE billing_id = %s", (billing_id,))
        billing = cursor.fetchone()
        cursor.execute("SELECT patient_id, full_name FROM patients")
        patients = cursor.fetchall()
        cursor.execute("SELECT doctor_id, full_name FROM doctors")
        doctors = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin/edit_billing.html', billing=billing, patients=patients, doctors=doctors)

@admin_bp.route('/delete_billing/<int:billing_id>')
def delete_billing(billing_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_bp.login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM billing WHERE billing_id = %s", (billing_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_bp.view_billing'))

@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_bp.login'))