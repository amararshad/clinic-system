from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from db import get_db_connection
import bcrypt

signup_bp = Blueprint('signup', __name__)

@signup_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        role = request.form['role']
        full_name = request.form['full_name']
        contact_info = request.form.get('contact_info', '')
        gender = request.form.get('gender', None)
        dob = request.form.get('date_of_birth', None)
        address = request.form.get('address', '')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if username/email exists
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                flash("Username or email already taken.", "error")
                return render_template('signup.html')

            hashed_pw = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

            # Insert into users
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role, full_name, contact_info, gender, date_of_birth, address) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (username, email, hashed_pw, role, full_name, contact_info, gender, dob, address)
            )
            user_id = cursor.lastrowid

            # Role-specific inserts
            if role == 'Patient':
                cursor.execute(
                    "INSERT INTO patients (user_id, full_name, email, contact_info, gender, date_of_birth, address) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (user_id, full_name, email, contact_info, gender, dob, address)
                )
            elif role == 'Doctor':
                specialization = request.form.get('specialization', '').strip()
                license_number = request.form.get('license_number', '').strip()

                if not specialization or not license_number:
                    conn.rollback()
                    flash("Specialization and License Number are required for Doctors.", "error")
                    return render_template('signup.html')

                cursor.execute(
                    "INSERT INTO doctors (user_id, full_name, email, contact_info, specialization, license_number) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (user_id, full_name, email, contact_info, specialization, license_number)
                )
            elif role == 'Admin':
                cursor.execute(
                    "INSERT INTO admin_staff (user_id, full_name) VALUES (%s, %s)",
                    (user_id, full_name)
                )

            conn.commit()
            flash("Signup successful! Please log in.", "success")
            return redirect(url_for('login.login'))
        except Exception as e:
            conn.rollback()
            flash(f"Error during signup: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template('signup.html')