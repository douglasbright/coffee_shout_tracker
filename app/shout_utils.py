from datetime import datetime
from .models import db, Shout, User, shout_users, ShoutRound, MissedShout, CoffeeShop, UserFavoriteCoffeeShop


def set_next_shouter(shout_id):
    shout = Shout.query.get(shout_id)
    if not shout:
        return

    # Ensure all users have a sequence number
    participants_without_sequence = db.session.query(User).join(shout_users).filter(
        shout_users.c.shout_id == shout.id,
        shout_users.c.sequence == None
    ).all()
    if participants_without_sequence:
        max_sequence = db.session.query(db.func.max(shout_users.c.sequence)).filter_by(shout_id=shout.id).scalar()
        next_sequence = (max_sequence or 0) + 1
        for participant in participants_without_sequence:
            db.session.execute(
                shout_users.update().where(
                    shout_users.c.shout_id == shout.id,
                    shout_users.c.user_id == participant.id
                ).values(sequence=next_sequence)
            )
            next_sequence += 1
        db.session.commit()

    # Get the current shouter with sequence
    current_shouter = db.session.query(User, shout_users.c.sequence).join(shout_users).filter(
        shout_users.c.shout_id == shout.id,
        shout_users.c.user_id == User.id,
        shout_users.c.is_active == True,
        shout_users.c.user_id == shout.current_shouter_id
    ).first()

    if not current_shouter:
        # If no current shouter, set the first user in the sequence as the current shouter
        next_shouter = db.session.query(User).join(shout_users).filter(
            shout_users.c.shout_id == shout.id,
            shout_users.c.is_active == True,
            shout_users.c.is_available_for_shout == True
        ).order_by(shout_users.c.sequence).first()
        if next_shouter:
            shout.current_shouter_id = next_shouter.id
            db.session.commit()
        return

    current_shouter_user, current_shouter_sequence = current_shouter

    # Mark the current shouter's is_available_for_shout as False
    db.session.execute(
        shout_users.update().where(
            shout_users.c.shout_id == shout.id,
            shout_users.c.user_id == current_shouter_user.id
        ).values(is_available_for_shout=False)
    )
    db.session.commit()

    # Get the next active user in the sequence who is available for a shout and has catch-up due
    next_shouter = db.session.query(User).join(shout_users).filter(
        shout_users.c.shout_id == shout.id,
        shout_users.c.is_active == True,
        shout_users.c.is_available_for_shout == True,
        shout_users.c.is_catchup_due == True,
        shout_users.c.sequence > current_shouter_sequence
    ).order_by(shout_users.c.sequence).first()

    # If no next shouter with catch-up due found, get the next active user in the sequence who is available for a shout
    if not next_shouter:
        next_shouter = db.session.query(User).join(shout_users).filter(
            shout_users.c.shout_id == shout.id,
            shout_users.c.is_active == True,
            shout_users.c.is_available_for_shout == True,
            shout_users.c.sequence > current_shouter_sequence
        ).order_by(shout_users.c.sequence).first()

    # If no next shouter found, wrap around to the first user in the sequence who is available for a shout and has catch-up due
    if not next_shouter:
        next_shouter = db.session.query(User).join(shout_users).filter(
            shout_users.c.shout_id == shout.id,
            shout_users.c.is_active == True,
            shout_users.c.is_available_for_shout == True,
            shout_users.c.is_catchup_due == True
        ).order_by(shout_users.c.sequence).first()

    # If no next shouter with catch-up due found, wrap around to the first user in the sequence who is available for a shout
    if not next_shouter:
        next_shouter = db.session.query(User).join(shout_users).filter(
            shout_users.c.shout_id == shout.id,
            shout_users.c.is_active == True,
            shout_users.c.is_available_for_shout == True
        ).order_by(shout_users.c.sequence).first()

    # Update the current shouter
    if next_shouter:
        shout.current_shouter_id = next_shouter.id
        db.session.commit()

    # Reset is_available_for_shout for all users if all have been scheduled
    all_users_scheduled = db.session.query(shout_users).filter(
        shout_users.c.shout_id == shout.id,
        shout_users.c.is_available_for_shout == True
    ).count() == 0

    if all_users_scheduled:
        db.session.execute(
            shout_users.update().where(
                shout_users.c.shout_id == shout.id
            ).values(is_available_for_shout=True)
        )
        db.session.commit()

def calculate_coffee_stats(shout_id):
    shout = Shout.query.get_or_404(shout_id)
    users = shout.participants  # Get the participants of the shout

    # Initialize a dictionary to store coffee purchases and received
    coffee_purchases = {user.id: {recipient.id: 0 for recipient in users} for user in users}
    coffee_received = {user.id: {purchaser.id: 0 for purchaser in users} for user in users}

    # Calculate coffee purchases for each shout round
    for round in shout.rounds:
        for attendee in round.attendees:
            if round.shouter_id not in coffee_purchases:
                coffee_purchases[round.shouter_id] = {}
            if attendee.id not in coffee_purchases[round.shouter_id]:
                coffee_purchases[round.shouter_id][attendee.id] = 0
            coffee_purchases[round.shouter_id][attendee.id] += 1
            if attendee.id not in coffee_received:
                coffee_received[attendee.id] = {}
            if round.shouter_id not in coffee_received[attendee.id]:
                coffee_received[attendee.id][round.shouter_id] = 0
            coffee_received[attendee.id][round.shouter_id] += 1

    # Calculate the ratio of coffees purchased versus received
    coffee_ratios = {}
    for user in users:
        coffee_ratios[user.id] = {}
        for other_user in users:
            purchased = coffee_purchases[user.id].get(other_user.id, 0)
            received = coffee_received[user.id].get(other_user.id, 0)
            ratio = purchased / received if received != 0 else purchased
            coffee_ratios[user.id][other_user.id] = ratio

    return shout, users, coffee_purchases, coffee_received, coffee_ratios


def record_missed_shout_util(shout_id, current_user):
    shout = Shout.query.get(shout_id)
    if not shout or current_user not in shout.participants:
        return False, 'You are not a participant in this shout.'
    
    current_shouter = db.session.query(User).filter_by(id=shout.current_shouter_id).first()
    if not current_shouter:
        return False, 'No current shouter assigned.'
    
    # Calculate the next round number
    max_round_number = db.session.query(db.func.max(ShoutRound.round_number)).filter_by(shout_id=shout.id).scalar()
    next_round_number = (max_round_number or 0) + 1
    
    # Record the missed shout
    missed_shout = MissedShout(
        user_id=current_shouter.id,
        shout_id=shout.id,
        round_number=next_round_number  # Store the next round number
    )
    db.session.add(missed_shout)
    db.session.commit()
    
    # Set is_catchup_due to True and is_available_for_shout to False for the missed shouter
    db.session.execute(
        shout_users.update().where(
            shout_users.c.shout_id == shout.id,
            shout_users.c.user_id == current_shouter.id
        ).values(is_catchup_due=True, is_available_for_shout=False)
    )
    db.session.commit()
    
    # Set the next shouter
    set_next_shouter(shout.id)
    
    return True, f'{current_shouter.username} has been recorded as absent for their allocated shout.'

def create_new_shout(name, workplace, owner_id, is_private, pin_code):
    new_shout = Shout(
        name=name,
        workplace=workplace,
        owner_id=owner_id,
        is_private=is_private
    )
    if pin_code:
        new_shout.set_pin_code(pin_code)
    db.session.add(new_shout)
    db.session.commit()
    return new_shout

def assign_creator_to_shout(shout_id, user_id, is_admin=True, is_active=True, sequence=1):
    stmt = shout_users.insert().values(
        user_id=user_id,
        shout_id=shout_id,
        is_admin=is_admin,
        is_active=is_active,
        sequence=sequence
    )
    db.session.execute(stmt)
    db.session.commit()

    
def calculate_next_round_number(shout_id):
        max_round_number = db.session.query(db.func.max(ShoutRound.round_number)).filter_by(shout_id=shout_id).scalar()
        return (max_round_number or 0) + 1
    
def set_form_choices(form, shout):
        form.shouter.choices = [(user.id, user.username) for user in shout.participants]
        form.attendees.choices = [(user.id, user.username) for user in shout.participants]
        form.coffee_shop.choices += [(shop.id, shop.name) for shop in CoffeeShop.query.all()]
    
def preselect_favorite_coffee_shop(form, user_id, shout_id):
        favorite = UserFavoriteCoffeeShop.query.filter_by(user_id=user_id, shout_id=shout_id).first()
        if favorite:
            form.coffee_shop.data = favorite.coffee_shop_id
    
def handle_form_submission(form, shout, next_round_number, recorded_by_id):
    try:
        shout_round = ShoutRound(
            shout_id=shout.id,
            shouter_id=form.shouter.data,
            date=form.date.data,
            coffee_shop_id=form.coffee_shop.data if form.coffee_shop.data != 0 else None,
            round_number=next_round_number,
            recorded_by_id=recorded_by_id  # Set the recorded_by_id field
        )
        shout_round.attendees = User.query.filter(User.id.in_(form.attendees.data)).all()
        db.session.add(shout_round)
        db.session.commit()
        
        # Mark the shouter's is_available_for_shout as False and reset is_catchup_due
        db.session.execute(
            shout_users.update().where(
                shout_users.c.shout_id == shout.id,
                shout_users.c.user_id == form.shouter.data
            ).values(is_available_for_shout=False, is_catchup_due=False)
        )
        db.session.commit()
        
        set_next_shouter(shout.id)
        return shout_round
    except Exception as e:
        print(f"Error in handle_form_submission: {e}")
        return None


def join_shout_util(shout_name, pin_code, user_id):
    print(f"join_shout_util called with shout_name={shout_name}, pin_code={pin_code}, user_id={user_id}")
    shout_to_join = Shout.query.filter_by(name=shout_name).first()
    if not shout_to_join:
        print("Shout not found.")
        return False, 'Shout not found.'
    if shout_to_join.pin_code_hash:
        if not shout_to_join.check_pin_code(pin_code):
            print("Incorrect PIN code.")
            return False, 'Incorrect PIN code.'
    if user_id in [participant.id for participant in shout_to_join.participants]:
        print("User is already a participant in this shout.")
        return False, 'You are already a participant in this shout.'
    max_sequence = db.session.query(db.func.max(shout_users.c.sequence)).filter_by(shout_id=shout_to_join.id).scalar()
    next_sequence = (max_sequence or 0) + 1
    stmt = shout_users.insert().values(
        user_id=user_id,
        shout_id=shout_to_join.id,
        is_active=True,
        sequence=next_sequence
    )
    db.session.execute(stmt)
    db.session.commit()
    print(f"User {user_id} joined the shout {shout_to_join.name}.")
    return True, f'You have joined the shout "{shout_to_join.name}".'

def join_shout_without_pin_util(shout_name, user_id):
    print(f"join_shout_without_pin_util called with shout_name={shout_name}, user_id={user_id}")
    shout_to_join = Shout.query.filter_by(name=shout_name).first()
    if not shout_to_join:
        print("Shout not found.")
        return False, 'Shout not found.'
    if shout_to_join.pin_code_hash:
        print("This shout requires a PIN code.")
        return False, 'This shout requires a PIN code.'
    if user_id in [participant.id for participant in shout_to_join.participants]:
        print("User is already a participant in this shout.")
        return False, 'You are already a participant in this shout.'
    max_sequence = db.session.query(db.func.max(shout_users.c.sequence)).filter_by(shout_id=shout_to_join.id).scalar()
    next_sequence = (max_sequence or 0) + 1
    stmt = shout_users.insert().values(
        user_id=user_id,
        shout_id=shout_to_join.id,
        is_active=True,
        sequence=next_sequence
    )
    db.session.execute(stmt)
    db.session.commit()
    print(f"User {user_id} joined the shout {shout_to_join.name}.")
    return True, f'You have joined the shout "{shout_to_join.name}".'


def leave_shout_util(shout_id, user_id):
    shout = Shout.query.get(shout_id)
    if not shout or user_id not in [participant.id for participant in shout.participants]:
        return False, 'You are not part of this shout.'
    
    shout_participation = db.session.execute(
        shout_users.select().where(
            (shout_users.c.user_id == user_id) & 
            (shout_users.c.shout_id == shout_id)
        )
    ).first()
    
    if shout_participation and shout_participation.is_admin:
        other_admins = db.session.execute(
            shout_users.select().where(
                (shout_users.c.shout_id == shout_id) & 
                (shout_users.c.is_admin == True) & 
                (shout_users.c.user_id != user_id)
            )
        ).fetchall()
        if not other_admins:
            return False, 'You cannot leave the shout as the only admin.'
    
    shout.participants.remove(User.query.get(user_id))
    db.session.commit()
    return True, 'You have successfully left the shout.'