from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from .models import Notification, NotificationType, User, Shout, db

notification = Blueprint('notification', __name__)

def create_notification(user_id, notification_type, message, url=None):
    user = User.query.get(user_id)
    if not user:
        return

    # Check user preferences
    if notification_type == NotificationType.COMMENT and not user.notify_comments:
        return
    if notification_type == NotificationType.REACTION and not user.notify_reactions:
        return
    if notification_type == NotificationType.SHOUT_UPDATE and not user.notify_shout_updates:
        return
    if notification_type == NotificationType.NEW_SHOUT and not user.notify_new_shouts:
        return

    # Create and add the notification
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        message=message,
        url=url  # Store the URL
    )
    db.session.add(notification)
    db.session.commit()

def notify_all_participants(shout_id, notification_type, message, url=None):
    shout = Shout.query.get(shout_id)
    if not shout:
        return

    for participant in shout.participants:
        create_notification(participant.id, notification_type, message, url)

@notification.route('/notifications', methods=['GET'])
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=user_notifications)

@notification.route('/notifications/mark_as_read', methods=['POST'])
@login_required
def mark_as_read():
    notification_id = request.form.get('notification_id')
    notification = Notification.query.get(notification_id)
    if notification and notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@notification.route('/notifications/clear_all', methods=['POST'])
@login_required
def clear_all_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@notification.route('/notifications/delete_all', methods=['POST'])
@login_required
def delete_all_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).all()
    for notification in notifications:
        db.session.delete(notification)
    db.session.commit()
    return jsonify({'success': True})
