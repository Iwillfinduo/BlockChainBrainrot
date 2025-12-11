document.addEventListener('DOMContentLoaded', function() {
    // Получаем элементы формы
    const form = document.getElementById('register-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    // Функция для отображения и скрытия сообщений об ошибках под полем ввода
    function createErrorMessage(inputElement, message) {
        // Находим старое сообщение об ошибке (если оно есть)
        let errorElement = inputElement.parentNode.querySelector('.error-message-js');

        if (!errorElement) {
            // Если сообщения нет, создаем его
            errorElement = document.createElement('div');
            errorElement.className = 'error-message-js';
            inputElement.parentNode.insertBefore(errorElement, inputElement.nextElementSibling);
        }

        // Обновляем текст
        errorElement.textContent = message;
        // Показываем/скрываем элемент
        errorElement.style.display = message ? 'block' : 'none';

        // Дополнительный класс для стиля поля
        inputElement.classList.toggle('is-invalid', !!message);
    }

    form.addEventListener('submit', function(event) {
        let isValid = true;

        // --- 1. Валидация Имени пользователя ---
        if (usernameInput.value.length < 4) {
            createErrorMessage(usernameInput, "Имя пользователя должно содержать не менее 4 символов.");
            isValid = false;
        } else {
            createErrorMessage(usernameInput, "");
        }

        // --- 2. Валидация Пароля ---
        if (passwordInput.value.length < 8) {
            createErrorMessage(passwordInput, "Пароль должен содержать не менее 8 символов.");
            isValid = false;
        } else {
            createErrorMessage(passwordInput, "");
        }


        // Если хотя бы одно поле невалидно, отменяем отправку формы
        if (!isValid) {
            event.preventDefault();
            // Фокус на первом невалидном поле
            const firstInvalid = [usernameInput, passwordInput].find(input => input.classList.contains('is-invalid'));
            if (firstInvalid) {
                firstInvalid.focus();
            }
        }
    });
});