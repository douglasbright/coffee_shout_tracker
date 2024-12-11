# app/admin_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import LoginHistory

admin = Blueprint('admin', __name__)

@admin.route('/admin/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    return render_template('admin.html')

@admin.route('/admin/login_history')
@login_required
def view_login_history():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    login_history = LoginHistory.query.order_by(LoginHistory.login_time.desc()).all()
    return render_template('login_history.html', login_history=login_history)