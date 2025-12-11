document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('login-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    function createErrorMessage(inputElement, message) {
        // Удаляем старые сообщения об ошибках для этого поля
        const oldError = inputElement.nextElementSibling;
        if (oldError && oldError.classList.contains('error-message-js')) {
            oldError.remove();
        }

        if (message) {
            // Создаем новый элемент для сообщения об ошибке
            const errorElement = document.createElement('div');
            errorElement.className = 'error-message-js';
            errorElement.textContent = message;
            inputElement.parentNode.insertBefore(errorElement, inputElement.nextElementSibling);
        }
    }

    form.addEventListener('submit', function(event) {
        let isValid = true;

        // 1. Валидация имени пользователя
        if (usernameInput.value.length < 4) {
            createErrorMessage(usernameInput, "Имя пользователя должно содержать не менее 4 символов.");
            isValid = false;
        } else {
            createErrorMessage(usernameInput, ""); // Очистка ошибки
        }

        // 2. Валидация пароля
        if (passwordInput.value.length < 8) {
            createErrorMessage(passwordInput, "Пароль должен содержать не менее 8 символов.");
            isValid = false;
        } else {
            createErrorMessage(passwordInput, ""); // Очистка ошибки
        }

        // Если невалидно, предотвращаем отправку формы на сервер
        if (!isValid) {
            event.preventDefault();
            // Фокусируемся на первом невалидном поле
            if (usernameInput.value.length < 4) {
                usernameInput.focus();
            } else if (passwordInput.value.length < 8) {
                passwordInput.focus();
            }
        }
    });
});