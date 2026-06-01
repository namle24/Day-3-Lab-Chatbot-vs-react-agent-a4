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
    const logListContainer = document.getElementById('log-list');

    // Initialize application
    async function init() {
        try {
            await fetchUsers();
        } catch (error) {
            console.error('Lỗi khi khởi tạo ứng dụng:', error);
            userListContainer.innerHTML = `<p class="error-text" style="color: var(--text-muted); padding: 12px; font-size: 0.85rem;">Không thể kết nối đến server backend.</p>`;
        }
    }

    // Fetch simulated users list
    async function fetchUsers() {
        const response = await fetch('/api/users');
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
            // Fetch user chat history from server
            const response = await fetch(`/api/chat/${user.id}/history`);
            if (!response.ok) throw new Error('Không thể tải lịch sử chat');
            
            const history = await response.json();
            renderChatHistory(history);
            scrollToBottom();
            
            // Set default/detecting badges
            providerBadge.textContent = "Status: Connected";

            // Fetch and render tool logs
            await fetchAndRenderToolLogs();
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

    // Rich text and Markdown parser for chat messages
    function formatMessageText(text) {
        // 1. Escape HTML first to prevent XSS
        let html = escapeHTML(text);

        // 2. Parse Markdown Tables
        // Find markdown table blocks and convert them to HTML <table>
        const lines = html.split('\n');
        let inTable = false;
        let tableHTML = '';
        const parsedLines = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('|') && line.endsWith('|')) {
                // Table row
                const cells = line.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
                
                // Check if this is a separator line (e.g. |---|---|)
                const isSeparator = cells.every(c => /^:?-+:?$/.test(c));

                if (isSeparator) {
                    continue; // Skip separator line
                }

                if (!inTable) {
                    inTable = true;
                    tableHTML = '<table>';
                    // Check if the previous line was the header line
                    if (parsedLines.length > 0 && parsedLines[parsedLines.length - 1].startsWith('<tr>')) {
                        const prevLine = parsedLines.pop();
                        tableHTML += prevLine.replace(/<td>/g, '<th>').replace(/<\/td>/g, '<\/th>');
                    }
                }

                tableHTML += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
            } else {
                if (inTable) {
                    inTable = false;
                    tableHTML += '</table>';
                    parsedLines.push(tableHTML);
                    tableHTML = '';
                }
                parsedLines.push(line);
            }
        }
        if (inTable) {
            tableHTML += '</table>';
            parsedLines.push(tableHTML);
        }

        html = parsedLines.join('\n');

        // 3. Parse Markdown Bold: **text**
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // 4. Parse Inline Code: `code`
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // 5. Parse Markdown Bullet Points: - item
        html = html.replace(/^-\s+(.+)$/gm, '<li>$1</li>');
        // Wrap adjacent <li> items in <ul>
        html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

        // 6. Convert newlines to breaks (if not in tables or list blocks to prevent excessive vertical spacing)
        html = html.split('\n').map(line => {
            if (line.includes('<table>') || line.includes('</table>') || line.includes('<tr>') || line.includes('<td>') || line.includes('<th>') || line.includes('<ul>') || line.includes('</ul>') || line.includes('<li>')) {
                return line;
            }
            return line + '<br>';
        }).join('\n');

        return html;
    }

    // Helper to append a single message bubble
    function appendMessageBubble(sender, text, pendingAction = null) {
        const wrapper = document.createElement('div');
        wrapper.className = `message-wrapper ${sender}`;
        
        let formattedText = formatMessageText(text);
        
        let bubbleContent = `
            <div class="message-bubble">
                ${formattedText}
        `;

        // If there's a pending action, append an interactive confirmation card!
        if (pendingAction && sender === 'agent') {
            const actionId = pendingAction.id;
            const summary = pendingAction.summary;

            bubbleContent += `
                <div class="confirm-card" id="confirm-card-${actionId}">
                    <div class="confirm-card-title">
                        <svg class="confirm-card-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                            <line x1="16" y1="2" x2="16" y2="6"></line>
                            <line x1="8" y1="2" x2="8" y2="6"></line>
                            <line x1="3" y1="10" x2="21" y2="10"></line>
                        </svg>
                        <span>Xác Nhận Đặt Lịch Hẹn</span>
                    </div>
                    <div class="confirm-card-summary">
                        ${escapeHTML(summary)}
                    </div>
                    <button class="confirm-btn" id="confirm-btn-${actionId}">
                        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        <span>ĐỒNG Ý ĐẶT LỊCH</span>
                    </button>
                </div>
            `;
        }

        bubbleContent += `</div>`;
        wrapper.innerHTML = bubbleContent;
        chatMessagesContainer.appendChild(wrapper);

        // Bind confirmation click event
        if (pendingAction && sender === 'agent') {
            const actionId = pendingAction.id;
            const btn = wrapper.querySelector(`#confirm-btn-${actionId}`);
            if (btn) {
                btn.addEventListener('click', () => handleConfirmAction(actionId));
            }
        }
    }

    // Handle Confirm Action Click
    async function handleConfirmAction(actionId) {
        const confirmBtn = document.getElementById(`confirm-btn-${actionId}`);
        const confirmCard = document.getElementById(`confirm-card-${actionId}`);
        
        if (!confirmBtn || !activeUserId) return;

        // Lock button
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = `<span>Đang xác nhận...</span>`;

        try {
            const response = await fetch(`/api/v1/actions/${actionId}/confirm`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: activeUserId
                })
            });

            if (!response.ok) throw new Error('Không thể xác nhận đặt lịch');

            const result = await response.json();

            // Replace card button with success checkmark
            confirmBtn.style.display = 'none';
            const badge = document.createElement('div');
            badge.className = 'confirm-badge-success';
            badge.innerHTML = `
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>Đã xác nhận đặt lịch hẹn thành công!</span>
            `;
            confirmCard.appendChild(badge);

            // Append confirmation response bubble
            appendMessageBubble('agent', result.reply);
            scrollToBottom();

            // Update previews
            const previewEl = document.getElementById(`last-msg-preview-${activeUserId}`);
            if (previewEl) previewEl.textContent = result.reply;

            // Fetch and render tool logs
            await fetchAndRenderToolLogs();
        } catch (error) {
            console.error('Lỗi khi confirm:', error);
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = `<span>ĐỒNG Ý ĐẶT LỊCH (Thử lại)</span>`;
            alert('Có lỗi xảy ra khi xác nhận đặt lịch hẹn. Vui lòng thử lại.');
        }
    }

    // Fetch and render real-time ReAct Tool logs in the right-hand panel
    async function fetchAndRenderToolLogs() {
        if (!activeUserId) return;

        try {
            const response = await fetch(`/api/v1/sessions/${activeUserId}/tool-logs`);
            if (!response.ok) throw new Error('Không thể tải nhật ký hoạt động');

            const logs = await response.json();
            renderToolLogs(logs);
        } catch (error) {
            console.error('Lỗi khi tải tool logs:', error);
        }
    }

    // Render tool logs in log list panel
    function renderToolLogs(logs) {
        logListContainer.innerHTML = '';

        if (!logs || logs.length === 0) {
            logListContainer.innerHTML = `
                <div class="empty-log-state">
                    <p>Chưa có cuộc gọi công cụ (Tool calls) nào cho user này.</p>
                </div>
            `;
            return;
        }

        logs.forEach(log => {
            const logItem = document.createElement('div');
            logItem.className = 'log-item';

            // Format arguments and observations beautifully
            let prettyArgs = log.arguments;
            try {
                const parsed = JSON.parse(log.arguments);
                prettyArgs = JSON.stringify(parsed, null, 2);
            } catch(e) {}

            logItem.innerHTML = `
                <div class="log-item-header">
                    <span class="tool-name-badge">${escapeHTML(log.tool_name)}</span>
                    <span class="log-latency">${log.latency_ms}ms</span>
                </div>
                <div class="log-detail">
                    <span class="log-label">Arguments:</span>
                    <div class="log-value">${escapeHTML(prettyArgs)}</div>
                </div>
                <div class="log-detail">
                    <span class="log-label">Observation:</span>
                    <div class="log-value">${escapeHTML(log.observation)}</div>
                </div>
            `;
            logListContainer.appendChild(logItem);
        });
    }

    // Escape HTML helpers to prevent XSS injection
    function escapeHTML(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, function(m) { return map[m]; });
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
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: activeUserId,
                    message: text,
                    confirm_action_id: null
                })
            });

            if (!response.ok) throw new Error('Có lỗi xảy ra khi giao tiếp với Agent');

            const result = await response.json();
            
            // Hide typing animation
            typingIndicator.style.display = 'none';

            // Append Agent reply with pending_action if available
            appendMessageBubble('agent', result.reply, result.pending_action);
            
            // Update preview text in sidebar
            if (previewEl) previewEl.textContent = result.reply;

            // Update stats badge
            activeModelBadge.textContent = result.model;
            providerBadge.textContent = `Provider: ${result.provider} (${result.latency_ms}ms)`;

            // Fetch and render tool logs
            await fetchAndRenderToolLogs();
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
