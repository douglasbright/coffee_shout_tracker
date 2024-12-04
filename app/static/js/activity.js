// app/static/js/activity.js

document.addEventListener('DOMContentLoaded', function() {
    // Handle comment submission
    document.querySelectorAll('.add-comment-form').forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            const shoutRoundId = this.dataset.shoutRoundId;
            const commentText = this.querySelector('input[name="comment"]').value;
            if (commentText.trim() === '') {
                alert('Comment cannot be empty.');
                return;
            }
            fetch(`/add_comment/${shoutRoundId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ comment: commentText })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Response data:', data); // Log the response data
                if (data.success) {
                    location.reload(); // Reload the page to show the new comment
                } else {
                    alert(data.error);
                }
            });
        });
    });

    // Handle reaction submission
    document.querySelectorAll('.reaction-btn').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const form = this.closest('.reaction-form');
            const shoutRoundId = form.dataset.shoutRoundId;
            const reaction = this.dataset.reaction;
            console.log(`Submitting reaction: ${reaction} for shout round ID: ${shoutRoundId}`); // Log the data being sent
            fetch(`/add_reaction/${shoutRoundId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ reaction: reaction })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Response data:', data); // Log the response data
                if (data.success) {
                    location.reload(); // Reload the page to show the new reaction
                } else {
                    alert(data.error);
                }
            });
        });
    });

    // Handle comment deletion
    document.querySelectorAll('.delete-comment-form').forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            const commentId = this.dataset.commentId;
            fetch(`/delete_comment/${commentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload(); // Reload the page to show the updated comments
                } else {
                    alert(data.error);
                }
            });
        });
    });

    // Handle comment like submission
    document.querySelectorAll('.like-icon').forEach(icon => {
        icon.addEventListener('click', function(event) {
            event.preventDefault();
            const commentId = this.dataset.commentId;
            const likeAction = this.dataset.like;
            fetch(`/like_comment/${commentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ action: likeAction })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Response data:', data); // Log the response data
                if (data.success) {
                    location.reload(); // Reload the page to show the updated likes
                } else {
                    alert(data.error);
                }
            });
        });
    });

    // Handle coffee shop selection
    document.querySelectorAll('.add-coffee-shop-form').forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            const shoutRoundId = this.dataset.shoutRoundId;
            const coffeeShopId = this.querySelector('select[name="coffee_shop_id"]').value;
            if (!coffeeShopId) {
                alert('Please select a coffee shop.');
                return;
            }
            fetch(`/update_coffee_shop/${shoutRoundId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ coffee_shop_id: coffeeShopId })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Response data:', data); // Log the response data
                if (data.success) {
                    location.reload(); // Reload the page to show the updated coffee shop
                } else {
                    alert(data.error);
                }
            });
        });
    });
});