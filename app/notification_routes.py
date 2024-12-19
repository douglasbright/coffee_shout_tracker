from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from .models import Notification, NotificationType, User, Shout, ShoutRound, ShoutReaction, ShoutComment, db

notification = Blueprint('notification', __name__)

def create_notification(user_id, notification_type, shout_id=None, shout_round_id=None, comment_text=None, reaction_type=None):
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
        shout_id=shout_id,
        shout_round_id=shout_round_id
    )
    db.session.add(notification)
    db.session.commit()

def notify_all_participants(shout_id, notification_type, shout_round_id=None, comment_text=None, reaction_type=None):
    shout = Shout.query.get(shout_id)
    if not shout:
        return

    for participant in shout.participants:
        create_notification(participant.id, notification_type, shout_id=shout_id, shout_round_id=shout_round_id, comment_text=comment_text, reaction_type=reaction_type)

@notification.route('/notifications', methods=['GET'])
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Dynamically generate the URL and message
    for notification in user_notifications:
        if notification.shout_round_id:
            notification.url = url_for('activity.shout_round_activity', shout_round_id=notification.shout_round_id)
        
        # Generate dynamic message
        if notification.type == NotificationType.NEW_SHOUT:
            shout_round = ShoutRound.query.get(notification.shout_round_id)
            if shout_round:
                notification.message = f"{shout_round.shouter.username} has just performed round {shout_round.round_number} of \"{shout_round.shout.name}\".<br><small>Add a comment or reaction now!</small>"
        elif notification.type == NotificationType.REACTION:
            shout_round = ShoutRound.query.get(notification.shout_round_id)
            reaction = ShoutReaction.query.filter_by(user_id=notification.user_id, shout_round_id=notification.shout_round_id).first()
            if shout_round and reaction:
                notification.message = f"{reaction.user.username} has given you a <i class=\"{reaction.emoji}\"></i> on round {shout_round.round_number} of \"{shout_round.shout.name}\"."
        elif notification.type == NotificationType.COMMENT:
            shout_round = ShoutRound.query.get(notification.shout_round_id)
            comment = ShoutComment.query.filter_by(user_id=notification.user_id, shout_round_id=notification.shout_round_id).first()
            if shout_round and comment:
                notification.message = f"{comment.user.username} said \"{comment.text}\" on round {shout_round.round_number} of \"{shout_round.shout.name}\"."

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
