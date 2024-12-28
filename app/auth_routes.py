from flask import Blueprint, render_template, redirect, url_for, request, jsonify, make_response
from flask_login import login_required, current_user, login_user, logout_user
from .models import User, LoginHistory, db
from .forms import LoginForm, RegistrationForm
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        user = User(username=form.username.data, email=form.email.data.lower(), password=hashed_password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created successfully. You are now logged in.', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('register.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    last_user = request.cookies.get('last_user')
    form = LoginForm()
    if last_user and not form.email.data:
        form.email.data = last_user
    
    if form.validate_on_submit():
        email_lower = form.email.data.lower()
        user = User.query.filter_by(email=email_lower).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            
            # Record login history
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent')
            login_history = LoginHistory(user_id=user.id, ip_address=ip_address, user_agent=user_agent)
            db.session.add(login_history)
            db.session.commit()
            
            response = redirect(url_for('main.dashboard'))
            response.set_cookie('last_user', user.email, max_age=60*60*24*30)
            return response
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@auth.route('/clear_remembered_user', methods=['POST'])
def clear_remembered_user():
    response = redirect(url_for('auth.login'))
    response.delete_cookie('last_user')
    return response
