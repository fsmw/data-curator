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

// Search functionality
export async function searchIndicators(query, source = '', topic = '') {
  const params = new URLSearchParams();
  if (query) params.append('q', query);
  if (source) params.append('source', source);
  if (topic) params.append('topic', topic);
  
  const response = await fetch(`/api/search?${params}`);
  return await response.json();
}

// Download functionality  
export async function downloadIndicator(indicator) {
  const response = await fetch('/api/download/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(indicator)
  });
  return await response.json();
}

// Dataset listing
export async function listDatasets(query = '', source = '', topic = '') {
  const params = new URLSearchParams();
  if (query) params.append('q', query);
  if (source) params.append('source', source);
  if (topic) params.append('topic', topic);
  
  const response = await fetch(`/api/datasets?${params}`);
  return await response.json();
}

// Dataset preview
export async function previewDataset(datasetId, limit = 100) {
  const response = await fetch(`/api/datasets/${datasetId}/preview?limit=${limit}`);
  return await response.json();
}

// Delete dataset
export async function deleteDataset(datasetId) {
  const response = await fetch(`/api/datasets/${datasetId}/delete`, {
    method: 'DELETE'
  });
  return await response.json();
}

// Refresh catalog
export async function refreshCatalog(force = false) {
  const response = await fetch('/api/datasets/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force })
  });
  return await response.json();
}

// Enhanced SSE helper with automatic reconnection
export function attachProgressStream(targetId, options = {}) {
  const target = document.getElementById(targetId);
  if (!target) return;

  const { onMessage, onError, onComplete } = options;
  let evtSource = null;
  let reconnectAttempts = 0;
  const maxReconnects = 5;

  const render = (payload) => {
    if (onMessage) {
      onMessage(payload);
    } else {
      const line = document.createElement('div');
      line.className = 'small text-secondary mb-1';
      line.innerHTML = `
        <span class="badge ${payload.percent === 100 ? 'bg-success' : 'bg-primary'}">${payload.step}</span>
        ${payload.status}
        <div class="progress mt-1" style="height: 4px;">
          <div class="progress-bar" role="progressbar" style="width: ${payload.percent}%"></div>
        </div>
      `;
      target.prepend(line);
    }

    if (payload.percent === 100 && onComplete) {
      onComplete(payload);
    }
  };

  const connect = () => {
    try {
      evtSource = new EventSource('/api/progress/stream');
      
      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data || '{}');
          render(data);
          reconnectAttempts = 0; // Reset on successful message
        } catch (e) {
          console.error('Failed to parse SSE message:', e);
        }
      };

      evtSource.onerror = () => {
        evtSource.close();
        if (reconnectAttempts < maxReconnects) {
          reconnectAttempts++;
          setTimeout(connect, 2000 * reconnectAttempts); // Exponential backoff
        } else if (onError) {
          onError();
        }
      };
    } catch (e) {
      console.error('SSE not supported, falling back to polling');
      startPolling();
    }
  };

  const startPolling = () => {
    const poll = async () => {
      try {
        const res = await fetch('/api/progress/poll');
        const data = await res.json();
        render(data);
      } catch (err) {
        console.error('Poll error:', err);
      }
    };
    poll();
    setInterval(poll, 3000);
  };

  connect();

  // Return cleanup function
  return () => {
    if (evtSource) {
      evtSource.close();
    }
  };
}

// Simple SSE helper with 3s polling fallback (backward compatible)
export function attachProgressStreamSimple(targetId) {
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

// Make functions available globally for inline scripts
window.MisesApp = {
  searchIndicators,
  downloadIndicator,
  listDatasets,
  previewDataset,
  deleteDataset,
  refreshCatalog,
  attachProgressStream,
  attachProgressStreamSimple
};
