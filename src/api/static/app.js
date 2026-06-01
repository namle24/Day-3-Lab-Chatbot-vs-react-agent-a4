// Frontend Client Logic for AI Agent Chatroom

document.addEventListener('DOMContentLoaded', () => {
    // Application State
    let activeUserId = null;
    let users = [];

    // DOM Elements
    const userListContainer = document.getElementById('user-list');
    const chatMessagesContainer = document.getElementById('chat-messages');
    const activeUserName = document.getElementById('active-user-name');
    const activeUserProfile = document.getElementById('active-user-profile');
    const activeUserAvatar = document.getElementById('active-user-avatar');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatForm = document.getElementById('chat-form');
    const typingIndicator = document.getElementById('typing-indicator-container');
    const activeModelBadge = document.getElementById('active-model-name');
    const providerBadge = document.getElementById('provider-badge');

    // Initialize application
    async function init() {
        try {
            await fetchUsers();
        } catch (error) {
            console.error('Lỗi khi khởi tạo ứng dụng:', error);
            userListContainer.innerHTML = `<p class="error-text" style="color: var(--text-muted); padding: 12px; font-size: 0.85rem;">Không thể kết nối đến server backend.</p>`;
        }
    }

    // Flexible API fetch helper: tries '/api' then '/api/v1'
    async function apiFetch(path, options) {
        const bases = ['/api', '/api/v1'];
        let lastError = null;
        for (const base of bases) {
            try {
                const res = await fetch(base + path, options);
                if (res.ok) return res;
                lastError = new Error(`HTTP ${res.status}`);
            } catch (err) {
                lastError = err;
            }
        }
        throw lastError;
    }

    // Fetch simulated users list
    async function fetchUsers() {
        const response = await apiFetch('/users');
        if (!response.ok) throw new Error('Không thể tải danh sách người dùng');

        users = await response.json();
        renderUsersList();
    }

    // Render users in left sidebar
    function renderUsersList() {
        userListContainer.innerHTML = '';
        
        if (users.length === 0) {
            userListContainer.innerHTML = `<p style="color: var(--text-muted); padding: 12px; font-size: 0.85rem;">Không có người dùng mô phỏng.</p>`;
            return;
        }

        users.forEach(user => {
            const userCard = document.createElement('div');
            userCard.className = `user-item ${activeUserId === user.id ? 'active' : ''}`;
            userCard.id = `user-card-${user.id}`;
            
            userCard.innerHTML = `
                <div class="avatar-container">
                    <div class="avatar">${user.avatar}</div>
                    <div class="status-dot ${user.status === 'online' ? 'online' : 'offline'}"></div>
                </div>
                <div class="user-details">
                    <div class="user-name-row">
                        <h4>${user.name}</h4>
                    </div>
                    <p class="last-msg-preview" id="last-msg-preview-${user.id}">
                        ${user.last_message ? user.last_message : 'Chưa có tin nhắn...'}
                    </p>
                </div>
            `;
            
            userCard.addEventListener('click', () => selectUser(user));
            userListContainer.appendChild(userCard);
        });
    }

    // Handle user selection click event
    async function selectUser(user) {
        if (activeUserId === user.id) return;
        
        activeUserId = user.id;
        
        // Update active class styles in sidebar
        document.querySelectorAll('.user-item').forEach(el => el.classList.remove('active'));
        const activeCard = document.getElementById(`user-card-${user.id}`);
        if (activeCard) activeCard.classList.add('active');

        // Update header details
        activeUserName.textContent = user.name;
        activeUserProfile.textContent = user.profile;
        activeUserAvatar.textContent = user.avatar;
        
        // Show loading state in chat container
        chatMessagesContainer.innerHTML = `
            <div class="empty-state">
                <div class="typing-indicator" style="margin-bottom: 12px;">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </div>
                <h4>Đang tải lịch sử chat (Memory)...</h4>
                <p>Gọi API để truy xuất Memory lịch sử hội thoại của ${user.name}...</p>
            </div>
        `;

        // Enable input fields
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.placeholder = `Nhắn tin cho ${user.name}...`;
        messageInput.focus();

        try {
            // Simulate Memory call: Fetch user chat history from server
            const response = await apiFetch(`/chat/${user.id}/history`);
            if (!response.ok) throw new Error('Không thể tải lịch sử chat');

            const history = await response.json();
            renderChatHistory(history);
            scrollToBottom();
            
            // Set default/detecting badges
            providerBadge.textContent = "Provider: Connected";
        } catch (error) {
            console.error('Lỗi khi tải lịch sử:', error);
            chatMessagesContainer.innerHTML = `
                <div class="empty-state" style="color: #ef4444;">
                    <h4>Lỗi hệ thống</h4>
                    <p>Không thể kết nối Memory của ${user.name}.</p>
                </div>
            `;
        }
    }

    // Render message history in chat panel
    function renderChatHistory(messages) {
        chatMessagesContainer.innerHTML = '';
        
        if (!messages || messages.length === 0) {
            chatMessagesContainer.innerHTML = `
                <div class="empty-state">
                    <h4>Cuộc trò chuyện mới</h4>
                    <p>Chưa có lịch sử tin nhắn. Hãy bắt đầu chat bằng khung bên dưới.</p>
                </div>
            `;
            return;
        }

        messages.forEach(msg => {
            appendMessageBubble(msg.sender, msg.text);
        });
    }

    // Helper to append a single message bubble
    function appendMessageBubble(sender, text) {
        const wrapper = document.createElement('div');
        wrapper.className = `message-wrapper ${sender}`;
        
        // Simple helper to format text code blocks safely
        let formattedText = escapeHTML(text);
        // Replace `code` with <code>code</code>
        formattedText = formattedText.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        wrapper.innerHTML = `
            <div class="message-bubble">
                ${formattedText}
            </div>
        `;
        
        chatMessagesContainer.appendChild(wrapper);
    }

    // Escape HTML helpers to prevent XSS injection
    function escapeHTML(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    // Scroll chat window to bottom
    function scrollToBottom() {
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    // Handle Form Submit Event
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const text = messageInput.value.trim();
        if (!text || !activeUserId) return;

        // Append user message immediately to UI
        appendMessageBubble('user', text);
        messageInput.value = '';
        scrollToBottom();

        // Update preview text in sidebar
        const previewEl = document.getElementById(`last-msg-preview-${activeUserId}`);
        if (previewEl) previewEl.textContent = text;

        // Lock form inputs during API call
        messageInput.disabled = true;
        sendButton.disabled = true;

        // Show typing animation
        typingIndicator.style.display = 'flex';
        scrollToBottom();

        try {
            // Send payload to backend
            const response = await apiFetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: activeUserId,
                    message: text
                })
            });

            if (!response.ok) throw new Error('Có lỗi xảy ra khi giao tiếp với Agent');

            const result = await response.json();
            
            // Hide typing animation
            typingIndicator.style.display = 'none';

            // Append Agent reply
            appendMessageBubble('agent', result.reply);
            
            // Update preview text in sidebar
            if (previewEl) previewEl.textContent = result.reply;

            // Update stats badge with safe defaults
            const model = result.model || 'gpt-4o';
            const provider = result.provider || 'OpenAI';
            const latency = result.latency_ms || 0;
            
            activeModelBadge.textContent = `Model: ${model}`;
            providerBadge.textContent = `Provider: ${provider} (${latency}ms)`;

        } catch (error) {
            console.error('Lỗi gửi tin nhắn:', error);
            typingIndicator.style.display = 'none';
            appendMessageBubble('agent', `Lỗi: Không thể kết nối đến Agent để xử lý yêu cầu.`);
        } finally {
            // Re-enable form inputs
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
            scrollToBottom();
        }
    });

    // Start App
    init();
});
