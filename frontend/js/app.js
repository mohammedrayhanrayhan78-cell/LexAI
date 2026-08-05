import { initThemeToggle } from './theme.js';
import { checkBackendHealth } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
    checkBackendHealth();
    
    const sendBtn = document.getElementById('send-btn');
    const userInput = document.getElementById('user-input');

    sendBtn.addEventListener('click', () => {
        const text = userInput.value.trim();
        if (text) {
            console.log("Message submitted:", text);
            userInput.value = '';
        }
    });
});