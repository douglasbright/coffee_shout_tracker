from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from .models import User, Shout, db, shout_users, NotificationPreference
from .forms import UpdatePasswordForm, UpdateAvatarForm, NotificationPreferencesForm, UpdateUsernameForm, UpdateEmailForm
from werkzeug.security import check_password_hash, generate_password_hash

profile = Blueprint('profile', __name__)

@profile.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    update_password_form = UpdatePasswordForm()
    avatar_form = UpdateAvatarForm(avatar_icon=current_user.avatar_icon)
    notification_preferences_form = NotificationPreferencesForm(
        notify_comments=current_user.notify_comments,
        notify_reactions=current_user.notify_reactions,
        notify_shout_updates=current_user.notify_shout_updates,
        notify_new_shouts=current_user.notify_new_shouts,
        profile_visibility=current_user.is_public  # Set the initial value for profile visibility
    )
    update_username_form = UpdateUsernameForm(current_username=current_user.username)  # Create an instance of the UpdateUsernameForm
    update_email_form = UpdateEmailForm(current_email=current_user.email)

    return render_template('settings/profile.html', 
                           update_password_form=update_password_form, 
                           avatar_form=avatar_form, 
                           notification_preferences_form=notification_preferences_form,
                           update_username_form=update_username_form,
                           update_email_form=update_email_form)  # Pass the form to the template

@profile.route('/update_user_name/<int:user_id>', methods=['POST'])
@login_required
def update_user_name(user_id):
    user = User.query.get_or_404(user_id)
    form = UpdateUsernameForm(current_username=user.username)
    if form.validate_on_submit():
        new_username = form.username.data
        if new_username:
            user.username = new_username
            db.session.commit()
            flash(f'Username updated to {new_username}.', 'success')
        else:
            flash('Username cannot be empty.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    return redirect(request.referrer or url_for('profile.settings_profile'))

@profile.route('/update_user_email/<int:user_id>', methods=['POST'])
@login_required
def update_user_email(user_id):
    user = User.query.get_or_404(user_id)
    form = UpdateEmailForm(current_email=user.email)
    if form.validate_on_submit():
        new_email = form.email.data.lower()
        if new_email:
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user.id:
                flash('Email already in use by another account.', 'danger')
            else:
                user.email = new_email
                db.session.commit()
                flash('Email updated successfully.', 'success')
        else:
            flash('Email cannot be empty.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    return redirect(request.referrer or url_for('profile.settings_profile'))

@profile.route('/update_user_password/<int:user_id>', methods=['POST'])
@login_required
def update_user_password(user_id):
    user = User.query.get_or_404(user_id)
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(user.password, form.current_password.data):
            flash('Incorrect current password.', 'danger')
            return redirect(request.referrer or url_for('profile.settings_profile'))
        new_password = form.password.data
        user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        flash('Password updated successfully.', 'success')
    else:
        flash('There was an error updating the password.', 'danger')
    return redirect(request.referrer or url_for('profile.settings_profile'))

@profile.route('/update_user_avatar/<int:user_id>', methods=['POST'])
@login_required
def update_user_avatar(user_id):
    user = User.query.get_or_404(user_id)
    if user.id != current_user.id:
        flash('You do not have permission to update this avatar.', 'danger')
        return redirect(url_for('profile.settings_profile'))
    form = UpdateAvatarForm()
    if form.validate_on_submit():
        user.avatar_icon = form.avatar_icon.data
        db.session.commit()
        flash('Avatar updated successfully.', 'success')
    else:
        flash('There was an error updating your avatar.', 'danger')
    return redirect(request.referrer)

@profile.route('/profile/<int:user_id>', methods=['GET'])
@login_required
def profile_view(user_id):
    user = User.query.get_or_404(user_id)
    user_shouts = db.session.execute(
        db.select(Shout, shout_users.c.is_admin, shout_users.c.is_active)
        .join_from(shout_users, Shout, shout_users.c.shout_id == Shout.id)
        .where(shout_users.c.user_id == user_id)
    ).all()
    return render_template('profile.html', user=user, user_shouts=user_shouts)

@profile.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    users = User.query.all()
    update_password_form = UpdatePasswordForm()
    return render_template('manage_users.html', users=users, update_password_form=update_password_form)

@profile.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted.', 'success')
    return redirect(url_for('profile.manage_users'))

@profile.route('/update_profile_visibility', methods=['POST'])
@login_required
def update_profile_visibility():
    data = request.get_json()
    is_public = data.get('is_public', True)
    current_user.is_public = is_public
    db.session.commit()
    return jsonify({'success': 'Profile visibility updated successfully.'})

@profile.route('/update_notification_preferences', methods=['POST'])
@login_required
def update_notification_preferences():
    form = NotificationPreferencesForm()
    if form.validate_on_submit():
        current_user.notify_comments = form.notify_comments.data
        current_user.notify_reactions = form.notify_reactions.data
        current_user.notify_shout_updates = form.notify_shout_updates.data
        current_user.notify_new_shouts = form.notify_new_shouts.data
        current_user.is_public = form.profile_visibility.data  # Update profile visibility
        db.session.commit()
        flash('Notification preferences updated successfully.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    return redirect(url_for('profile.settings_profile'))