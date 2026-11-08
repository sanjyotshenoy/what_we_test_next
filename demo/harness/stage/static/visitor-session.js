/* Keep one slot per browser while a dashboard tab is visible. */
(() => {
  async function heartbeat() {
    if (document.hidden) return;
    try {
      const response = await fetch('/api/visitor', {cache: 'no-store'});
      if (response.status === 429) window.location.reload();
    } catch (_) { /* A transient network outage can recover on the next tick. */ }
  }
  setInterval(heartbeat, 30000);
  document.addEventListener('visibilitychange', heartbeat);
  heartbeat();
})();
