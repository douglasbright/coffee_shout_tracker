from flask import request, g
import random


def inject_quote():
    # Fetch random quote logic
    from .models import Quote  # Import here to prevent circular imports
    last_quote_id = request.cookies.get('last_quote_id')
    quotes = Quote.query.all()

    if last_quote_id:
        quotes = [quote for quote in quotes if str(quote.id) != last_quote_id]

    random_quote = random.choice(quotes) if quotes else None

    # Set the quote globally
    g.random_quote = random_quote
    return dict(quote=random_quote)

from flask import request


