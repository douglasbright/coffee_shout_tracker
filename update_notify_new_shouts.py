# update_notify_new_shouts.py

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
                notify_shout_updates=True,
                notify_new_shouts=True  # Set the new field to True
            )
            db.session.add(notification_preference)
        else:
            user.notification_preferences.notify_new_shouts = True  # Update the existing field to True
    db.session.commit()
    print("All users' notify_new_shouts field has been set to True.")