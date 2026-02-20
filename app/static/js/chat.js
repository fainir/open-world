// ══════════════════════════════════════════
// CHAT MODULE
// ══════════════════════════════════════════

const Chat = (() => {
  const API_KEY_STORAGE = 'ow_api_key';
  let sessionId = null;
  let currentVersionId = null;
  let isProcessing = false;

  function getApiKey() {
    return document.getElementById('api-key-input').value.trim();
  }

  function saveApiKey(key) {
    localStorage.setItem(API_KEY_STORAGE, key);
  }

  function loadApiKey() {
    const saved = localStorage.getItem(API_KEY_STORAGE);
    if (saved) {
      document.getElementById('api-key-input').value = saved;
    }
  }

  function getSessionId() { return sessionId; }
  function setSessionId(id) { sessionId = id; }
  function getCurrentVersionId() { return currentVersionId; }

  async function sendMessage(message) {
    if (isProcessing) return null;

    const apiKey = getApiKey();
    if (!apiKey) {
      throw new Error('Please enter your Anthropic API key first');
    }

    // Save the key for next session
    saveApiKey(apiKey);
    isProcessing = true;

    try {
      const headers = { 'Content-Type': 'application/json', ...Auth.authHeaders() };

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message,
          session_id: sessionId,
          api_key: apiKey,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Request failed');

      // Update session tracking
      if (data.session_id) sessionId = data.session_id;
      if (data.version_id) currentVersionId = data.version_id;

      return data;
    } finally {
      isProcessing = false;
    }
  }

  async function getVersions() {
    if (!sessionId) return [];
    const res = await fetch(`/api/versions/${sessionId}`);
    if (!res.ok) return [];
    return await res.json();
  }

  async function saveVersion(versionId) {
    const res = await fetch('/api/versions/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...Auth.authHeaders() },
      body: JSON.stringify({ version_id: versionId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Save failed');
    return data;
  }

  async function shareVersion(versionId) {
    const res = await fetch('/api/versions/share', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...Auth.authHeaders() },
      body: JSON.stringify({ version_id: versionId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Share failed');
    return data;
  }

  async function getUserVersions() {
    const res = await fetch('/api/user/versions', {
      headers: Auth.authHeaders(),
    });
    if (!res.ok) return [];
    return await res.json();
  }

  function isWorking() { return isProcessing; }

  return {
    getApiKey, saveApiKey, loadApiKey,
    getSessionId, setSessionId, getCurrentVersionId,
    sendMessage, getVersions, saveVersion, shareVersion, getUserVersions,
    isWorking,
  };
})();
