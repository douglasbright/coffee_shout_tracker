// modal_validation.js

document.addEventListener('DOMContentLoaded', function () {
    // Loop over all forms with modal shout forms (assuming each form has a unique id)
    document.querySelectorAll('[id^="editShoutForm"]').forEach(function(form) {
        let newPass = form.querySelector('[id$="new_passcode"]');
        let confirmPass = form.querySelector('[id$="confirm_new_passcode"]');
        let currentPass = form.querySelector('[id$="current_passcode"]'); // Required current PIN field
        let passwordMismatch = form.querySelector('[id^="passwordMismatch"]');
        let submitButton = form.querySelector('[id^="submitShoutForm"]'); // Submit button

        // Real-time validation for password mismatch and required current PIN
        function validateForm() {
            let isPasswordMatch = (!newPass || !confirmPass || newPass.value === confirmPass.value);
            let isCurrentPinFilled = !currentPass || currentPass.value.trim() !== ''; // Check if current PIN is filled

            // Handle password validation
            if (!isPasswordMatch) {
                confirmPass.classList.add('is-invalid');
                if (passwordMismatch) passwordMismatch.style.display = 'block';
            } else if (confirmPass) {
                confirmPass.classList.remove('is-invalid');
                if (passwordMismatch) passwordMismatch.style.display = 'none';
            }

            // Enable or disable the submit button based on password match and current PIN
            if (isPasswordMatch && isCurrentPinFilled) {
                submitButton.disabled = false; // Enable submit button if all conditions are met
            } else {
                submitButton.disabled = true;  // Disable submit button if any condition fails
            }
        }

        if (newPass && confirmPass && currentPass) {
            newPass.addEventListener('input', validateForm);
            confirmPass.addEventListener('input', validateForm);
            currentPass.addEventListener('input', validateForm); // Validate on current PIN change
        }

        // Apply Bootstrap validation styles on form submission
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});
