from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import Quote, db
from .forms import AddQuoteForm, EditQuoteForm

quote = Blueprint('quote', __name__)

# Route for managing quotes (Admin-Only Access)
@quote.route('/manage_quotes', methods=['GET', 'POST'])
@login_required
def manage_quotes():
    # Ensure the user is a global admin
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Forms for adding and editing quotes
    add_quote_form = AddQuoteForm()
    edit_quote_form = EditQuoteForm()

    # Handle adding a new quote
    if add_quote_form.validate_on_submit():
        new_quote = Quote(
            text=add_quote_form.text.data,
            author=add_quote_form.author.data
        )
        db.session.add(new_quote)
        db.session.commit()
        flash('Quote added successfully!', 'success')
        return redirect(url_for('main.manage_quotes'))

    # Fetch all quotes from the database
    quotes = Quote.query.all()

    return render_template('manage_quotes.html', 
                           quotes=quotes, 
                           add_quote_form=add_quote_form, 
                           edit_quote_form=edit_quote_form)

# Route for updating a quote (Admin-Only)
@quote.route('/edit_quote/<int:quote_id>', methods=['POST'])
@login_required
def edit_quote(quote_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    quote = Quote.query.get_or_404(quote_id)
    form = EditQuoteForm()

    if form.validate_on_submit():
        quote.text = form.text.data
        quote.author = form.author.data
        db.session.commit()
        flash('Quote updated successfully.', 'success')
        return redirect(url_for('main.manage_quotes'))

    return render_template('manage_quotes.html', edit_quote_form=form)

# Route for deleting a quote (Admin-Only)
@quote.route('/delete_quote/<int:quote_id>', methods=['POST'])
@login_required
def delete_quote(quote_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    quote = Quote.query.get_or_404(quote_id)
    db.session.delete(quote)
    db.session.commit()
    flash('Quote deleted successfully.', 'success')

    return redirect(url_for('main.manage_quotes'))

from .shout_utils import set_next_shouter