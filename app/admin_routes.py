# app/admin_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import LoginHistory, Shout, User, shout_users, db

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

@admin.route('/admin/shout_users', methods=['GET'])
@login_required
def admin_shout_users():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Query all shouts and their users
    shouts = Shout.query.all()
    shout_users_data = db.session.execute(
        db.select(
            User.id, User.username, User.email,
            shout_users.c.is_admin, shout_users.c.is_active, shout_users.c.sequence,
            shout_users.c.is_catchup_due, shout_users.c.is_available_for_shout,
            shout_users.c.shout_id
        )
        .join_from(shout_users, User, shout_users.c.user_id == User.id)
        .order_by(shout_users.c.shout_id, shout_users.c.sequence)
    ).all()

    # Organize data by shout
    shouts_with_users = {}
    for shout in shouts:
        shouts_with_users[shout.id] = {
            'shout': shout,
            'users': [user for user in shout_users_data if user.shout_id == shout.id]
        }

    return render_template('admin_shout_users.html', shouts_with_users=shouts_with_users)