// Shared game page: one-tap share with a copy fallback. The game itself stays in its opaque frame.
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const frame = $('ow-game'), shareButton = $('ow-share'), copyBox = $('ow-copy'), copyLink = $('ow-copy-link'), status = $('ow-status');
  const url = location.origin + location.pathname;
  const title = (document.querySelector('meta[property="og:title"]') || {}).content || 'OpenWorld';
  let statusTimer = 0;

  function say(text) {
    status.textContent = text;
    clearTimeout(statusTimer);
    statusTimer = setTimeout(() => { status.textContent = ''; }, 3000);
  }
  function closeCopy() { copyBox.hidden = true; shareButton.focus(); }

  shareButton.addEventListener('click', async () => {
    const result = window.OWShare ? await window.OWShare(url, title, 'Play this 3D game made with AI on OpenWorld') : 'manual';
    if (result === 'copied') say('Link copied');
    else if (result === 'manual') {
      // Older browsers can still copy a selected field; otherwise the link waits, selected, in the box.
      copyLink.value = url; copyBox.hidden = false; copyLink.focus(); copyLink.select();
      let copied = false;
      try { copied = document.execCommand('copy'); } catch (error) { copied = false; }
      if (copied) { closeCopy(); say('Link copied'); }
    }
  });
  $('ow-copy-done').addEventListener('click', closeCopy);
  copyBox.addEventListener('keydown', event => { if (event.key === 'Escape') closeCopy(); });

  // The game's own store portal may only send the player to the home page, nothing else.
  addEventListener('message', event => {
    if (event.source === frame.contentWindow && event.data && event.data.type === 'ow-open-store') location.href = '/';
  });
  // Keys go to the game, like the old full-page link, unless the visitor already moved focus.
  const focusGame = () => { if (document.activeElement === document.body) frame.focus(); };
  focusGame();
  frame.addEventListener('load', focusGame);
})();
