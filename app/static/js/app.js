// ══════════════════════════════════════════
// MAIN APP MODULE
// ══════════════════════════════════════════

(function () {
  // ── State ──
  let isFullscreen = false;

  // ── Init ──
  document.addEventListener('DOMContentLoaded', () => {
    Chat.loadApiKey();
    updateAuthUI();
  });

  // ══════════ AUTH UI ══════════

  window.updateAuthUI = function () {
    const guestArea = document.getElementById('user-area-guest');
    const authArea = document.getElementById('user-area-auth');
    const usernameEl = document.getElementById('username-display');

    if (Auth.isLoggedIn()) {
      guestArea.style.display = 'none';
      authArea.style.display = 'flex';
      const user = Auth.getUser();
      usernameEl.textContent = user ? user.username : 'User';
    } else {
      guestArea.style.display = 'flex';
      authArea.style.display = 'none';
    }
  };

  window.showAuthModal = function () {
    document.getElementById('auth-modal').style.display = 'flex';
    switchAuthTab('login');
  };

  window.closeAuthModal = function () {
    document.getElementById('auth-modal').style.display = 'none';
    clearAuthErrors();
  };

  window.switchAuthTab = function (tab) {
    document.querySelectorAll('.modal-tabs .tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.modal-tabs .tab[data-tab="${tab}"]`).classList.add('active');
    document.getElementById('login-form').style.display = tab === 'login' ? 'flex' : 'none';
    document.getElementById('signup-form').style.display = tab === 'signup' ? 'flex' : 'none';
    clearAuthErrors();
  };

  function clearAuthErrors() {
    document.getElementById('login-error').textContent = '';
    document.getElementById('signup-error').textContent = '';
  }

  window.handleLogin = async function (e) {
    e.preventDefault();
    const loginId = document.getElementById('login-id').value.trim();
    const password = document.getElementById('login-password').value;
    try {
      await Auth.login(loginId, password);
      closeAuthModal();
      updateAuthUI();
    } catch (err) {
      document.getElementById('login-error').textContent = err.message;
    }
  };

  window.handleSignup = async function (e) {
    e.preventDefault();
    const username = document.getElementById('signup-username').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    try {
      await Auth.signup(email, username, password);
      closeAuthModal();
      updateAuthUI();
    } catch (err) {
      document.getElementById('signup-error').textContent = err.message;
    }
  };

  window.handleLogout = function () {
    Auth.logout();
    updateAuthUI();
  };

  // ══════════ API KEY ══════════

  window.toggleApiKeyVisibility = function () {
    const input = document.getElementById('api-key-input');
    input.type = input.type === 'password' ? 'text' : 'password';
  };

  // ══════════ GAME IFRAME ══════════

  function loadGameVersion(versionId, versionNumber) {
    const iframe = document.getElementById('game-iframe');
    const loading = document.getElementById('game-loading');
    loading.style.display = 'flex';
    iframe.src = `/game/version/${versionId}`;
    iframe.onload = () => {
      loading.style.display = 'none';
    };
    // Track which version we're viewing
    Chat.setCurrentVersionId(versionId);
    updateVersionIndicator(versionNumber);
  }

  function loadBaseGame() {
    const iframe = document.getElementById('game-iframe');
    iframe.src = '/game/base';
    Chat.setCurrentVersionId(null);
    updateVersionIndicator(null);
  }

  function updateVersionIndicator(versionNumber) {
    let indicator = document.getElementById('version-indicator');
    if (versionNumber == null) {
      if (indicator) indicator.style.display = 'none';
      return;
    }
    if (!indicator) return;
    indicator.style.display = 'flex';
    indicator.querySelector('.vi-label').textContent = versionNumber === 0 ? 'Base' : `v${versionNumber}`;
  }

  window.toggleFullscreen = function () {
    isFullscreen = !isFullscreen;
    document.body.classList.toggle('fullscreen', isFullscreen);
    if (!isFullscreen) {
      // Re-focus is handled by user
    }
  };

  // ESC to exit fullscreen
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isFullscreen) {
      isFullscreen = false;
      document.body.classList.remove('fullscreen');
    }
  });

  // ══════════ CHAT ══════════

  window.sendMessage = async function () {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message || Chat.isWorking()) return;

    // Clear welcome
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    // Add user message to UI
    addMessageToUI('user', message);
    input.value = '';
    autoResize(input);

    // Show thinking
    const thinkingEl = addThinkingIndicator();
    setStatus('Generating changes...', 'loading');
    document.getElementById('game-loading').style.display = 'flex';
    document.getElementById('chat-send').disabled = true;

    try {
      const result = await Chat.sendMessage(message);
      thinkingEl.remove();

      if (result.message && !result.version_id) {
        // Text-only response (no code changes)
        addMessageToUI('assistant', result.message || result.description);
      } else {
        // Code was changed
        let responseText = result.description || 'Changes applied!';
        addAssistantMessage(responseText, result.version_id, result.version_number);

        // Load new version and auto-switch to it
        if (result.version_id) {
          loadGameVersion(result.version_id, result.version_number);
        }

        // Show suggestions
        if (result.suggestions && result.suggestions.length > 0) {
          showSuggestions(result.suggestions);
        }
      }

      setStatus('Done!', 'success');
      setTimeout(() => setStatus(''), 2000);
    } catch (err) {
      thinkingEl.remove();
      addMessageToUI('assistant', `Error: ${err.message}`);
      setStatus('Failed', 'error');
      setTimeout(() => setStatus(''), 3000);
    } finally {
      document.getElementById('game-loading').style.display = 'none';
      document.getElementById('chat-send').disabled = false;
    }
  };

  window.sendExample = function (btn) {
    const input = document.getElementById('chat-input');
    input.value = btn.textContent;
    sendMessage();
  };

  window.handleChatKeydown = function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  window.autoResize = function (el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  };

  function addMessageToUI(role, content) {
    const container = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = `msg msg-${role}`;
    msg.innerHTML = `<div class="msg-bubble">${escapeHtml(content)}</div>`;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return msg;
  }

  function addAssistantMessage(description, versionId, versionNumber) {
    const container = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = 'msg msg-assistant';

    let actionsHtml = '';
    if (versionId) {
      actionsHtml = `
        <div class="msg-actions">
          <button class="msg-action-btn" onclick="handleSaveVersion('${versionId}', this)">Save</button>
          <button class="msg-action-btn" onclick="handleShareVersion('${versionId}', this)">Share</button>
        </div>`;
    }

    msg.innerHTML = `
      <div class="msg-bubble">${escapeHtml(description)}</div>
      ${versionNumber ? `<span class="msg-version-badge">v${versionNumber}</span>` : ''}
      ${actionsHtml}
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return msg;
  }

  function addThinkingIndicator() {
    const container = document.getElementById('chat-messages');
    const el = document.createElement('div');
    el.className = 'msg-thinking';
    el.innerHTML = `
      <div class="thinking-dots"><span></span><span></span><span></span></div>
      <span>Modifying game code...</span>
    `;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    return el;
  }

  function setStatus(text, type) {
    const el = document.getElementById('chat-status');
    el.textContent = text;
    el.className = 'chat-status' + (type ? ` ${type}` : '');
  }

  function showSuggestions(suggestions) {
    const area = document.getElementById('suggestions-area');
    const list = document.getElementById('suggestions-list');
    list.innerHTML = '';
    suggestions.forEach(s => {
      const btn = document.createElement('button');
      btn.className = 'suggestion-btn';
      btn.textContent = s;
      btn.onclick = () => {
        document.getElementById('chat-input').value = s;
        sendMessage();
        area.style.display = 'none';
      };
      list.appendChild(btn);
    });
    area.style.display = 'block';
  }

  // ══════════ SAVE / SHARE ══════════

  window.handleSaveVersion = async function (versionId, btn) {
    if (!Auth.isLoggedIn()) {
      showAuthModal();
      return;
    }
    try {
      await Chat.saveVersion(versionId);
      btn.textContent = 'Saved!';
      btn.disabled = true;
      btn.style.color = 'var(--success)';
    } catch (err) {
      alert(err.message);
    }
  };

  window.handleShareVersion = async function (versionId, btn) {
    if (!Auth.isLoggedIn()) {
      showAuthModal();
      return;
    }
    try {
      const result = await Chat.shareVersion(versionId);
      btn.textContent = 'Shared!';
      btn.style.color = 'var(--success)';
      // Show share modal with link
      const shareUrl = `${window.location.origin}/shared/${result.share_slug}`;
      document.getElementById('share-link').value = shareUrl;
      document.getElementById('share-modal').style.display = 'flex';
    } catch (err) {
      alert(err.message);
    }
  };

  window.closeShareModal = function () {
    document.getElementById('share-modal').style.display = 'none';
    document.getElementById('share-copied').style.display = 'none';
  };

  window.copyShareLink = function () {
    const input = document.getElementById('share-link');
    input.select();
    navigator.clipboard.writeText(input.value).then(() => {
      document.getElementById('share-copied').style.display = 'block';
      setTimeout(() => {
        document.getElementById('share-copied').style.display = 'none';
      }, 2000);
    });
  };

  // ══════════ VERSIONS MODAL ══════════

  window.showVersionsModal = async function () {
    const modal = document.getElementById('versions-modal');
    const list = document.getElementById('versions-list');

    if (!Chat.getSessionId()) {
      list.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px">No versions yet. Start chatting to create game versions.</p>';
      modal.style.display = 'flex';
      return;
    }

    list.innerHTML = '<div style="text-align:center;padding:20px"><div class="spinner"></div></div>';
    modal.style.display = 'flex';

    try {
      const versions = await Chat.getVersions();
      if (versions.length === 0) {
        list.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px">No versions yet.</p>';
        return;
      }

      list.innerHTML = versions.map(v => {
        const isActive = v.id === Chat.getCurrentVersionId();
        const time = v.created_at ? new Date(v.created_at).toLocaleString() : '';
        return `
          <div class="version-item ${isActive ? 'active' : ''}">
            <div class="version-num">${v.version_number === 0 ? '0' : 'v' + v.version_number}</div>
            <div class="version-info" onclick="loadVersionFromList('${v.id}', ${v.version_number})" style="cursor:pointer">
              <div class="version-desc">${escapeHtml(v.description)}</div>
              <div class="version-time">${time}</div>
            </div>
            <div class="version-actions">
              ${v.is_saved ? '<span class="msg-version-badge">Saved</span>' : ''}
              ${v.is_shared ? '<span class="msg-version-badge">Shared</span>' : ''}
              ${!isActive ? `<button class="msg-action-btn" onclick="branchFromVersion('${v.id}', ${v.version_number})" title="Switch to this version and make changes from here">Use</button>` : '<span class="msg-version-badge" style="background:var(--success);color:#fff">Active</span>'}
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      list.innerHTML = `<p style="color:var(--error);text-align:center;padding:20px">Error loading versions</p>`;
    }
  };

  window.closeVersionsModal = function () {
    document.getElementById('versions-modal').style.display = 'none';
  };

  window.loadVersionFromList = function (versionId, versionNumber) {
    loadGameVersion(versionId, versionNumber);
    closeVersionsModal();
  };

  // ══════════ BRANCH ══════════

  window.branchFromVersion = function (versionId, versionNumber) {
    loadGameVersion(versionId, versionNumber);
    closeVersionsModal();
    // Notify user
    addMessageToUI('assistant', `Switched to v${versionNumber}. Your next changes will branch from this version.`);
  };

  // ══════════ HELPERS ══════════

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
})();
