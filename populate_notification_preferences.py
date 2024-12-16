# populate_notification_preferences.py

from app import create_app, db
from app.models import User, NotificationPreference

app = create_app()

with app.app_context():
    users = User.query.all()
    for user in users:
        if not user.notification_preferences:
            notification_preference = NotificationPreference(
                user_id=user.id,
                notify_comments=True,
                notify_reactions=True,
                notify_shout_updates=True
            )
            db.session.add(notification_preference)
    db.session.commit()
    print("Notification preferences populated for existing users.")