# TUI Implementation Roadmap

## 📋 Executive Summary

This document provides the **step-by-step implementation plan** for building the Textual-based TUI for the MISES economic data curation tool.

**Estimated Timeline**: 4-5 working days for complete implementation
**Complexity**: Medium (reuses existing data/config, focuses on UI)
**Risk Level**: Low (doesn't modify core functionality, independent module)

---

## 🎯 Phase Breakdown

### Phase 1: Foundation (Day 1)
**Goal**: Set up Textual framework and basic structure

#### 1.1 Project Setup
```python
# src/tui/__init__.py
# Create TUI package

# requirements.txt
# Add: textual >= 0.50.0, rich >= 13.0.0

# src/tui/app.py
class MisesApp(App):
    """Main Textual application."""
    def on_mount(self):
        # Initialize screens
        pass
```

**Deliverables**:
- `src/tui/` package created
- Dependencies installed
- Basic app structure

**Time**: 30 minutes

#### 1.2 Theme & Styling
```python
# src/tui/colors.py
THEME = {
    "primary": "cyan",
    "success": "green",
    "warning": "orange",
    "error": "red",
    # ... more colors
}

# src/tui/config.py
TUI_CONFIG = {
    "min_width": 80,
    "min_height": 24,
    "default_screen": "status",
    # ... more settings
}
```

**Deliverables**:
- Theme definition
- Configuration constants
- Color palette defined

**Time**: 20 minutes

#### 1.3 Base Screen Class
```python
# src/tui/screens/base.py
class BaseScreen(Screen):
    """Base class for all TUI screens."""
    def __init__(self, app):
        super().__init__()
        self.app_ref = app
        self.data = {}
    
    def on_mount(self):
        """Override in subclasses."""
        pass
    
    def refresh_data(self):
        """Refresh screen data from disk/API."""
        pass
```

**Deliverables**:
- Base screen abstraction
- Common methods
- Data refresh pattern

**Time**: 25 minutes

#### 1.4 Sidebar Navigation
```python
# src/tui/widgets/sidebar.py
class SidebarNavigation(Static):
    """Main navigation sidebar."""
    
    MENU_ITEMS = [
        ("Browse Local", "browse_local", "📂"),
        ("Browse Available", "browse_available", "📥"),
        # ... more items
    ]
```

**Deliverables**:
- Sidebar widget
- Menu rendering
- Selection tracking

**Time**: 40 minutes

**Phase 1 Total**: ~2 hours ✓

---

### Phase 2: Data Browsing Screens (Day 1-2)
**Goal**: Implement screens for exploring local and available data

#### 2.1 Browse Local Screen
```python
# src/tui/screens/browse_local.py
class BrowseLocalScreen(BaseScreen):
    """Browse downloaded datasets organized by topic."""
    
    def on_mount(self):
        # Load topics from 02_Datasets_Limpios/
        # Build tree view widget
        pass
    
    def on_select_topic(self, topic):
        # Load datasets for topic
        pass
    
    def on_select_dataset(self, dataset):
        # Show details panel
        pass
```

**Sub-tasks**:
- Load topic structure from filesystem
- Create collapsible tree widget
- Display dataset details on selection
- Add metadata preview panel

**Deliverables**:
- Topic tree view
- Dataset listing
- Details panel
- File size calculation

**Time**: 1.5 hours

#### 2.2 Browse Available Screen
```python
# src/tui/screens/browse_available.py
class BrowseAvailableScreen(BaseScreen):
    """Browse available indicators from all sources."""
    
    def on_mount(self):
        # Load sources from indicators.yaml
        # Build source list
        pass
    
    def on_select_source(self, source):
        # Load indicators for source
        # Show details panel
        pass
```

**Sub-tasks**:
- Load sources from indicators.yaml
- Create source card view
- List indicators per source
- Show indicator details

**Deliverables**:
- Source listing
- Indicator browsing
- Details panel
- Coverage info

**Time**: 1.5 hours

#### 2.3 Search Screen
```python
# src/tui/screens/search.py
class SearchScreen(BaseScreen):
    """Search indicators across sources."""
    
    def __init__(self, app):
        super().__init__(app)
        self.search_query = ""
        self.filters = {}
    
    def on_search_input(self, query):
        # Fuzzy search in indicators
        # Apply filters
        # Display results
        pass
```

**Sub-tasks**:
- Create search input widget
- Implement fuzzy matching
- Create filter controls
- Display results list
- Quick details panel

**Deliverables**:
- Search input box
- Filter controls (topic, source, status)
- Results display
- Selection details

**Time**: 1.5 hours

**Phase 2 Total**: ~4.5 hours ✓

---

### Phase 3: Data Management Screens (Day 2-3)
**Goal**: Implement download and progress monitoring

#### 3.1 Download Manager Screen
```python
# src/tui/screens/download.py
class DownloadScreen(BaseScreen):
    """Manage downloads and configure parameters."""
    
    def __init__(self, app):
        super().__init__(app)
        self.download_params = {}
        self.queue = []
    
    def on_source_select(self, source):
        # Update dynamic form fields
        pass
    
    def on_preview(self):
        # Show download preview
        pass
    
    def on_download(self):
        # Start download process
        pass
```

**Sub-tasks**:
- Create form with source selector
- Dynamic field updates based on source
- Country multi-select widget
- Year range slider
- Download preview
- Queue management

**Deliverables**:
- Download form
- Dynamic field generation
- Country selector
- Year range picker
- Queue display

**Time**: 2 hours

#### 3.2 Progress Monitor
```python
# src/tui/screens/progress.py
class ProgressScreen(BaseScreen):
    """Monitor active downloads."""
    
    def __init__(self, app):
        super().__init__(app)
        self.progress_data = {}
        self.log_buffer = []
    
    def watch_progress(self, step, percent):
        # Update progress bar
        pass
    
    def watch_logs(self, new_log):
        # Add to log display
        pass
```

**Sub-tasks**:
- Progress bar rendering (3 steps)
- Step indicator
- Real-time log display
- Cancel button
- Background mode option

**Deliverables**:
- Progress bars
- Step indicators
- Log viewer
- Cancel functionality

**Time**: 1.5 hours

#### 3.3 Status Dashboard
```python
# src/tui/screens/status.py
class StatusScreen(BaseScreen):
    """Display project overview and statistics."""
    
    def on_mount(self):
        # Calculate directory stats
        # Check API connectivity
        # Load recent activity
        pass
    
    def on_refresh(self):
        # Recalculate all stats
        pass
```

**Sub-tasks**:
- Directory size calculation
- Dataset counting
- API status checking
- Recent activity log
- Progress bars

**Deliverables**:
- Statistics display
- Directory info
- Source status
- Activity log

**Time**: 1 hour

**Phase 3 Total**: ~4.5 hours ✓

---

### Phase 4: Modals & Dialogs (Day 3)
**Goal**: Implement metadata viewer and confirmation dialogs

#### 4.1 Metadata Viewer Modal
```python
# src/tui/widgets/metadata_viewer.py
class MetadataViewer(Modal):
    """Display full markdown metadata."""
    
    def __init__(self, dataset_name):
        super().__init__()
        self.dataset = dataset_name
        self.markdown_content = ""
    
    def on_mount(self):
        # Load markdown file
        # Render with syntax highlighting
        pass
```

**Sub-tasks**:
- Markdown rendering
- Syntax highlighting
- Scrollable content
- Copy to clipboard
- Export options

**Deliverables**:
- Metadata modal
- Markdown renderer
- Copy button
- Export button

**Time**: 1 hour

#### 4.2 Confirmation Dialogs
```python
# src/tui/widgets/dialogs.py
class ConfirmDialog(Modal):
    """Generic confirmation dialog."""
    
    def __init__(self, title, message, on_confirm):
        super().__init__()
        self.title = title
        self.message = message
        self.on_confirm = on_confirm
```

**Sub-tasks**:
- Delete confirmation
- Download confirmation
- Clear cache confirmation
- Custom dialogs

**Deliverables**:
- Confirmation dialog class
- Yes/No buttons
- Callback mechanism

**Time**: 45 minutes

#### 4.3 Input Dialogs
```python
# src/tui/widgets/input.py
class InputDialog(Modal):
    """Generic input dialog."""
    pass

class SelectDialog(Modal):
    """Dropdown/multi-select dialog."""
    pass
```

**Sub-tasks**:
- Text input dialog
- Dropdown dialog
- Multi-select dialog
- Validation

**Deliverables**:
- Input dialog classes
- Validation support
- Callback mechanism

**Time**: 45 minutes

**Phase 4 Total**: ~2.5 hours ✓

---

### Phase 5: Data Layer (Day 4)
**Goal**: Build data access layer connecting TUI to existing code

#### 5.1 Local Data Manager
```python
# src/tui/data/local_manager.py
class LocalDataManager:
    """Manage local filesystem operations."""
    
    def __init__(self, config):
        self.config = config
        self.cache = {}
        self.last_refresh = 0
    
    def get_topics(self):
        # Read from 02_Datasets_Limpios/
        # Return list of topics
        pass
    
    def get_datasets(self, topic):
        # Return datasets in topic
        pass
    
    def get_metadata(self, dataset):
        # Load markdown metadata
        pass
    
    def get_directory_stats(self):
        # Calculate sizes
        pass
```

**Sub-tasks**:
- Directory scanning
- Metadata loading
- Size calculation
- Cache management
- File watching

**Deliverables**:
- Local data manager class
- Caching layer
- File I/O utilities

**Time**: 1 hour

#### 5.2 API Data Manager
```python
# src/tui/data/api_manager.py
class APIDataManager:
    """Query available data from indicators.yaml."""
    
    def __init__(self, config):
        self.config = config
        self.indicators = {}
    
    def get_sources(self):
        # Return all sources
        pass
    
    def get_indicators(self, source):
        # Return indicators for source
        pass
    
    def search_indicators(self, query, filters):
        # Fuzzy search with filtering
        pass
    
    def check_api_status(self):
        # Ping each API
        pass
```

**Sub-tasks**:
- Indicator loading
- Fuzzy search implementation
- Filter logic
- API connectivity checks
- Caching

**Deliverables**:
- API data manager class
- Search algorithm
- Status checking

**Time**: 1.5 hours

#### 5.3 Download Coordinator
```python
# src/tui/data/download_coordinator.py
class DownloadCoordinator:
    """Orchestrate download process."""
    
    def __init__(self, config):
        self.config = config
        self.manager = DataIngestionManager(config)
        self.queue = []
        self.current = None
    
    def add_to_queue(self, download_spec):
        # Add download to queue
        pass
    
    def start_download(self, spec):
        # Call existing pipeline
        # Track progress
        # Update UI
        pass
    
    def on_progress(self, callback):
        # Register progress callback
        pass
```

**Sub-tasks**:
- Download queuing
- Process orchestration
- Progress tracking
- Error handling
- Logging

**Deliverables**:
- Download coordinator
- Progress callback system
- Error handling

**Time**: 1.5 hours

#### 5.4 Caching Layer
```python
# src/tui/data/cache.py
class TUICache:
    """Local caching for TUI data."""
    
    def __init__(self, ttl=3600):
        self.ttl = ttl
        self.cache = {}
    
    def get(self, key):
        pass
    
    def set(self, key, value):
        pass
    
    def invalidate(self, pattern):
        pass
```

**Deliverables**:
- Cache class with TTL
- Invalidation logic
- Cache management

**Time**: 45 minutes

**Phase 5 Total**: ~5 hours ✓

---

### Phase 6: Integration & Testing (Day 4-5)
**Goal**: Connect all pieces, test, and deploy

#### 6.1 Screen Navigation
```python
# src/tui/app.py - Modified
class MisesApp(App):
    def __init__(self):
        super().__init__()
        self.screens = {
            "browse_local": BrowseLocalScreen,
            "browse_available": BrowseAvailableScreen,
            "search": SearchScreen,
            "download": DownloadScreen,
            "progress": ProgressScreen,
            "status": StatusScreen,
            "help": HelpScreen,
        }
    
    def switch_to(self, screen_name):
        # Navigate to screen
        pass
```

**Sub-tasks**:
- Screen registration
- Navigation logic
- History management
- Shortcut routing

**Deliverables**:
- Navigation system
- Screen switching
- Keyboard routing

**Time**: 1 hour

#### 6.2 Event Binding
```python
# Connect screens to data managers
# Bind actions to callbacks
# Wire up progress tracking
# Connect keyboard shortcuts
```

**Deliverables**:
- Event system
- Callback routing
- Keyboard mapping

**Time**: 1.5 hours

#### 6.3 Testing
```python
# Test scenarios:
# 1. Browse local data - expand/collapse topics
# 2. View metadata - scroll and copy
# 3. Search indicators - filters work
# 4. Download manager - form validation
# 5. Download flow - end-to-end
# 6. Keyboard navigation - all screens
# 7. Error handling - graceful failures
```

**Deliverables**:
- Test checklist
- Bug fixes
- Edge case handling

**Time**: 2 hours

#### 6.4 Entry Point
```python
# src/tui/__main__.py
if __name__ == "__main__":
    app = MisesApp()
    app.run()

# Also add CLI integration:
# python -m src.tui

# And update CLI:
# curate tui
```

**Deliverables**:
- Entry point
- CLI integration
- Command alias

**Time**: 30 minutes

#### 6.5 Documentation
```python
# TUI_README.md
# - Installation
# - Running
# - Keyboard shortcuts
# - Screen descriptions
# - Troubleshooting
```

**Deliverables**:
- TUI documentation
- User guide
- Troubleshooting guide

**Time**: 1 hour

**Phase 6 Total**: ~6 hours ✓

---

## 📊 Implementation Timeline

```
Day 1 (8 hours):
├─ Phase 1: Foundation (2h)
│  └─ Setup, theme, base class, sidebar
├─ Phase 2.1: Browse Local (1.5h)
└─ Phase 2.2: Browse Available (1.5h)
└─ Phase 2.3: Search (1.5h)

Day 2 (8 hours):
├─ Phase 3.1: Download Manager (2h)
├─ Phase 3.2: Progress Monitor (1.5h)
├─ Phase 3.3: Status Dashboard (1h)
├─ Phase 4.1: Metadata Viewer (1h)
├─ Phase 4.2: Confirmation (45min)
└─ Phase 4.3: Input Dialogs (45min)

Day 3 (8 hours):
├─ Phase 5.1: Local Data Manager (1h)
├─ Phase 5.2: API Data Manager (1.5h)
├─ Phase 5.3: Download Coordinator (1.5h)
├─ Phase 5.4: Cache Layer (45min)
└─ Buffer/Catch-up (3.5h)

Day 4 (8 hours):
├─ Phase 6.1: Navigation (1h)
├─ Phase 6.2: Event Binding (1.5h)
├─ Phase 6.3: Testing (2h)
├─ Phase 6.4: Entry Point (30min)
├─ Phase 6.5: Documentation (1h)
└─ Buffer (2h)

TOTAL: 32 hours = ~4 working days
```

---

## 🔧 Technical Details

### Import Structure
```python
# Top-level TUI imports
from .app import MisesApp
from .screens import (
    BrowseLocalScreen,
    BrowseAvailableScreen,
    SearchScreen,
    DownloadScreen,
    ProgressScreen,
    StatusScreen,
    HelpScreen,
)
from .data import (
    LocalDataManager,
    APIDataManager,
    DownloadCoordinator,
)
```

### Data Flow
```
TUI Screen
    ↓
Data Manager (Local/API)
    ↓
Configuration (existing)
    ↓
File System / Indicators.yaml
    ↓
[Response bubbles back up]
```

### Integration Points
```
TUI Download Screen
    ↓
Download Coordinator
    ↓
DataIngestionManager (existing)
    ↓
Cleaning (existing)
    ↓
Metadata Generation (existing)
    ↓
File System
```

---

## ✅ Acceptance Criteria

### Phase 1
- [ ] TUI app runs without errors
- [ ] Sidebar displays correctly
- [ ] Theme colors apply properly

### Phase 2
- [ ] Browse Local shows topics and datasets
- [ ] Browse Available shows sources and indicators
- [ ] Search works with keyword filtering

### Phase 3
- [ ] Download form displays correctly
- [ ] Progress screen shows 3 steps
- [ ] Status dashboard loads data

### Phase 4
- [ ] Metadata modal renders markdown
- [ ] Confirmation dialogs work
- [ ] Input dialogs accept values

### Phase 5
- [ ] Local data manager reads filesystem
- [ ] API data manager loads indicators
- [ ] Download coordinator triggers downloads
- [ ] Cache works with TTL

### Phase 6
- [ ] All screens navigate properly
- [ ] Events trigger correctly
- [ ] Keyboard navigation works
- [ ] Download completes end-to-end
- [ ] No crashes on edge cases

---

## 🚀 Deployment

### Installation
```bash
# In existing project
pip install textual>=0.50.0 rich>=13.0.0

# Copy TUI module
# src/tui/ → existing codebase
```

### Running
```bash
# Method 1: Direct
python -m src.tui

# Method 2: Through CLI
curate tui

# Method 3: From entry point
python src/tui/__main__.py
```

### File Structure After Implementation
```
c:\dev\mises\
├── src/
│   ├── __init__.py
│   ├── cli.py (existing)
│   ├── config.py (existing)
│   ├── ingestion.py (existing)
│   ├── cleaning.py (existing)
│   ├── metadata.py (existing)
│   ├── searcher.py (existing)
│   │
│   └── tui/                 ← NEW
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── colors.py
│       ├── config.py
│       ├── widgets/
│       │   ├── sidebar.py
│       │   ├── metadata_viewer.py
│       │   ├── dialogs.py
│       │   ├── input.py
│       │   └── components.py
│       ├── screens/
│       │   ├── base.py
│       │   ├── browse_local.py
│       │   ├── browse_available.py
│       │   ├── search.py
│       │   ├── download.py
│       │   ├── progress.py
│       │   ├── status.py
│       │   └── help.py
│       └── data/
│           ├── local_manager.py
│           ├── api_manager.py
│           ├── download_coordinator.py
│           └── cache.py
└── TUI_DESIGN_PLAN.md (this file)
└── TUI_MOCKUPS.md (mockups)
```

---

## 📈 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| App Startup | < 500ms | — |
| Screen Switch | < 100ms | — |
| Search Results | < 500ms | — |
| Browse Local Load | < 1s | — |
| Keyboard Response | < 50ms | — |
| Memory Usage | < 100MB | — |
| No Crashes | 100% | — |
| All Features Work | 100% | — |

---

## 🎓 Notes

### Why Textual?
- Pure Python, no external dependencies
- Rich integration for beautiful output
- Keyboard & mouse support
- Runs in any terminal
- Active development, good docs

### Reusing Existing Code
- Use existing `Config` class as-is
- Use existing `DataIngestionManager` directly
- No modifications to core functionality
- TUI is pure wrapper/UI layer

### Future Enhancements
- Mouse wheel scrolling support
- Theme customization
- Settings persistence
- Download history
- Favorites system

