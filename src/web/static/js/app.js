document.addEventListener("alpine:init", () => {
  Alpine.store("panel", {
    open: false,
    mode: "inline",
    setMode(width) {
      this.mode = width < 992 ? "overlay" : "inline";
    },
    show() { this.open = true; },
    hide() { this.open = false; },
    toggle() { this.open = !this.open; },
  });
});

// Simple SSE helper with 3s polling fallback
export function attachProgressStream(targetId) {
  const target = document.getElementById(targetId);
  if (!target) return;

  const render = (payload) => {
    const line = document.createElement("div");
    line.className = "small text-secondary";
    line.textContent = `${payload.step || "step"}: ${payload.status || ""} (${payload.percent || 0}%)`;
    target.prepend(line);
  };

  try {
    const evtSource = new EventSource("/api/progress/stream");
    evtSource.onmessage = (event) => {
      const data = JSON.parse(event.data || "{}");
      render(data);
    };
    evtSource.onerror = () => {
      evtSource.close();
      startPolling();
    };
  } catch (e) {
    startPolling();
  }

  function startPolling() {
    const poll = async () => {
      try {
        const res = await fetch("/api/progress/poll");
        const data = await res.json();
        render(data);
      } catch (err) {
        console.error("poll error", err);
      }
    };
    poll();
    setInterval(poll, 3000);
  }
}
