from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .models import Shout, ShoutReaction, ShoutRound, ShoutComment, CommentLike, CoffeeShop, MissedShout, User, db
from .forms import ReactionForm
import logging

activity = Blueprint('activity', __name__)

@activity.route('/activity', methods=['GET'])
@login_required
def activity_feed():
    shout_id = request.args.get('shout_id', type=int)
    sort_by = request.args.get('sort_by', 'date')  # Default sorting by date

    if shout_id:
        shout_rounds_query = ShoutRound.query.filter_by(shout_id=shout_id)
    else:
        shout_rounds_query = ShoutRound.query.join(Shout).filter(Shout.participants.any(id=current_user.id))

    if sort_by == 'date':
        shout_rounds_query = shout_rounds_query.order_by(ShoutRound.date.desc())
    elif sort_by == 'shouter':
        shout_rounds_query = shout_rounds_query.join(User, User.id == ShoutRound.shouter_id).order_by(User.username)
    elif sort_by == 'round_number':
        shout_rounds_query = shout_rounds_query.order_by(ShoutRound.round_number.desc())

    shout_rounds = shout_rounds_query.all()
    shouts = Shout.query.filter(Shout.participants.any(id=current_user.id)).all()
    coffee_shops = CoffeeShop.query.all()  # Fetch all coffee shops
    reaction_form = ReactionForm()
    missed_shouts = MissedShout.query.filter(MissedShout.shout_id.in_([shout.id for shout in shouts])).all()
    return render_template('activity.html', shout_rounds=shout_rounds, shouts=shouts, selected_shout_id=shout_id, reaction_form=reaction_form, coffee_shops=coffee_shops, missed_shouts=missed_shouts, sort_by=sort_by)

@activity.route('/add_comment/<int:shout_round_id>', methods=['POST'])
@login_required
def add_comment(shout_round_id):
    shout_round = ShoutRound.query.get_or_404(shout_round_id)
    shout = shout_round.shout
    if current_user not in shout.participants:
        return jsonify({'error': 'You are not part of this shout.'}), 403

    comment_text = request.form.get('comment')
    if comment_text:
        comment = ShoutComment(user_id=current_user.id, shout_round_id=shout_round_id, text=comment_text)
        db.session.add(comment)
        db.session.commit()
        return jsonify({
            'success': 'Comment added successfully.',
            'comment_id': comment.id,
            'user_id': current_user.id,
            'username': current_user.username,
            'avatar_icon': current_user.avatar_icon
        }), 200
    return jsonify({'error': 'Comment cannot be empty.'}), 400

@activity.route('/add_reaction/<int:shout_round_id>', methods=['POST'])
@login_required
def add_reaction(shout_round_id):
    shout_round = ShoutRound.query.get_or_404(shout_round_id)
    shout = shout_round.shout
    if current_user not in shout.participants:
        return jsonify({'error': 'You are not part of this shout.'}), 403

    form = ReactionForm()
    form.shout_round_id.data = shout_round_id  # Set the shout_round_id in the form
    form.reaction.data = request.form.get('reaction')  # Set the reaction data from the request

    # Log the reaction data for debugging
    logging.debug(f"Reaction data received: {form.reaction.data} for shout_round_id: {shout_round_id}")
    logging.debug(f"Form data: {request.form} for shout_round_id: {shout_round_id}")

    if form.validate_on_submit():
        reaction_type = form.reaction.data
        existing_reaction = ShoutReaction.query.filter_by(user_id=current_user.id, shout_round_id=shout_round_id).first()
        if existing_reaction:
            if existing_reaction.emoji == reaction_type:
                db.session.delete(existing_reaction)
                db.session.commit()
                return jsonify({'success': 'Reaction removed successfully.'}), 200
            else:
                existing_reaction.emoji = reaction_type
                db.session.commit()
                return jsonify({'success': 'Reaction updated successfully.'}), 200
        else:
            reaction = ShoutReaction(user_id=current_user.id, shout_round_id=shout_round_id, emoji=reaction_type)
            db.session.add(reaction)
            db.session.commit()
            return jsonify({'success': 'Reaction added successfully.'}), 200
    else:
        # Log form errors for debugging
        logging.error(f"Form errors: {form.errors} for shout_round_id: {shout_round_id}")
        return jsonify({'error': f'Invalid reaction type: {form.reaction.data}'}), 400

@activity.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = ShoutComment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        return jsonify({'error': 'You do not have permission to delete this comment.'}), 403

    db.session.delete(comment)
    db.session.commit()
    return jsonify({'success': 'Comment deleted successfully.'}), 200

@activity.route('/get_comments/<int:shout_round_id>', methods=['GET'])
@login_required
def get_comments(shout_round_id):
    shout_round = ShoutRound.query.get_or_404(shout_round_id)
    comments = ShoutComment.query.filter_by(shout_round_id=shout_round_id).all()
    return jsonify([{
        'id': comment.id,
        'user_id': comment.user.id,
        'username': comment.user.username,
        'avatar_icon': comment.user.avatar_icon,
        'text': comment.text,
        'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for comment in comments])

# activity_routes.py

@activity.route('/like_comment/<int:comment_id>', methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = ShoutComment.query.get_or_404(comment_id)
    if current_user not in comment.shout_round.shout.participants:
        return jsonify({'error': 'You are not part of this shout.'}), 403

    existing_like = CommentLike.query.filter_by(user_id=current_user.id, comment_id=comment_id).first()
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        return jsonify({'success': 'Like removed successfully.'}), 200
    else:
        like = CommentLike(user_id=current_user.id, comment_id=comment_id)
        db.session.add(like)
        db.session.commit()
        return jsonify({'success': 'Comment liked successfully.'}), 200

@activity.route('/update_coffee_shop/<int:shout_round_id>', methods=['POST'])
@login_required
def update_coffee_shop(shout_round_id):
    shout_round = ShoutRound.query.get_or_404(shout_round_id)
    shout = shout_round.shout
    if current_user not in shout.participants:
        return jsonify({'error': 'You are not part of this shout.'}), 403

    coffee_shop_id = request.form.get('coffee_shop_id')
    if coffee_shop_id:
        coffee_shop = CoffeeShop.query.get(coffee_shop_id)
        if not coffee_shop:
            return jsonify({'error': 'Invalid coffee shop selected.'}), 400
        shout_round.coffee_shop_id = coffee_shop_id
        db.session.commit()
        return jsonify({'success': 'Coffee shop updated successfully.'}), 200
    return jsonify({'error': 'Please select a coffee shop.'}), 400