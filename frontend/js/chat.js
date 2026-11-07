import { initThemeToggle } from './theme.js';
import { attachTTSHandler } from './voice.js';
import { API_BASE } from './config.js';

document.addEventListener('DOMContentLoaded', async () => {
    initThemeToggle();

    let token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    const conversationListEl = document.getElementById('conversation-list');
    const chatWindowEl = document.getElementById('chat-window');
    const chatTitleEl = document.getElementById('chat-title');
    const userInputEl = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const userEmailDisplay = document.getElementById('user-email-display');
    
    const attachImageBtn = document.getElementById('attach-image-btn');
    const imageFileInput = document.getElementById('image-file-input');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreviewThumb = document.getElementById('image-preview-thumb');
    const removeImageBtn = document.getElementById('remove-image-btn');

    let currentConversationId = null;
    let selectedImageFile = null;

    async function tryRefreshToken() {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return null;
        try {
            const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
            if (!res.ok) return null;
            const data = await res.json();
            localStorage.setItem('access_token', data.access_token);
            if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token);
            return data.access_token;
        } catch {
            return null;
        }
    }

    let currentToken = token;
    try {
        let userRes = await fetch(`${API_BASE}/api/v1/auth/me`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        if (userRes.status === 401) {
            const newToken = await tryRefreshToken();
            if (newToken) {
                currentToken = newToken;
                userRes = await fetch(`${API_BASE}/api/v1/auth/me`, {
                    headers: { 'Authorization': `Bearer ${currentToken}` }
                });
            }
        }
        if (userRes.ok) {
            const userData = await userRes.json();
            userEmailDisplay.textContent = userData.email;
        } else {
            localStorage.clear();
            window.location.href = 'login.html';
            return;
        }
    } catch (err) {
        console.error('Auth verification failed:', err);
    }

    attachImageBtn.addEventListener('click', () => imageFileInput.click());

    imageFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                alert('Please select a valid image file.');
                return;
            }
            selectedImageFile = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreviewThumb.src = e.target.result;
                imagePreviewContainer.style.display = 'flex';
            };
            reader.readAsDataURL(file);
        }
    });

    removeImageBtn.addEventListener('click', () => {
        selectedImageFile = null;
        imageFileInput.value = '';
        imagePreviewContainer.style.display = 'none';
        imagePreviewThumb.src = '';
    });

    async function loadConversations() {
        try {
            const res = await fetch(`${API_BASE}/api/v1/chat/conversations`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const conversations = await res.json();
                renderConversations(conversations);
                if (conversations.length > 0 && !currentConversationId) {
                    selectConversation(conversations[0].id, conversations[0].title);
                } else if (conversations.length === 0) {
                    createNewConversation('Initial Legal Session');
                }
            }
        } catch (err) {
            console.error('Failed to load conversations:', err);
        }
    }

    function renderConversations(conversations) {
        conversationListEl.innerHTML = '';
        conversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = `history-item ${conv.id === currentConversationId ? 'active' : ''}`;
            item.textContent = conv.title;
            item.addEventListener('click', () => selectConversation(conv.id, conv.title));
            conversationListEl.appendChild(item);
        });
    }

    async function createNewConversation(title = 'New Legal Session') {
        try {
            const res = await fetch(`${API_BASE}/api/v1/chat/conversations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ title })
            });
            if (res.ok) {
                const newConv = await res.json();
                currentConversationId = newConv.id;
                chatTitleEl.textContent = newConv.title;
                chatWindowEl.innerHTML = '';
                appendMessage('assistant', 'Welcome to LexAI. How can I assist you with legal research today?');
                loadConversations();
            }
        } catch (err) {
            console.error('Failed to create conversation:', err);
        }
    }

    async function selectConversation(id, title) {
        currentConversationId = id;
        chatTitleEl.textContent = title;
        
        document.querySelectorAll('.history-item').forEach(el => {
            el.classList.remove('active');
        });

        try {
            const res = await fetch(`${API_BASE}/api/v1/chat/conversations/${id}/messages`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const messages = await res.json();
                chatWindowEl.innerHTML = '';
                if (messages.length === 0) {
                    appendMessage('assistant', 'Welcome to LexAI. How can I assist you with legal research today?');
                } else {
                    messages.forEach(msg => appendMessage(msg.role, msg.content));
                }
            }
        } catch (err) {
            console.error('Failed to load messages:', err);
        }
        loadConversations();
    }

    /**
     * Render a message bubble.
     * For assistant messages, the content is rendered as markdown (via marked.js).
     * Citations are lines starting with "[Source:" which are wrapped in a <cite> block.
     */
    function appendMessage(role, content) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role === 'user' ? 'user-message' : 'assistant-message'}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        if (role === 'assistant') {
            const html = marked.parse(content);
            contentDiv.innerHTML = String(html).replace(
                /\[Source:[^\]]+\]/g,
                (tag) => `<span class="source-chip">${tag}</span>`
            );
        } else {
            contentDiv.textContent = content;
        }
        
        msgDiv.appendChild(contentDiv);

        if (role === 'assistant') {
            attachTTSHandler(msgDiv, content);
        }

        chatWindowEl.appendChild(msgDiv);
        chatWindowEl.scrollTop = chatWindowEl.scrollHeight;
    }

    async function sendMessage() {
        const text = userInputEl.value.trim();
        if ((!text && !selectedImageFile) || !currentConversationId) return;

        let displayContent = text;
        if (selectedImageFile) {
            displayContent += ` [Attached Image: ${selectedImageFile.name}]`;
        }

        appendMessage('user', displayContent);
        userInputEl.value = '';

        const formData = new FormData();
        formData.append('content', text || 'Please analyze this attached image.');
        if (selectedImageFile) {
            formData.append('image', selectedImageFile);
        }

        removeImageBtn.click();

        try {
            let res = await fetch(`${API_BASE}/api/v1/chat/conversations/${currentConversationId}/messages`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
            if (res.status === 401) {
                const newToken = await tryRefreshToken();
                if (newToken) {
                    token = newToken;
                    res = await fetch(`${API_BASE}/api/v1/chat/conversations/${currentConversationId}/messages`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        },
                        body: formData
                    });
                }
            }
            if (res.ok) {
                const data = await res.json();
                appendMessage(data.assistant_message.role, data.assistant_message.content);
            } else {
                const errData = await res.json();
                appendMessage('assistant', `Error: ${errData.detail || 'Failed to process message.'}`);
            }
        } catch (err) {
            console.error('Failed to send message:', err);
            appendMessage('assistant', 'Error: Network connection failed.');
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    userInputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    newChatBtn.addEventListener('click', () => {
        const title = prompt('Enter conversation title:', 'Legal Research Session');
        if (title) {
            createNewConversation(title);
        }
    });

    logoutBtn.addEventListener('click', () => {
        localStorage.clear();
        window.location.href = 'login.html';
    });

    loadConversations();
});
