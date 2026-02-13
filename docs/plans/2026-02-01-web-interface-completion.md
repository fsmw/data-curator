# Web Interface Completion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the web interface by implementing missing templates, fixing broken references, adding SSE progress endpoints, and enhancing JavaScript functionality.

**Architecture:** Flask Blueprint-based web interface with Bootstrap 5 + Alpine.js frontend. Will implement missing UI templates, fix route-template mismatches, add Server-Sent Events for progress tracking, and enhance client-side JavaScript for search, downloads, and dataset browsing.

**Tech Stack:** Flask, Jinja2, Bootstrap 5, Alpine.js, JavaScript (ES6 modules), SSE (Server-Sent Events)

---

## Overview

The web interface is partially implemented. Current status:
- ✅ Routes mostly implemented in `routes.py`
- ✅ Base template with Bootstrap 5 + Alpine.js
- ✅ Basic JS app structure
- ⚠️ Some templates incomplete
- ❌ SSE progress endpoints missing (referenced but not implemented)
- ❌ Template references broken (routes removed but templates still reference them)

---

## Task 1: Analyze Current State & Fix Template References

**Files:**
- Read: `src/web/routes.py` (already read)
- Read: `src/web/templates/status.html`
- Read: `src/web/templates/base.html`
- Modify: `src/web/templates/status.html:29`
- Modify: `src/web/templates/base.html:46-47`

**Analysis:**
Based on `routes.py` comments (lines 136-138), `/progress` and `/download` routes were removed:
- Downloads now happen directly from `/search` page
- Progress tracking removed (downloads are fast <15s)
- However, templates still reference these removed routes

**Step 1: Fix status.html broken reference**

Current line 29:
```html
<a class="btn btn-outline-light btn-sm" href="/progress">Ver progreso</a>
```

Change to:
```html
<a class="btn btn-outline-light btn-sm" href="/search">Buscar datos</a>
```

**Step 2: Fix base.html quick actions dropdown**

Current lines 46-47:
```html
<li><a class="dropdown-item" href="/download">Start a download</a></li>
<li><a class="dropdown-item" href="/api/status">API status</a></li>
```

Change to:
```html
<li><a class="dropdown-item" href="/search">Start a download</a></li>
<li><a class="dropdown-item" href="/api/datasets">Browse datasets API</a></li>
```

**Step 3: Verify fixes**

Run: `grep -n "/progress\|/download" src/web/templates/*.html`
Expected: No matches (or only in comments)

**Step 4: Commit**

```bash
git add src/web/templates/status.html src/web/templates/base.html
git commit -m "fix: Remove references to deleted /progress and /download routes"
```

---

## Task 2: Create Browse Available Indicators Template

**Files:**
- Create: `src/web/templates/browse_available.html`
- Reference: `src/web/templates/search.html` (for styling patterns)

**Step 1: Create template file**

Create `src/web/templates/browse_available.html`:

```html
{% extends "base.html" %}
{% block content %}
<div x-data="availableData()" x-init="init()">
  <div class="card mb-3">
    <div class="card-body">
      <div class="row g-2 align-items-center">
        <div class="col-md-6">
          <input type="text" 
                 class="form-control" 
                 placeholder="Search indicators..." 
                 x-model="searchQuery"
                 @keyup.enter="search()">
        </div>
        <div class="col-md-3">
          <select class="form-select" x-model="sourceFilter">
            <option value="">All Sources</option>
            <option value="owid">OWID</option>
            <option value="ilostat">ILOSTAT</option>
            <option value="oecd">OECD</option>
            <option value="imf">IMF</option>
            <option value="worldbank">World Bank</option>
            <option value="eclac">ECLAC</option>
          </select>
        </div>
        <div class="col-md-3">
          <button class="btn btn-primary w-100" @click="search()">
            <i class="bi bi-search"></i> Search
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="d-flex justify-content-between align-items-center mb-3">
    <h5 class="mb-0">Available Indicators</h5>
    <span class="text-secondary" x-text="`${results.length} results`"></span>
  </div>

  <div class="row g-3">
    <template x-for="indicator in results" :key="indicator.id">
      <div class="col-md-6 col-lg-4">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <span class="badge bg-secondary" x-text="indicator.source"></span>
              <span class="badge" :class="indicator.downloaded ? 'bg-success' : 'bg-light text-dark'" 
                    x-text="indicator.downloaded ? 'Downloaded' : 'Available'"></span>
            </div>
            <h6 class="card-title" x-text="indicator.indicator"></h6>
            <p class="card-text small text-secondary" x-text="indicator.description || 'No description available'"></p>
            <div class="mt-auto">
              <button class="btn btn-sm btn-primary w-100" 
                      @click="download(indicator)"
                      :disabled="indicator.downloaded || loading">
                <span x-show="!loading || currentId !== indicator.id">
                  <i class="bi bi-download"></i> 
                  <span x-text="indicator.downloaded ? 'Already Downloaded' : 'Download'"></span>
                </span>
                <span x-show="loading && currentId === indicator.id">
                  <span class="spinner-border spinner-border-sm"></span> Downloading...
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>

  <div x-show="results.length === 0 && !loading" class="text-center py-5">
    <i class="bi bi-inbox fs-1 text-secondary"></i>
    <p class="text-secondary mt-2">No indicators found. Try a different search.</p>
  </div>

  <div x-show="loading && results.length === 0" class="text-center py-5">
    <div class="spinner-border text-primary"></div>
    <p class="text-secondary mt-2">Loading indicators...</p>
  </div>
</div>

<script>
function availableData() {
  return {
    searchQuery: '',
    sourceFilter: '',
    results: [],
    loading: false,
    currentId: null,

    init() {
      this.search();
    },

    async search() {
      this.loading = true;
      try {
        const params = new URLSearchParams();
        if (this.searchQuery) params.append('q', this.searchQuery);
        if (this.sourceFilter) params.append('source', this.sourceFilter);
        
        const response = await fetch(`/api/search?${params}`);
        const data = await response.json();
        
        if (data.status === 'success' || data.results) {
          this.results = data.results || [];
        } else {
          console.error('Search error:', data.message);
          this.results = [];
        }
      } catch (error) {
        console.error('Search failed:', error);
        this.results = [];
      } finally {
        this.loading = false;
      }
    },

    async download(indicator) {
      if (indicator.downloaded) return;
      
      this.loading = true;
      this.currentId = indicator.id;
      
      try {
        const response = await fetch('/api/download/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: indicator.id,
            source: indicator.source.toLowerCase(),
            indicator: indicator.indicator,
            remote: indicator.remote || false
          })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
          indicator.downloaded = true;
          alert(`Downloaded: ${indicator.indicator}`);
        } else {
          alert(`Download failed: ${data.message}`);
        }
      } catch (error) {
        console.error('Download failed:', error);
        alert('Download failed. Check console for details.');
      } finally {
        this.loading = false;
        this.currentId = null;
      }
    }
  }
}
</script>
{% endblock %}
```

**Step 2: Add route for browse_available**

Add to `src/web/routes.py` after line 124:

```python
@ui_bp.route("/browse/available")
@ui_bp.route("/browse_available")
def browse_available() -> str:
    ctx = base_context(
        "browse_available", "Browse Available", "Indicadores disponibles para descargar"
    )
    return render_template("browse_available.html", **ctx)
```

**Step 3: Update NAV_ITEMS in routes.py**

Change line 82-88 to include new navigation item:

```python
NAV_ITEMS: List[Dict[str, str]] = [
    {"slug": "status", "label": "Status", "icon": "house"},
    {"slug": "browse_local", "label": "Browse Local", "icon": "folder"},
    {"slug": "browse_available", "label": "Browse Available", "icon": "cloud-download"},
    {"slug": "search", "label": "Search", "icon": "search"},
    {"slug": "chat", "label": "Chat AI", "icon": "chat"},
    {"slug": "help", "label": "Help", "icon": "question-circle"},
]
```

**Step 4: Test template**

Run: `python -c "from src.web.routes import ui_bp; print('Template syntax OK')"`
Expected: "Template syntax OK" (or no output if no syntax errors)

**Step 5: Commit**

```bash
git add src/web/templates/browse_available.html src/web/routes.py
git commit -m "feat: Add browse available indicators template with Alpine.js"
```

---

## Task 3: Enhance Search Template with Download Functionality

**Files:**
- Read: `src/web/templates/search.html`
- Modify: `src/web/templates/search.html` (add download functionality)

**Step 1: Read current search.html**

```bash
cat src/web/templates/search.html
```

**Step 2: Enhance with download buttons and Alpine.js data**

Add download functionality to search results. The template should include:
- Download button for each result
- Loading states
- Success/error feedback

Replace the entire content with enhanced version (if it's basic) or add Alpine.js component.

**Step 3: Test**

Open browser and verify search page loads with download buttons.

**Step 4: Commit**

```bash
git add src/web/templates/search.html
git commit -m "feat: Add download functionality to search template"
```

---

## Task 4: Implement SSE Progress Endpoints

**Files:**
- Modify: `src/web/routes.py` (add after line 750)

**Step 1: Add progress tracking data store**

Add at the top of routes.py (after imports, around line 40):

```python
# In-memory progress tracking for SSE
_download_progress: Dict[str, Dict] = {}
```

**Step 2: Add SSE stream endpoint**

Add at the end of routes.py:

```python
@ui_bp.route("/api/progress/stream")
def progress_stream() -> Response:
    """SSE endpoint for real-time download progress."""
    def generate():
        last_sent = None
        while True:
            # Get current progress (would be updated by download process)
            progress = _download_progress.get('current', {
                'step': 'idle',
                'status': 'waiting',
                'percent': 0
            })
            
            # Only send if changed
            if progress != last_sent:
                yield f"data: {json.dumps(progress)}\n\n"
                last_sent = progress.copy()
            
            time.sleep(1)  # Check every second
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@ui_bp.route("/api/progress/poll")
def progress_poll() -> Response:
    """Polling fallback for browsers without SSE support."""
    progress = _download_progress.get('current', {
        'step': 'idle',
        'status': 'waiting',
        'percent': 0
    })
    return jsonify(progress)
```

**Step 3: Update download endpoint to emit progress**

Modify the `start_download` function to update progress:

In `start_download()`, add progress updates:

```python
# At start of download
_download_progress['current'] = {
    'step': 'downloading',
    'status': f'Downloading {indicator_name}...',
    'percent': 25
}

# After successful download
_download_progress['current'] = {
    'step': 'cleaning',
    'status': 'Processing data...',
    'percent': 50
}

# After cleaning
_download_progress['current'] = {
    'step': 'documenting',
    'status': 'Generating metadata...',
    'percent': 75
}

# At completion
_download_progress['current'] = {
    'step': 'complete',
    'status': f'Complete: {indicator_name}',
    'percent': 100
}
```

**Step 4: Test endpoints**

Run Flask and test:
- `curl http://localhost:5000/api/progress/poll`
- Open browser and check EventSource connection to `/api/progress/stream`

**Step 5: Commit**

```bash
git add src/web/routes.py
git commit -m "feat: Add SSE progress endpoints with polling fallback"
```

---

## Task 5: Enhance JavaScript App

**Files:**
- Modify: `src/web/static/js/app.js`

**Step 1: Add search functionality**

Add to app.js:

```javascript
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
```

**Step 2: Update SSE progress helper**

Update the existing `attachProgressStream` function to be more robust:

```javascript
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
```

**Step 3: Export all functions**

Make sure all functions are exported for use in templates:

```javascript
// Make functions available globally for inline scripts
window.MisesApp = {
  searchIndicators,
  downloadIndicator,
  listDatasets,
  previewDataset,
  deleteDataset,
  refreshCatalog,
  attachProgressStream
};
```

**Step 4: Test JavaScript**

Open browser console and verify:
- `window.MisesApp` exists
- Functions are callable

**Step 5: Commit**

```bash
git add src/web/static/js/app.js
git commit -m "feat: Enhance JavaScript with search, download, and dataset functions"
```

---

## Task 6: Update Browse Local Template with New Functions

**Files:**
- Read: `src/web/templates/browse_local.html`
- Modify: `src/web/templates/browse_local.html`

**Step 1: Enhance with Alpine.js and dataset loading**

Update browse_local.html to use the new JavaScript functions:

- Add Alpine.js data component
- Load datasets from API
- Add preview modal
- Add delete functionality

**Step 2: Test**

Verify:
- Datasets load from API
- Preview button works
- Delete confirmation works

**Step 3: Commit**

```bash
git add src/web/templates/browse_local.html
git commit -m "feat: Enhance browse local with API integration and actions"
```

---

## Task 7: Test Complete Web Interface

**Files:**
- Test: All routes and templates

**Step 1: Start Flask server**

```bash
python -m src.web
```

**Step 2: Verify all routes load**

Test each URL:
- http://localhost:5000/ (status)
- http://localhost:5000/browse_local
- http://localhost:5000/browse_available
- http://localhost:5000/search
- http://localhost:5000/chat
- http://localhost:5000/help

**Step 3: Verify API endpoints**

Test:
- http://localhost:5000/api/datasets
- http://localhost:5000/api/search?q=gdp
- http://localhost:5000/api/progress/poll

**Step 4: Test SSE endpoint**

Open browser console:
```javascript
const es = new EventSource('/api/progress/stream');
es.onmessage = (e) => console.log(JSON.parse(e.data));
```

**Step 5: Commit**

```bash
git commit -m "test: Verify all web interface routes and endpoints"
```

---

## Summary

After completing these tasks, the web interface will have:

1. ✅ All templates complete and functional
2. ✅ No broken references to removed routes
3. ✅ Browse Available indicators page
4. ✅ SSE progress tracking with polling fallback
5. ✅ Enhanced JavaScript with all API functions
6. ✅ Fully interactive search, download, and browse functionality

**Estimated Time:** 3-4 hours
**Complexity:** Medium (mostly frontend work with some backend SSE)
