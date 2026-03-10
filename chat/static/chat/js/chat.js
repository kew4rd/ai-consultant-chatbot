let currentConversationId = null;
let isProcessing = false;
let selectedConsultant = 'business';

const CONSULTANT_INFO = {
    business: { icon: '💼', name: 'Бизнес-консультант' },
    legal:    { icon: '⚖️', name: 'Юридический консультант' },
};

// ===== CONSULTANT SELECTION =====

function setConsultant(consultant) {
    selectedConsultant = consultant;
    document.querySelectorAll('.consultant-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.consultant === consultant);
    });
    if (!currentConversationId) {
        updateChatHeader(consultant);
    }
}

function updateChatHeader(consultant) {
    const info = CONSULTANT_INFO[consultant] || CONSULTANT_INFO.business;
    document.getElementById('chat-consultant-icon').textContent = info.icon;
    document.getElementById('chat-consultant-name').textContent = info.name;
}

// ===== CONVERSATION MANAGEMENT =====

function newConversation() {
    if (isProcessing) return;
    currentConversationId = null;
    setActiveConversation(null);
    updateChatHeader(selectedConsultant);

    const container = document.getElementById('chat-container');
    container.innerHTML = `
        <div class="welcome-message">
            <h2>Новый чат</h2>
            <p>Задайте ваш вопрос ${CONSULTANT_INFO[selectedConsultant].name.toLowerCase()}у.</p>
        </div>
    `;
    document.getElementById('user-input').focus();
}

async function loadConversation(conversationId) {
    if (isProcessing) return;
    if (currentConversationId === conversationId) return;

    currentConversationId = conversationId;
    setActiveConversation(conversationId);

    const container = document.getElementById('chat-container');
    container.innerHTML = '<div class="loading-chat">Загрузка...</div>';

    try {
        const response = await fetch(`/conversations/${conversationId}/`);
        const data = await response.json();

        if (data.consultant) {
            updateChatHeader(data.consultant);
        }

        container.innerHTML = '';

        if (data.messages && data.messages.length > 0) {
            for (const msg of data.messages) {
                addMessage(msg.content, msg.role, false);
            }
            scrollToBottom();
        } else {
            const info = CONSULTANT_INFO[data.consultant] || CONSULTANT_INFO.business;
            container.innerHTML = `
                <div class="welcome-message">
                    <h2>${escapeHtml(data.title)}</h2>
                    <p>Начните разговор с ${info.name.toLowerCase()}ом.</p>
                </div>
            `;
        }
    } catch (e) {
        container.innerHTML = '<div class="loading-chat">Ошибка загрузки чата</div>';
        console.error(e);
    }
}

function setActiveConversation(conversationId) {
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.toggle('active', item.dataset.id === String(conversationId));
    });
}

function addConversationToSidebar(id, title, consultant) {
    const list = document.getElementById('conversations-list');
    const info = CONSULTANT_INFO[consultant] || CONSULTANT_INFO.business;

    const existing = list.querySelector(`[data-id="${id}"]`);
    if (existing) {
        existing.querySelector('.conv-title').textContent = title;
        list.insertBefore(existing, list.firstChild);
        return;
    }

    const item = document.createElement('div');
    item.className = 'conversation-item';
    item.dataset.id = String(id);
    item.dataset.consultant = consultant;
    item.onclick = () => loadConversation(id);
    item.innerHTML = `
        <span class="conv-icon">${info.icon}</span>
        <span class="conv-title">${escapeHtml(title)}</span>
        <button class="conv-delete" onclick="deleteConversation(event, ${id})" title="Удалить">×</button>
    `;
    list.insertBefore(item, list.firstChild);
}

async function deleteConversation(event, conversationId) {
    event.stopPropagation();
    if (!confirm('Удалить этот чат?')) return;

    try {
        const response = await fetch(`/conversations/${conversationId}/delete/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const item = document.querySelector(`[data-id="${conversationId}"]`);
            if (item) item.remove();

            if (currentConversationId === conversationId) {
                newConversation();
            }
        }
    } catch (e) {
        console.error('Error deleting conversation:', e);
    }
}

// ===== MESSAGING =====

async function sendMessage() {
    if (isProcessing) return;

    const input = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const message = input.value.trim();

    if (!message) {
        showError('Пожалуйста, введите сообщение');
        return;
    }

    addMessage(message, 'user');
    input.value = '';
    autoResize(input);

    const loadingMsg = addLoadingMessage();
    sendBtn.disabled = true;
    isProcessing = true;

    try {
        const response = await fetch('/send/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                conversation_id: currentConversationId,
                consultant: selectedConsultant,
            })
        });

        loadingMsg.remove();
        const data = await response.json();

        if (data.status === 'success') {
            addMessage(data.response, 'assistant');

            if (data.conversation_id !== currentConversationId) {
                currentConversationId = data.conversation_id;
                const consultant = data.consultant || selectedConsultant;
                addConversationToSidebar(data.conversation_id, data.conversation_title, consultant);
                setActiveConversation(currentConversationId);
                updateChatHeader(consultant);
            } else {
                const item = document.querySelector(`[data-id="${currentConversationId}"]`);
                if (item && data.conversation_title) {
                    item.querySelector('.conv-title').textContent = data.conversation_title;
                }
            }

            updateTokenDisplay(data.tokens_remaining);

        } else if (data.status === 'limit_exceeded') {
            showError(data.error);
        } else {
            showError(data.error || 'Произошла ошибка');
        }

    } catch (error) {
        loadingMsg.remove();
        showError('Ошибка соединения. Проверьте что сервер запущен.');
        console.error('Error:', error);
    } finally {
        sendBtn.disabled = false;
        isProcessing = false;
        input.focus();
    }
}

// ===== UI HELPERS =====

function addMessage(text, role, scroll = true) {
    const container = document.getElementById('chat-container');
    const welcomeMsg = container.querySelector('.welcome-message');
    if (welcomeMsg) welcomeMsg.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    if (role === 'assistant') {
        messageDiv.innerHTML = marked.parse(text);
    } else {
        messageDiv.textContent = text;
    }

    container.appendChild(messageDiv);
    if (scroll) scrollToBottom();
    return messageDiv;
}

function addLoadingMessage() {
    const container = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant loading';

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('div');
        dot.className = 'typing-dot';
        indicator.appendChild(dot);
    }

    messageDiv.appendChild(indicator);
    container.appendChild(messageDiv);
    scrollToBottom();
    return messageDiv;
}

function updateTokenDisplay(tokensRemaining) {
    tokensUsed = TOKENS_LIMIT - tokensRemaining;
    const percent = Math.min(100, Math.round(tokensUsed / TOKENS_LIMIT * 100));

    const display = document.getElementById('tokens-display');
    const bar = document.getElementById('tokens-bar');

    if (display) display.textContent = `${tokensUsed.toLocaleString('ru')} / ${TOKENS_LIMIT.toLocaleString('ru')}`;
    if (bar) bar.style.width = percent + '%';
}

function showError(message) {
    const existing = document.querySelector('.error-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function scrollToBottom() {
    const container = document.getElementById('chat-container');
    container.scrollTop = container.scrollHeight;
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// ===== INIT =====

document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('user-input');
    input.focus();
    input.addEventListener('input', function () { autoResize(this); });
    input.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
});
