// One-tap share for a public game link, used by the shared game page and the studio.
// The device's own share sheet comes first; without one, the link is copied.
// Returns 'shared', 'cancelled', 'copied', or 'manual' (show the link to copy by hand).
window.OWShare = async function (url, title, text) {
  if (navigator.share) {
    try { await navigator.share({ title: title, text: text, url: url }); return 'shared'; }
    catch (error) { if (error && error.name === 'AbortError') return 'cancelled'; }
  }
  try { await navigator.clipboard.writeText(url); return 'copied'; } catch (error) { /* fall through */ }
  return 'manual';
};
