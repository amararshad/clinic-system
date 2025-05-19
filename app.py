from flask import Flask, url_for, redirect, render_template
from blueprints.doctor import doctor_bp
from blueprints.patient import patient_bp
from blueprints.admin import admin_bp
from blueprints.login import login_bp
from blueprints.signup import signup_bp

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Register blueprints
app.register_blueprint(doctor_bp, url_prefix='/doctor')
app.register_blueprint(patient_bp, url_prefix='/patient')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(login_bp)
app.register_blueprint(signup_bp, url_prefix='/signup')


@app.route('/')
def home():
    return redirect(url_for('choose_role'))

@app.route('/choose_role')
def choose_role():
    return render_template('shared/choose_role.html')

if __name__ == '__main__':
    app.run(debug=True)