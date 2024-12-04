import random
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user, login_user, logout_user
from .models import User, Shout, db, shout_users, Quote, ShoutRound, MissedShout, ShoutComment, ShoutReaction
from .forms import LoginForm, RegistrationForm, CreateShoutForm, JoinShoutForm, UpdatePasswordForm, AddParticipantForm, EditShoutForm, AdminForm, UpdateAvatarForm, AddQuoteForm, EditQuoteForm, RecordShoutForm
from werkzeug.security import generate_password_hash, check_password_hash
from .shout_utils import calculate_coffee_stats, set_next_shouter

main = Blueprint('main', __name__)

@main.route('/')
def home():
    # Check if the user is authenticated and redirect to the dashboard if they are
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Quote fetching logic for anonymous users
    last_quote_id = request.cookies.get('last_quote_id')
    quotes = Quote.query.all()

    # If there are quotes, exclude the last one displayed (if any)
    if last_quote_id:
        quotes = [quote for quote in quotes if str(quote.id) != last_quote_id]

    # Select a new random quote
    random_quote = random.choice(quotes) if quotes else None

    # Render the home page with the random quote and set a cookie for the last quote
    response = make_response(render_template('home.html', quote=random_quote))
    if random_quote:
        response.set_cookie('last_quote_id', str(random_quote.id), max_age=60 * 60 * 24)  # Cookie valid for 1 day

    return response

@main.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_shouts = db.session.execute(
        db.select(Shout, shout_users.c.is_active)
        .join_from(shout_users, Shout, shout_users.c.shout_id == Shout.id)
        .where(shout_users.c.user_id == current_user.id)
    ).all()

    join_form = JoinShoutForm()  # The form for joining a shout
    quotes = Quote.query.all()
    random_quote = random.choice(quotes) if quotes else None

    # Prepare shout data for the template, adding admin and admin_count
    user_shout_data = []
    for shout, is_active in user_shouts:
        # Get all participants for the shout along with their admin status
        participants_with_admin_status = db.session.execute(
            db.select(User, shout_users.c.is_admin)
            .select_from(shout_users)
            .join(User, User.id == shout_users.c.user_id)
            .where(shout_users.c.shout_id == shout.id)
        ).fetchall()

        # Check if the current user is an admin of the shout
        is_admin = any(p[1] for p in participants_with_admin_status if p[0].id == current_user.id)

        # Count the number of admins in the shout
        admin_count = sum(1 for p in participants_with_admin_status if p[1])

        # Check if the current shouter is set, and if not, set it
        if not shout.current_shouter:
            set_next_shouter(shout.id)
            db.session.refresh(shout)  # Refresh the shout object to get the updated current_shouter

        # Append the shout and admin data to the list for rendering in the template
        user_shout_data.append({
            'shout': shout,
            'participants': participants_with_admin_status,  # Passing participants with their admin status
            'is_admin': is_admin,
            'admin_count': admin_count,
            'is_active': is_active
        })

    # Render the dashboard template with the user's shout data and join form
    return render_template('dashboard.html', user_shouts=user_shout_data, join_form=join_form, quote=random_quote)

# Import the activity blueprint
from .activity_routes import activity as activity_blueprint
main.register_blueprint(activity_blueprint)


@main.route('/search_shouts')
@login_required
def search_shouts():
    search_term = request.args.get('q', '')

    # Fetch all shouts matching the search term that are public and the user is not already a participant/admin
    shouts = Shout.query.filter(
        Shout.is_private == False,  # Only include public shouts
        Shout.name.ilike(f'%{search_term}%'),  # Match search term
        ~Shout.participants.any(User.id == current_user.id)  # Exclude shouts the user is part of
    ).all()

    shout_names = [shout.name for shout in shouts]
    return jsonify(shout_names)

@main.route('/check_shout_name', methods=['POST'])
@login_required
def check_shout_name():
    data = request.get_json()
    shout_name = data.get('name', '').strip()

    # Check if the shout name already exists in the database
    shout_exists = Shout.query.filter_by(name=shout_name).first() is not None

    return jsonify({'exists': shout_exists})

@main.route('/shout/<int:shout_id>/update_admins', methods=['POST'])
@login_required
def update_admins(shout_id):
    shout = Shout.query.get_or_404(shout_id)

    # Only admins can update other admins
    user_is_admin = db.session.execute(
        shout_users.select().where(
            shout_users.c.user_id == current_user.id,
            shout_users.c.shout_id == shout.id,
            shout_users.c.is_admin == True
        )
    ).first()

    if not user_is_admin:
        flash('You do not have permission to update admins.', 'danger')
        return redirect(url_for('shout.shout_profile', shout_id=shout.id))

    form = AdminForm()
    form.new_admins.choices = [(p.id, p.username) for p, _ in db.session.execute(
        db.select(User, shout_users.c.is_admin)
        .join_from(shout_users, User, shout_users.c.user_id == User.id)
        .where(shout_users.c.shout_id == shout.id)
    ).all()]

    if form.validate_on_submit():
        selected_admins = set(form.new_admins.data)
        
        # Get all current admins and participants
        all_participants = db.session.execute(
            db.select(User, shout_users.c.is_admin)
            .join_from(shout_users, User, shout_users.c.user_id == User.id)
            .where(shout_users.c.shout_id == shout.id)
        ).all()

        current_admins = {p.id for p, is_admin in all_participants if is_admin}

        # Prevent removal of all admins
        if len(selected_admins) == 0:
            flash('There must be at least one admin.', 'danger')
            return redirect(url_for('shout.shout_profile', shout_id=shout.id))

        # Update admin statuses
        for participant, is_admin in all_participants:
            if participant.id in selected_admins:
                # If not already an admin, make them admin
                if not is_admin:
                    db.session.execute(
                        shout_users.update()
                        .where(shout_users.c.user_id == participant.id)
                        .where(shout_users.c.shout_id == shout.id)
                        .values(is_admin=True)
                    )
            else:
                # If they are currently an admin but should no longer be
                if is_admin and len(current_admins) > 1:  # Ensure at least one admin remains
                    db.session.execute(
                        shout_users.update()
                        .where(shout_users.c.user_id == participant.id)
                        .where(shout_users.c.shout_id == shout.id)
                        .values(is_admin=False)
                    )

        db.session.commit()
        flash('Admins updated successfully.', 'success')

    return redirect(url_for('shout.shout_profile', shout_id=shout.id))


@main.route('/edit_shout/<int:shout_id>', methods=['POST'])
@login_required
def edit_shout(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    form = EditShoutForm(shout=shout)
    if form.validate_on_submit():
        if shout.pin_code_hash and form.current_passcode.data:
            if not shout.check_pin_code(form.current_passcode.data):
                flash('Incorrect current PIN code. Please try again.', 'danger')
                return redirect(request.referrer or url_for('shout.shout_profile', shout_id=shout.id))
        shout.name = form.name.data
        shout.workplace = form.workplace.data
        shout.is_private = form.is_private.data
        if form.remove_pin.data:
            shout.pin_code_hash = None
            flash('Shout details updated and PIN removed successfully.', 'success')
        elif form.new_passcode.data:
            shout.set_pin_code(form.new_passcode.data)
            flash('Shout details and PIN updated successfully.', 'success')
        else:
            flash('Shout details updated successfully.', 'success')
        db.session.commit()
        return redirect(request.referrer or url_for('shout.shout_profile', shout_id=shout.id))
    flash('There was an error updating the shout.', 'danger')
    return redirect(request.referrer or url_for('shout.shout_profile', shout_id=shout.id))

@main.route('/shout/<int:shout_id>/manage_participants', methods=['GET', 'POST'])
@login_required
def manage_participants(shout_id):
    shout = Shout.query.get_or_404(shout_id)

    # Fetch current participants and non-participants
    participants = db.session.execute(
        db.select(User, shout_users.c.is_admin)
        .join_from(shout_users, User, shout_users.c.user_id == User.id)
        .where(shout_users.c.shout_id == shout.id)
    ).all()

    non_participants = User.query.filter(User.id.notin_(
        [participant.id for participant, is_admin in participants]
    )).all()

    add_participant_form = AddParticipantForm()
    add_participant_form.new_participant.choices = [(user.id, user.username) for user in non_participants]

    # Handle adding a participant
    if add_participant_form.validate_on_submit():
        selected_user_id = add_participant_form.new_participant.data
        user_to_add = User.query.get_or_404(selected_user_id)

        # Add the user to the shout
        shout.participants.append(user_to_add)
        db.session.commit()

        flash(f'{user_to_add.username} has been added to the shout.', 'success')
        return redirect(url_for('main.manage_participants', shout_id=shout_id))

    return render_template('manage_participants.html', shout=shout, participants=participants,
                           add_participant_form=add_participant_form)

@main.route('/test_page', methods=['GET'])
@login_required  # You can remove this if you want it publicly accessible
def test_page():
    return render_template('blank_template.html')


from .shout_utils import calculate_coffee_stats

@main.route('/stats/<int:shout_id>', methods=['GET'])
@login_required
def stats(shout_id):
    shout, users, coffee_purchases, coffee_received, coffee_ratios = calculate_coffee_stats(shout_id)
    return render_template('stats.html', shout=shout, users=users, coffee_purchases=coffee_purchases, coffee_ratios=coffee_ratios)

@login_required
def toggle_active_status():
    data = request.get_json()
    shout_id = data.get('shout_id')
    is_active = data.get('is_active')

    # Update the active status for the current user in the specified shout
    db.session.execute(
        shout_users.update()
        .where((shout_users.c.user_id == current_user.id) & (shout_users.c.shout_id == shout_id))
        .values(is_active=is_active)
    )
    db.session.commit()
    return jsonify({'success': True})
