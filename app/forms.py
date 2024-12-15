from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, SelectMultipleField, DateField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, ValidationError
from wtforms.widgets import CheckboxInput, ListWidget
from .models import User
from datetime import datetime

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)], render_kw={"placeholder": "Enter your username"})
    email = StringField('Email', validators=[DataRequired(), Email()], render_kw={"placeholder": "Enter your email address"})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={"placeholder": "Enter your password"})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')], render_kw={"placeholder": "Confirm your password"})
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('An account with this username already exists. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()  # Normalize email
        if user:
            raise ValidationError('An account with this email already exists. Please log in.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')  # Added Remember Me checkbox
    submit = SubmitField('Login')

class CreateShoutForm(FlaskForm):
    name = StringField('Shout Name', validators=[DataRequired(), Length(min=2, max=100)])
    workplace = StringField('Workplace', validators=[DataRequired(), Length(min=2, max=100)])
    is_private = BooleanField('Make this Shout Private')
    pin_code = PasswordField('PIN Code (Optional)', validators=[Optional(), Length(min=4, max=10)])
    confirm_pin_code = PasswordField('Confirm PIN Code', validators=[Optional(), EqualTo('pin_code', message='PIN codes must match')])
    join_shout = BooleanField('Join this Shout', default=True)  # Checkbox to optionally join the shout as a participant
    submit = SubmitField('Create Shout')

class JoinShoutForm(FlaskForm):
    shout_name = StringField('Shout Name', validators=[DataRequired(), Length(min=2, max=100)])
    pin_code = StringField('PIN Code', validators=[Optional(), Length(min=4, max=10)])  # Optional PIN field
    submit = SubmitField('Join Shout')

class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=4)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Save Changes')

class EditShoutCommentsForm(FlaskForm):
    comments_public = BooleanField('Comments Public', default=True)
    submit = SubmitField('Save Changes')

class EditShoutForm(FlaskForm):
    name = StringField('Shout Name', validators=[DataRequired(), Length(min=2, max=100)])
    workplace = StringField('Workplace', validators=[DataRequired(), Length(min=2, max=100)])
    is_private = BooleanField('Private Shout')
    current_passcode = PasswordField('Current PIN (required to edit)', validators=[Optional()])
    new_passcode = PasswordField('New PIN (optional, leave blank if not changing)')
    confirm_new_passcode = PasswordField('Confirm New PIN', validators=[EqualTo('new_passcode', message="PINs must match")])
    remove_pin = BooleanField('Remove PIN')
    submit = SubmitField('Save Changes')

    def __init__(self, shout, *args, **kwargs):
        super(EditShoutForm, self).__init__(*args, **kwargs)
        self.shout = shout

    def validate(self, extra_validators=None):
        if not super(EditShoutForm, self).validate(extra_validators=extra_validators):
            return False
        if self.shout.pin_code_hash and not self.current_passcode.data:
            self.current_passcode.errors.append('Current PIN is required to edit this shout.')
            return False
        if self.shout.pin_code_hash and not self.shout.check_pin_code(self.current_passcode.data):
            self.current_passcode.errors.append('Incorrect current PIN code.')
            return False
        return True

# Form for adding a new participant
class AddParticipantForm(FlaskForm):
    new_participant = SelectField('Add Participant', validators=[DataRequired()], coerce=int)
    submit = SubmitField('Add Participant')

class AdminForm(FlaskForm):
    new_admins = SelectMultipleField('Select Admins', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Update Admins')

class UpdateAvatarForm(FlaskForm):
    # Avatar choices with some Bootstrap Icons (add more as needed)
    avatar_choices = [
        ('bi-person-circle', 'Person Circle'),
        ('bi-star-fill', 'Star Fill'),
        ('bi-heart-fill', 'Heart Fill'),
        ('bi-emoji-smile', 'Emoji Smile'),
        ('bi-lightning-fill', 'Lightning Fill'),
        ('bi-camera-fill', 'Camera Fill'),
        ('bi-music-note-beamed', 'Music Note'),
        ('bi-palette-fill', 'Palette Fill'),
        ('bi-balloon-fill', 'Balloon Fill'),
        ('bi-trophy-fill', 'Trophy Fill'),
        ('bi-emoji-laughing', 'Emoji Laughing'),
        ('bi-moon-stars-fill', 'Moon and Stars'),
        ('bi-puzzle-fill', 'Puzzle Fill'),
        ('bi-rocket-fill', 'Rocket Fill'),
        ('bi-sunglasses', 'Sunglasses'),
        ('bi-gift-fill', 'Gift Fill'),
        ('bi-flower1', 'Flower'),
        ('bi-peace-fill', 'Peace Fill'),
        ('bi-fire', 'Fire'),
        ('bi-ev-station-fill', 'Ev Station Fill'),
        ('bi-controller', 'Controller'),
        ('bi-arrow-through-heart-fill', 'Arrow Through Heart Fill'),
        ('bi-cloud-sun-fill', 'Cloud Sun'),
        ('bi-umbrella-fill', 'Umbrella Fill'),
        ('bi-bug-fill', 'Bug Fill'),
        ('bi-brightness-alt-high-fill', 'Sun Brightness'),
        ('bi-globe', 'Globe'),
        ('bi-boombox-fill', 'Boombox Fill'),
        ('bi-alarm-fill', 'Alarm Fill'),
        ('bi-cup-hot-fill', 'Hot Coffee Cup')
        # Add more Bootstrap Icons here as needed
    ]
    
    avatar_icon = SelectField('Select Avatar', choices=avatar_choices, validators=[DataRequired()])
    submit = SubmitField('Update Avatar')

# Form for adding a new quote
class AddQuoteForm(FlaskForm):
    text = StringField('Quote', validators=[DataRequired(), Length(min=5, max=255)])
    author = StringField('Author', validators=[Length(max=100)])
    submit = SubmitField('Add Quote')

# Form for editing an existing quote
class EditQuoteForm(FlaskForm):
    text = StringField('Quote', validators=[DataRequired(), Length(min=5, max=255)])
    author = StringField('Author', validators=[Length(max=100)])
    submit = SubmitField('Save Changes')

class RecordShoutForm(FlaskForm):
    shouter = SelectField('Shouter', validators=[DataRequired()], coerce=int)
    attendees = SelectMultipleField('Attendees', validators=[DataRequired()], coerce=int)
    date = DateField('Date', default=datetime.today, validators=[DataRequired()], format='%Y-%m-%d')
    coffee_shop = SelectField('Coffee Shop', validators=[Optional()], coerce=int, choices=[(0, 'None')])  # New field
    submit = SubmitField('Record Shout')

class AddCoffeeShopForm(FlaskForm):
    name = StringField('Coffee Shop Name', validators=[DataRequired(), Length(min=2, max=100)])
    address = StringField('Address', validators=[Length(max=200)])
    submit = SubmitField('Add Coffee Shop')

class EditShoutRoundForm(FlaskForm):
    shouter = SelectField('Shouter', validators=[DataRequired()], coerce=int)
    attendees = SelectMultipleField('Attendees', validators=[DataRequired()], coerce=int, option_widget=CheckboxInput(), widget=ListWidget(prefix_label=False))
    date = DateField('Date', validators=[DataRequired()], format='%Y-%m-%d')
    coffee_shop = SelectField('Coffee Shop', validators=[Optional()], coerce=int, choices=[(0, 'None')])
    submit = SubmitField('Update Shout Round')

class AddPinForm(FlaskForm):
    new_pin = PasswordField('New PIN', validators=[DataRequired(), Length(min=4, max=10)])
    confirm_new_pin = PasswordField('Confirm New PIN', validators=[DataRequired(), EqualTo('new_pin', message='PINs must match')])
    submit = SubmitField('Add PIN')

class UpdatePinForm(FlaskForm):
    current_pin = PasswordField('Current PIN', validators=[DataRequired()])
    new_pin = PasswordField('New PIN', validators=[DataRequired(), Length(min=4, max=10)])
    confirm_new_pin = PasswordField('Confirm New PIN', validators=[DataRequired(), EqualTo('new_pin', message='PINs must match')])
    submit = SubmitField('Update PIN')

class RemovePinForm(FlaskForm):
    current_pin = PasswordField('Current PIN', validators=[DataRequired()])
    submit = SubmitField('Remove PIN')

class ReactionForm(FlaskForm):
    shout_round_id = HiddenField('Shout Round ID', validators=[DataRequired()])
    reaction = SelectField('Reaction', choices=[
        ('bi bi-clock', 'Clock'),
        ('bi bi-hand-thumbs-up', 'Thumbs Up'),
        ('bi bi-hand-thumbs-down', 'Thumbs Down')
    ], validators=[DataRequired()])

class SelectFavoriteCoffeeShopForm(FlaskForm):
    coffee_shop = SelectField('Favorite Coffee Shop', validators=[DataRequired()], coerce=int)
    submit = SubmitField('Set as Favorite')

class NotificationPreferencesForm(FlaskForm):
    notify_comments = BooleanField('Notify me about comments')
    notify_reactions = BooleanField('Notify me about reactions')
    notify_shout_updates = BooleanField('Notify me about shout updates')
    submit = SubmitField('Save Preferences')