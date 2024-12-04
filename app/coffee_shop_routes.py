from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from .models import CoffeeShop, ShoutRound, User, Shout, db
from .forms import AddCoffeeShopForm, ReactionForm

coffee_shop = Blueprint('coffee_shop', __name__)

@coffee_shop.route('/add_coffee_shop', methods=['GET', 'POST'])
@login_required
def add_coffee_shop():
    form = AddCoffeeShopForm()
    if form.validate_on_submit():
        new_coffee_shop = CoffeeShop(
            name=form.name.data,
            address=form.address.data
        )
        db.session.add(new_coffee_shop)
        db.session.commit()
        flash('Coffee shop added successfully!', 'success')
        return redirect(url_for('coffee_shop.coffee_shop_profile', coffee_shop_id=new_coffee_shop.id))
    return render_template('add_coffee_shop.html', form=form)

@coffee_shop.route('/coffee_shop/<int:coffee_shop_id>', methods=['GET'])
def coffee_shop_profile(coffee_shop_id):
    coffee_shop = CoffeeShop.query.get_or_404(coffee_shop_id)
    shout_rounds = db.session.query(ShoutRound).join(Shout, ShoutRound.shout_id == Shout.id).join(User, ShoutRound.shouter_id == User.id).filter(
        ShoutRound.coffee_shop_id == coffee_shop_id,
        Shout.is_private == False,
        Shout.comments_public == True,  # Ensure comments are public
        User.is_public == True
    ).order_by(ShoutRound.date.desc()).all()
    reaction_form = ReactionForm()
    return render_template('coffee_shop_profile.html', coffee_shop=coffee_shop, shout_rounds=shout_rounds, reaction_form=reaction_form)