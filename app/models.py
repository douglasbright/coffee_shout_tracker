from . import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event
from enum import Enum

# NotificationType Enum
class NotificationType(Enum):
    COMMENT = 'comment'
    REACTION = 'reaction'
    SHOUT_UPDATE = 'shout_update'
    NEW_SHOUT = 'new_shout'  # Add this line

# Notification Model
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    type = db.Column(db.Enum(NotificationType), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=True)  # New field to store the URL
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='notifications')

# NotificationPreference Model
class NotificationPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    notify_comments = db.Column(db.Boolean, default=True)
    notify_reactions = db.Column(db.Boolean, default=True)
    notify_shout_updates = db.Column(db.Boolean, default=True)
    notify_new_shouts = db.Column(db.Boolean, default=True)  # New field for new shouts

    user = db.relationship('User', back_populates='notification_preferences')

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    avatar_icon = db.Column(db.String(100), nullable=True, default='bi-person-circle')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)
    login_history = db.relationship('LoginHistory', back_populates='user', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan')
    notification_preferences = db.relationship('NotificationPreference', back_populates='user', uselist=False, cascade='all, delete-orphan')

    # Relationships
    shouts_performed = db.relationship('ShoutRound', back_populates='shouter', cascade='all, delete', foreign_keys='ShoutRound.shouter_id')
    rounds_recorded = db.relationship('ShoutRound', back_populates='recorded_by', cascade='all, delete', foreign_keys='ShoutRound.recorded_by_id')
    missed_shouts = db.relationship('MissedShout', back_populates='user', cascade='all, delete')
    comment_likes = db.relationship('CommentLike', back_populates='user', cascade='all, delete-orphan')
    favorite_coffee_shops = db.relationship('UserFavoriteCoffeeShop', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def notify_comments(self):
        return self.notification_preferences.notify_comments if self.notification_preferences else False

    @notify_comments.setter
    def notify_comments(self, value):
        if not self.notification_preferences:
            self.notification_preferences = NotificationPreference(user_id=self.id)
        self.notification_preferences.notify_comments = value

    @property
    def notify_reactions(self):
        return self.notification_preferences.notify_reactions if self.notification_preferences else False

    @notify_reactions.setter
    def notify_reactions(self, value):
        if not self.notification_preferences:
            self.notification_preferences = NotificationPreference(user_id=self.id)
        self.notification_preferences.notify_reactions = value

    @property
    def notify_shout_updates(self):
        return self.notification_preferences.notify_shout_updates if self.notification_preferences else False

    @notify_shout_updates.setter
    def notify_shout_updates(self, value):
        if not self.notification_preferences:
            self.notification_preferences = NotificationPreference(user_id=self.id)
        self.notification_preferences.notify_shout_updates = value

    @property
    def notify_new_shouts(self):
        return self.notification_preferences.notify_new_shouts if self.notification_preferences else True

    @notify_new_shouts.setter
    def notify_new_shouts(self, value):
        if not self.notification_preferences:
            self.notification_preferences = NotificationPreference(user_id=self.id)
        self.notification_preferences.notify_new_shouts = value

# LoginHistory Model
class LoginHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    user_agent = db.Column(db.String(256), nullable=True)

    user = db.relationship('User', back_populates='login_history')

# CoffeeShop Model
class CoffeeShop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    shouts = db.relationship('ShoutRound', back_populates='coffee_shop', cascade='all, delete-orphan')

# Shout Model
class Shout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    workplace = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token = db.Column(db.String(36), unique=True, nullable=True)
    is_private = db.Column(db.Boolean, default=False)
    is_closed = db.Column(db.Boolean, default=False)
    pin_code_hash = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    version = db.Column(db.Integer, default=1, nullable=False)
    current_shouter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    comments_public = db.Column(db.Boolean, default=True)  # New field to determine if comments are public

    # Relationships
    participants = db.relationship(
        'User',
        secondary='shout_users',
        backref='shouts',
        primaryjoin="and_(Shout.id == shout_users.c.shout_id, shout_users.c.is_active == True)",
        secondaryjoin="User.id == shout_users.c.user_id"
    )
    rounds = db.relationship('ShoutRound', back_populates='shout', cascade='all, delete-orphan')
    current_shouter = db.relationship('User', foreign_keys=[current_shouter_id])
    favorite_coffee_shops = db.relationship('UserFavoriteCoffeeShop', back_populates='shout', cascade='all, delete-orphan')

    # Pin code methods
    def set_pin_code(self, pin_code):
        self.pin_code_hash = generate_password_hash(pin_code)

    def check_pin_code(self, pin_code):
        if self.pin_code_hash:
            return check_password_hash(self.pin_code_hash, pin_code)
        return False

# Association Table for Shouts and Users
shout_users = db.Table('shout_users',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True, index=True),
    db.Column('shout_id', db.Integer, db.ForeignKey('shout.id'), primary_key=True, index=True),
    db.Column('is_admin', db.Boolean, default=False),
    db.Column('is_active', db.Boolean, default=True),
    db.Column('sequence', db.Integer, nullable=True),
    db.Column('is_catchup_due', db.Boolean, default=False),  # New field to indicate if catchup is due
    db.Column('performed_on_behalf', db.Boolean, default=False),  # New field to indicate if the shouter performed on behalf of someone else
    db.Column('is_available_for_shout', db.Boolean, default=True)  # Field to indicate if the shouter is available for a shout
)

# Quote Model
class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserFavoriteCoffeeShop(db.Model):
    __tablename__ = 'user_favorite_coffee_shop'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', name='fk_user_favorite_coffee_shop_user'), primary_key=True)
    shout_id = db.Column(db.Integer, db.ForeignKey('shout.id', ondelete='CASCADE', name='fk_user_favorite_coffee_shop_shout'), primary_key=True)
    coffee_shop_id = db.Column(db.Integer, db.ForeignKey('coffee_shop.id', name='fk_user_favorite_coffee_shop_coffee_shop'), nullable=False)

    user = db.relationship('User', back_populates='favorite_coffee_shops')
    shout = db.relationship('Shout', back_populates='favorite_coffee_shops')
    coffee_shop = db.relationship('CoffeeShop')

# ShoutRound Model
class ShoutRound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shout_id = db.Column(db.Integer, db.ForeignKey('shout.id'), nullable=False, index=True)
    shouter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    coffee_shop_id = db.Column(db.Integer, db.ForeignKey('coffee_shop.id'), nullable=True, index=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    round_number = db.Column(db.Integer, nullable=False)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)  # New field to record the user who recorded the shout round
    attendees = db.relationship(
        'User',
        secondary='shout_round_attendees',
        backref='attended_rounds'
    )
    comments = db.relationship('ShoutComment', back_populates='shout_round', cascade='all, delete-orphan')
    reactions = db.relationship('ShoutReaction', back_populates='shout_round', cascade='all, delete-orphan')

    # Relationships
    shout = db.relationship('Shout', back_populates='rounds')
    shouter = db.relationship('User', foreign_keys=[shouter_id])
    recorded_by = db.relationship('User', foreign_keys=[recorded_by_id])  # New relationship for the user who recorded the shout round
    coffee_shop = db.relationship('CoffeeShop', back_populates='shouts')

    def calculate_coffee_purchases(self):
        purchases = {}
        for attendee in self.attendees:
            if attendee.id != self.shouter_id:
                if self.shouter_id not in purchases:
                    purchases[self.shouter_id] = {}
                if attendee.id not in purchases[self.shouter_id]:
                    purchases[self.shouter_id][attendee.id] = 0
                purchases[self.shouter_id][attendee.id] += 1
        return purchases

# MissedShout Model
class MissedShout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    shout_id = db.Column(db.Integer, db.ForeignKey('shout.id'), nullable=False, index=True)
    resolved_in_round_id = db.Column(db.Integer, db.ForeignKey('shout_round.id'), nullable=True)
    round_number = db.Column(db.Integer, nullable=False)  # New field to store the round number

    # Relationships
    user = db.relationship('User', back_populates='missed_shouts')
    shout = db.relationship('Shout')
    resolved_in_round = db.relationship('ShoutRound')

# ShoutComment Model
class ShoutComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shout_round_id = db.Column(db.Integer, db.ForeignKey('shout_round.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    shout_round = db.relationship('ShoutRound', back_populates='comments')
    user = db.relationship('User')
    likes = db.relationship('CommentLike', back_populates='comment', cascade='all, delete-orphan')

# ShoutReaction Model
class ShoutReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shout_round_id = db.Column(db.Integer, db.ForeignKey('shout_round.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    emoji = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    shout_round = db.relationship('ShoutRound', back_populates='reactions')
    user = db.relationship('User')

# Association Table for ShoutRound Attendees
shout_round_attendees = db.Table('shout_round_attendees',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True, index=True),
    db.Column('shout_round_id', db.Integer, db.ForeignKey('shout_round.id'), primary_key=True, index=True)
)

# Add CommentLike Model
class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('shout_comment.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    comment = db.relationship('ShoutComment', back_populates='likes')
    user = db.relationship('User')

# Event listener for versioning control
@event.listens_for(Shout, 'before_update')
def receive_before_update(mapper, connection, target):
    """Automatically increment version before shout update."""
    target.version += 1
