from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from .models import User, Shout, db, shout_users, ShoutRound, CoffeeShop, MissedShout, UserFavoriteCoffeeShop
from .forms import CreateShoutForm, JoinShoutForm, EditShoutForm, AddParticipantForm, AdminForm, RecordShoutForm, EditShoutRoundForm, EditShoutCommentsForm, AddPinForm, UpdatePinForm, RemovePinForm, SelectFavoriteCoffeeShopForm
from .shout_utils import set_next_shouter, calculate_coffee_stats, record_missed_shout_util, create_new_shout, assign_creator_to_shout, calculate_next_round_number, set_form_choices, preselect_favorite_coffee_shop, handle_form_submission, join_shout_util, join_shout_without_pin_util, leave_shout_util
from datetime import datetime

shout = Blueprint('shout', __name__)

@shout.route('/create_shout', methods=['GET', 'POST'])
@login_required
def create_shout():
    form = CreateShoutForm()
    if form.validate_on_submit():
        new_shout = create_new_shout(
            name=form.name.data,
            workplace=form.workplace.data,
            owner_id=current_user.id,
            is_private=form.is_private.data,
            pin_code=form.pin_code.data if form.pin_code.data else None
        )
        assign_creator_to_shout(
            shout_id=new_shout.id,
            user_id=current_user.id,
            is_admin=True,
            is_active=form.join_shout.data,
            sequence=1
        )
        flash(f'Shout "{new_shout.name}" created successfully! You are the admin.', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('create_shout.html', form=form)

@shout.route('/join_shout', methods=['GET', 'POST'])
@login_required
def join_shout():
    join_form = JoinShoutForm()
    if join_form.validate_on_submit():
        success, message = join_shout_util(
            shout_name=join_form.shout_name.data,
            pin_code=join_form.pin_code.data,
            user_id=current_user.id
        )
        if not success:
            flash(message, 'danger')
            return redirect(url_for('shout.join_shout'))
        flash(message, 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('join_shout.html', form=join_form)

@shout.route('/join_shout_without_pin', methods=['POST'])
@login_required
def join_shout_without_pin():
    data = request.get_json()
    shout_name = data.get('shout_name')
    success, message = join_shout_without_pin_util(
        shout_name=shout_name,
        user_id=current_user.id
    )
    if not success:
        return jsonify({'success': False, 'message': message})
    return jsonify({'success': True, 'redirect_url': url_for('main.dashboard')})

# shout_routes.py

@shout.route('/leave_shout/<int:shout_id>', methods=['POST'])
@login_required
def leave_shout(shout_id):
    success, message = leave_shout_util(shout_id, current_user.id)
    if not success:
        flash(message, 'danger')
        return redirect(url_for('main.dashboard'))
    
    flash(message, 'success')
    return redirect(url_for('main.dashboard'))

@shout.route('/delete_shout/<int:shout_id>', methods=['POST'])
@login_required
def delete_shout(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    shout_participation = db.session.execute(
        shout_users.select().where(
            (shout_users.c.user_id == current_user.id) & 
            (shout_users.c.shout_id == shout_id)
        )
    ).first()
    if not shout_participation or not shout_participation.is_admin:
        flash('You do not have permission to delete this shout.', 'danger')
        return redirect(url_for('main.dashboard'))
    db.session.delete(shout)
    db.session.commit()
    flash('Shout deleted successfully.', 'success')
    return redirect(url_for('main.dashboard'))

# shout_routes.py

@shout.route('/record_shout/<int:shout_id>', methods=['GET', 'POST'])
@login_required
def record_shout(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    if current_user not in shout.participants:
        flash('You are not a participant in this shout.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = RecordShoutForm()
    set_form_choices(form, shout)
    
    # Calculate the next round number for this shout
    next_round_number = calculate_next_round_number(shout.id)
    
    if request.method == 'GET':
        if shout.current_shouter_id:
            form.shouter.data = shout.current_shouter_id
            form.attendees.data = [shout.current_shouter_id]
        
        # Preselect the favorite coffee shop if available
        preselect_favorite_coffee_shop(form, current_user.id, shout_id)
    
    if form.validate_on_submit():
        handle_form_submission(form, shout, next_round_number)
        flash('Shout recorded successfully.', 'success')
        return redirect(url_for('activity.activity_feed', shout_id=shout.id, sort_by='round_number'))
    
    return render_template('record_shout.html', form=form, shout=shout, next_round_number=next_round_number)
    
    return render_template('record_shout.html', form=form, shout=shout, next_round_number=next_round_number)


@shout.route('/shout/<int:shout_id>', methods=['GET', 'POST'])
@login_required
def shout_profile(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    participants = db.session.execute(
        db.select(User, shout_users.c.is_admin)
        .join_from(shout_users, User, shout_users.c.user_id == User.id)
        .where(shout_users.c.shout_id == shout.id)
        .where(shout_users.c.is_active == True) 
        .order_by(shout_users.c.sequence)
    ).all()
    active_participants = [participant for participant, is_admin in participants]
    
    # Determine if the current user is an admin without checking their active status
    user_is_admin = db.session.execute(
        db.select(shout_users.c.is_admin)
        .where(shout_users.c.user_id == current_user.id)
        .where(shout_users.c.shout_id == shout.id)
        .where(shout_users.c.is_admin == True)
    ).scalar()
    
    # Calculate coffee stats
    shout, users, coffee_purchases, coffee_received, coffee_ratios = calculate_coffee_stats(shout_id)
    
    # Prepare data for the pie chart
    coffee_purchases_labels = [user.username for user in users]
    coffee_purchases_data = [sum(coffee_purchases[user.id].values()) for user in users]
    
    # Get the current shouter
    current_shouter = db.session.query(User).filter_by(id=shout.current_shouter_id).first()
    
    # Get the user's favorite coffee shop for this shout
    favorite_coffee_shop = UserFavoriteCoffeeShop.query.filter_by(user_id=current_user.id, shout_id=shout_id).first()
    
    # Instantiate the form for selecting a favorite coffee shop
    form = SelectFavoriteCoffeeShopForm()
    form.coffee_shop.choices = [(shop.id, shop.name) for shop in CoffeeShop.query.all()]
    if favorite_coffee_shop:
        form.coffee_shop.data = favorite_coffee_shop.coffee_shop_id
    
    return render_template(
        'shout_profile.html',
        shout=shout,
        participants=participants,
        active_participants=active_participants,
        user_is_admin=user_is_admin,
        users=users,
        coffee_purchases=coffee_purchases,
        coffee_received=coffee_received,
        coffee_ratios=coffee_ratios,
        current_shouter=current_shouter,
        favorite_coffee_shop=favorite_coffee_shop,
        form=form,
        coffee_purchases_labels=coffee_purchases_labels,
        coffee_purchases_data=coffee_purchases_data
    )

@shout.route('/shout/<int:shout_id>/manage_sequence', methods=['GET', 'POST'])
@login_required
def manage_sequence(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    shout_participation = db.session.execute(
        shout_users.select().where(
            (shout_users.c.user_id == current_user.id) & 
            (shout_users.c.shout_id == shout_id) & 
            (shout_users.c.is_admin == True)
        )
    ).first()
    if not shout_participation:
        flash('You do not have permission to manage the sequence.', 'danger')
        return redirect(url_for('shout.shout_profile', shout_id=shout_id))
    active_participants = db.session.execute(
        db.select(User, shout_users.c.sequence)
        .join_from(shout_users, User, shout_users.c.user_id == User.id)
        .where(shout_users.c.shout_id == shout.id)
        .where(shout_users.c.is_active == True)
        .order_by(shout_users.c.sequence)
    ).all()
    if request.method == 'POST':
        new_sequence = request.form.getlist('sequence[]')
        for index, user_id in enumerate(new_sequence):
            db.session.execute(
                shout_users.update()
                .where(shout_users.c.user_id == user_id)
                .where(shout_users.c.shout_id == shout_id)
                .values(sequence=index + 1)
            )
        db.session.commit()
        flash('Sequence updated successfully.', 'success')
        return redirect(url_for('shout.shout_profile', shout_id=shout_id))
    return render_template('manage_sequence.html', shout=shout, active_participants=active_participants)

@shout.route('/manage_shouts', methods=['GET', 'POST'])
@login_required
def manage_shouts():
    # Fetch all shouts
    shouts = Shout.query.all()

    # Create a form instance for each shout, passing the shout object
    shout_forms = {shout.id: EditShoutForm(shout=shout, obj=shout) for shout in shouts}

    # Dictionary to store participants and admins for each shout
    participants_by_shout = {}
    admins_by_shout = {}

    for shout in shouts:
        # Fetch participants (both active and inactive users) and their admin status
        participants = db.session.execute(
            db.select(User, shout_users.c.is_admin, shout_users.c.is_active)
            .join_from(shout_users, User, shout_users.c.user_id == User.id)
            .where(shout_users.c.shout_id == shout.id)
        ).all()

        # Fetch admins (both active and inactive users)
        admins = db.session.execute(
            db.select(User)
            .join_from(shout_users, User, shout_users.c.user_id == User.id)
            .where(shout_users.c.shout_id == shout.id)
            .where(shout_users.c.is_admin == True)  # Admins, regardless of active status
        ).scalars().all()

        # Store participants and admins for each shout
        participants_by_shout[shout.id] = participants
        admins_by_shout[shout.id] = admins

    # Handle form submissions
    if request.method == 'POST':
        shout_id = request.form.get('shout_id')  # Hidden input in the form to identify the shout
        form = shout_forms.get(int(shout_id))

        if form and form.validate_on_submit():
            # Get the shout to be updated
            shout = Shout.query.get_or_404(shout_id)

            # Update shout details from the form
            shout.name = form.name.data
            shout.workplace = form.workplace.data
            shout.is_private = form.is_private.data

            # Update passcode if provided
            if form.passcode.data:
                shout.set_pin_code(form.passcode.data)

            db.session.commit()
            flash(f'Shout "{shout.name}" updated successfully.', 'success')

        return redirect(url_for('shout.manage_shouts'))

    return render_template('manage_shouts.html', 
                           shouts=shouts, 
                           shout_forms=shout_forms, 
                           participants_by_shout=participants_by_shout, 
                           admins_by_shout=admins_by_shout)

@shout.route('/check_shout_pin')
@login_required
def check_shout_pin():
    shout_name = request.args.get('shout_name')
    shout = Shout.query.filter_by(name=shout_name).first()
    if shout:
        return jsonify({'requires_pin': bool(shout.pin_code_hash)})
    return jsonify({'requires_pin': False})

@shout.route('/join_shout_with_pin', methods=['POST'])
@login_required
def join_shout_with_pin():
    data = request.get_json()
    shout_name = data.get('shout_name')
    pin_code = data.get('pin_code')
    success, message = join_shout_util(
        shout_name=shout_name,
        pin_code=pin_code,
        user_id=current_user.id
    )
    if not success:
        return jsonify({'success': False, 'message': message})
    return jsonify({'success': True, 'redirect_url': url_for('main.dashboard')})

@shout.route('/shout/<int:shout_id>/toggle_active_status', methods=['POST'])
@login_required
def toggle_active_status(shout_id):
    data = request.get_json()
    is_active = data.get('is_active')
    db.session.execute(
        shout_users.update()
        .where((shout_users.c.user_id == current_user.id) & (shout_users.c.shout_id == shout_id))
        .values(is_active=is_active)
    )
    db.session.commit()
    return jsonify({'success': True, 'message': 'Active status updated successfully.'})

@shout.route('/edit_shout_round/<int:shout_round_id>', methods=['GET', 'POST'])
@login_required
def edit_shout_round(shout_round_id):
    shout_round = ShoutRound.query.get_or_404(shout_round_id)
    shout = shout_round.shout
    if current_user not in shout.participants:
        flash('You are not a participant in this shout.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = EditShoutRoundForm()
    form.shouter.choices = [(user.id, user.username) for user in shout.participants]
    form.attendees.choices = [(user.id, user.username) for user in shout.participants]
    form.coffee_shop.choices += [(shop.id, shop.name) for shop in CoffeeShop.query.all()]

    if request.method == 'GET':
        form.shouter.data = shout_round.shouter_id
        form.attendees.data = [attendee.id for attendee in shout_round.attendees]
        form.date.data = shout_round.date
        form.coffee_shop.data = shout_round.coffee_shop_id if shout_round.coffee_shop_id else 0

    if form.validate_on_submit():
        shout_round.shouter_id = form.shouter.data
        shout_round.attendees = User.query.filter(User.id.in_(form.attendees.data)).all()
        shout_round.date = form.date.data
        shout_round.coffee_shop_id = form.coffee_shop.data if form.coffee_shop.data != 0 else None
        db.session.commit()
        flash('Shout round updated successfully.', 'success')
        return redirect(url_for('shout.shout_profile', shout_id=shout.id))
    
    return render_template('edit_shout_round.html', form=form, shout_round=shout_round)

@shout.route('/shout/<int:shout_id>/admin', methods=['GET', 'POST'])
@login_required
def shout_admin(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    
    # Determine if the current user is an admin without checking their active status
    user_is_admin = db.session.execute(
        db.select(shout_users.c.is_admin)
        .where(shout_users.c.user_id == current_user.id)
        .where(shout_users.c.shout_id == shout.id)
        .where(shout_users.c.is_admin == True)
    ).scalar()
    
    if not user_is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('shout.shout_profile', shout_id=shout.id))
    
    edit_shout_form = EditShoutForm(shout=shout, obj=shout)
    admin_form = AdminForm()
    edit_comments_form = EditShoutCommentsForm(obj=shout)
    add_pin_form = AddPinForm()
    update_pin_form = UpdatePinForm()
    remove_pin_form = RemovePinForm()
    
    if edit_shout_form.validate_on_submit():
        shout.name = edit_shout_form.name.data
        shout.workplace = edit_shout_form.workplace.data
        shout.is_private = edit_shout_form.is_private.data
        if edit_shout_form.new_passcode.data:
            shout.set_pin_code(edit_shout_form.new_passcode.data)
        db.session.commit()
        flash('Shout details updated successfully.', 'success')
        return redirect(url_for('shout.shout_admin', shout_id=shout.id))
    
    if edit_comments_form.validate_on_submit():
        shout.comments_public = edit_comments_form.comments_public.data
        db.session.commit()
        flash('Shout comments visibility updated successfully.', 'success')
        return redirect(url_for('shout.shout_admin', shout_id=shout.id))
    
    return render_template(
        'shout_admin.html',
        shout=shout,
        edit_shout_form=edit_shout_form,
        admin_form=admin_form,
        edit_comments_form=edit_comments_form,
        add_pin_form=add_pin_form,
        update_pin_form=update_pin_form,
        remove_pin_form=remove_pin_form
    )

@shout.route('/shout/<int:shout_id>/toggle_private_shout', methods=['POST'])
@login_required
def toggle_private_shout(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    user_is_admin = db.session.execute(
        db.select(shout_users.c.is_admin)
        .where(shout_users.c.user_id == current_user.id)
        .where(shout_users.c.shout_id == shout.id)
        .where(shout_users.c.is_admin == True)
    ).scalar()
    
    if not user_is_admin:
        return jsonify({'success': False, 'message': 'You do not have permission to perform this action.'})
    
    data = request.get_json()
    shout.is_private = data.get('is_private', shout.is_private)
    db.session.commit()
    return jsonify({'success': True})

@shout.route('/shout/<int:shout_id>/toggle_comments_visibility', methods=['POST'])
@login_required
def toggle_comments_visibility(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    user_is_admin = db.session.execute(
        db.select(shout_users.c.is_admin)
        .where(shout_users.c.user_id == current_user.id)
        .where(shout_users.c.shout_id == shout.id)
        .where(shout_users.c.is_admin == True)
    ).scalar()
    
    if not user_is_admin:
        return jsonify({'success': False, 'message': 'You do not have permission to perform this action.'})
    
    data = request.get_json()
    shout.comments_public = data.get('comments_public', shout.comments_public)
    db.session.commit()
    return jsonify({'success': True})

@shout.route('/shout/<int:shout_id>/add_pin', methods=['POST'])
@login_required
def add_shout_pin(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    user_is_admin = db.session.execute(
        db.select(shout_users.c.is_admin)
        .where(shout_users.c.user_id == current_user.id)
        .where(shout_users.c.shout_id == shout.id)
        .where(shout_users.c.is_admin == True)
    ).scalar()
    
    if not user_is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('shout.shout_admin', shout_id=shout.id))
    
    form = AddPinForm()
    if form.validate_on_submit():
        shout.set_pin_code(form.new_pin.data)
        db.session.commit()
        flash('PIN added successfully.', 'success')
    else:
        flash('Failed to add PIN.', 'danger')
    
    return redirect(url_for('shout.shout_admin', shout_id=shout.id))

@shout.route('/shout/<int:shout_id>/update_pin', methods=['POST'])
@login_required
def update_shout_pin(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    user_is_admin = db.session.execute(
        db.select(shout_users.c.is_admin)
        .where(shout_users.c.user_id == current_user.id)
        .where(shout_users.c.shout_id == shout.id)
        .where(shout_users.c.is_admin == True)
    ).scalar()
    
    if not user_is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('shout.shout_admin', shout_id=shout.id))
    
    form = UpdatePinForm()
    if form.validate_on_submit():
        if not shout.check_pin_code(form.current_pin.data):
            flash('Incorrect current PIN.', 'danger')
        else:
            shout.set_pin_code(form.new_pin.data)
            db.session.commit()
            flash('PIN updated successfully.', 'success')
    else:
        flash('Failed to update PIN.', 'danger')
    
    return redirect(url_for('shout.shout_admin', shout_id=shout.id))

@shout.route('/shout/<int:shout_id>/remove_pin', methods=['POST'])
@login_required
def remove_shout_pin(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    user_is_admin = db.session.execute(
        db.select(shout_users.c.is_admin)
        .where(shout_users.c.user_id == current_user.id)
        .where(shout_users.c.shout_id == shout.id)
        .where(shout_users.c.is_admin == True)
    ).scalar()
    
    if not user_is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('shout.shout_admin', shout_id=shout.id))
    
    form = RemovePinForm()
    if form.validate_on_submit():
        if not shout.check_pin_code(form.current_pin.data):
            flash('Incorrect current PIN.', 'danger')
        else:
            shout.pin_code_hash = None
            db.session.commit()
            flash('PIN removed successfully.', 'success')
    else:
        flash('Failed to remove PIN.', 'danger')
    
    return redirect(url_for('shout.shout_admin', shout_id=shout.id))

@shout.route('/shout/<int:shout_id>/edit_workplace', methods=['POST'])
@login_required
def edit_workplace(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    form = EditShoutForm(shout=shout)
    if form.validate_on_submit():
        shout.workplace = form.workplace.data
        db.session.commit()
        flash('Workplace updated successfully.', 'success')
    else:
        flash('There was an error updating the workplace.', 'danger')
    return redirect(url_for('shout.shout_admin', shout_id=shout.id))

@shout.route('/shout/<int:shout_id>/edit_name', methods=['POST'])
@login_required
def edit_shout_name(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    form = EditShoutForm(shout=shout)
    if form.validate_on_submit():
        shout.name = form.name.data
        db.session.commit()
        flash('Shout name updated successfully.', 'success')
    else:
        flash('There was an error updating the shout name.', 'danger')
    return redirect(url_for('shout.shout_admin', shout_id=shout.id))

@shout.route('/record_missed_shout/<int:shout_id>', methods=['POST'])
@login_required
def record_missed_shout(shout_id):
    success, message = record_missed_shout_util(shout_id, current_user)
    if not success:
        flash(message, 'danger')
        return redirect(url_for('main.dashboard'))
    
    flash(message, 'success')
    return redirect(url_for('shout.shout_profile', shout_id=shout_id))

@shout.route('/shout/<int:shout_id>/select_favorite_coffee_shop', methods=['GET', 'POST'])
@login_required
def select_favorite_coffee_shop(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    form = SelectFavoriteCoffeeShopForm()
    form.coffee_shop.choices = [(shop.id, shop.name) for shop in CoffeeShop.query.all()]

    # Preselect the favorite coffee shop if available (commented out for testing)
    # favorite = UserFavoriteCoffeeShop.query.filter_by(user_id=current_user.id, shout_id=shout_id).first()
    # if favorite:
    #     form.coffee_shop.data = favorite.coffee_shop_id

    if form.validate_on_submit():
        print("Form Data:", form.data)  # Debugging statement
        print("Selected Coffee Shop ID:", form.coffee_shop.data)  # Debugging statement
        
        favorite = UserFavoriteCoffeeShop.query.filter_by(user_id=current_user.id, shout_id=shout_id).first()
        if favorite:
            favorite.coffee_shop_id = form.coffee_shop.data
        else:
            favorite = UserFavoriteCoffeeShop(user_id=current_user.id, shout_id=shout_id, coffee_shop_id=form.coffee_shop.data)
            db.session.add(favorite)
        db.session.commit()
        flash('Favorite coffee shop updated successfully.', 'success')
        return redirect(url_for('shout.shout_profile', shout_id=shout_id))

    return render_template('select_favorite_coffee_shop.html', form=form, shout=shout)

@shout.route('/shout/<int:shout_id>/calendar', methods=['GET'])
@login_required
def shout_calendar(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    shout_rounds = ShoutRound.query.filter_by(shout_id=shout_id).all()
    return render_template('shout_calendar.html', shout=shout, shout_rounds=shout_rounds)

@shout.route('/shout/<int:shout_id>/settings', methods=['GET', 'POST'])
@login_required
def user_shout_settings(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    shout_participation = db.session.execute(
        shout_users.select().where(
            (shout_users.c.user_id == current_user.id) & 
            (shout_users.c.shout_id == shout_id)
        )
    ).first()
    
    if not shout_participation:
        flash('You are not a participant in this shout.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Handle form submissions for toggling comment visibility
        if 'toggle_comment_visibility' in request.form:
            comments_public = request.form.get('comments_public') == 'on'
            shout.comments_public = comments_public
            db.session.commit()
            flash('Comment visibility updated successfully.', 'success')
        
        if 'leave_shout' in request.form:
            success, message = leave_shout_util(shout_id, current_user.id)
            if not success:
                flash(message, 'danger')
                return redirect(url_for('main.dashboard'))
            flash(message, 'success')
            return redirect(url_for('main.dashboard'))
    
    return render_template('user_shout_settings.html', shout=shout, shout_participation=shout_participation)

