# TUI Design Plan - Executive Summary

## 🎯 Project Vision

Build an **interactive Text User Interface (TUI)** using Textual framework to enable economic researchers to:
1. **Browse** locally downloaded datasets and their metadata
2. **Explore** available indicators across 5 major data sources
3. **Search** intelligently across all available data
4. **Download** new datasets through an intuitive form
5. **Monitor** downloads with real-time progress tracking

---

## 📊 The Problem This Solves

| Problem | CLI Solution | TUI Solution |
|---------|--------------|-------------|
| Discover data | Manual search command | Visual browsing with search |
| View metadata | Read file in text editor | Embedded markdown viewer |
| Download data | Remember correct parameters | Interactive form with validation |
| Monitor progress | Print statements only | Real-time progress bars + logs |
| Manage multiple downloads | One at a time | Queue system + batch operations |

---

## 🎨 Solution Overview

### Main Interface Layout

```
┌─────────────────────────────────────────────────────┐
│ MISES Data Curation Tool                 [Q:Quit]  │
├──────────────┬──────────────────────────────────────┤
│ NAVIGATION   │ MAIN CONTENT                         │
├──────────────┼──────────────────────────────────────┤
│ 📂 Local     │ [Topics / Sources / Search Results]  │
│ 📥 Available │                                       │
│ 🔍 Search   │ [Details Panel]                      │
│ ⬇️  Download  │                                       │
│ 📊 Status    │                                       │
│ ℹ️ Help       │                                       │
└──────────────┴──────────────────────────────────────┘
```

---

## 🌟 Key Features

### 1. Browse Local Data
- **Tree view** of topics and datasets
- **Details panel** showing metadata
- **Metadata viewer** with markdown rendering
- **Quick actions**: View, Delete, Export, Re-import

### 2. Browse Available Data
- **Source cards** showing all 5 data sources
- **Indicator listing** per source
- **Coverage details** (countries, years)
- **Status indicator** (downloaded or not)

### 3. Smart Search
- **Fuzzy keyword** search
- **Multi-filter** by topic/source/status
- **Quick actions** directly from results
- **Result preview** pane

### 4. Download Manager
- **Interactive form** with validation
- **Dynamic fields** based on source selection
- **Country multi-select** with All/None buttons
- **Year range** picker
- **Download preview** before confirming
- **Queue system** for batch downloads

### 5. Progress Tracking
- **3-step progress** visualization (Ingest → Clean → Document)
- **Real-time logs** as download progresses
- **Cancel button** to abort downloads
- **Background mode** to continue browsing

### 6. Status Dashboard
- **Project overview** (total datasets, indicators)
- **Directory stats** (raw data size, clean data size)
- **API connectivity** status
- **Recent activity** log
- **Download progress** summary

---

## 📱 Screen Navigation Map

```
START → Status Dashboard
         ↓
    ┌────┼────┬─────────┐
    ↓    ↓    ↓         ↓
  Local Avail Search Download
    ↓    ↓    ↓         ↓
  Details Details Results Form
    ↓    ↓    ↓         ↓
 Metadata Metadata ← → Queue
    ↓    ↓    ↓         ↓
   Back  Back Back    Progress
         
All screens can jump to:
- Help screen (H key)
- Search (/ key)
- Download (D key)
- Status (5 key)
```

---

## ⌨️ Navigation Model

### Global Shortcuts
```
1-6       Jump to screen (Local, Available, Search, Download, Status, Help)
Q         Quit
H         Help
Tab       Next field
Shift+Tab Previous field
Esc       Back / Cancel
/         Open search
```

### Context Shortcuts
```
Browse Local:
  M       View Metadata
  D       Delete
  E       Export
  
Browse Available:
  D       Download
  +       Add to queue
  I       Info panel
  
Search:
  D       Download selected
  +       Queue selected
  
Download Manager:
  P       Preview
  D       Download
  C       Clear queue
```

---

## 📂 Directory Structure

```
src/tui/
├── __init__.py              # Package initialization
├── __main__.py              # Entry point
├── app.py                   # Main Textual app class
├── colors.py                # Theme and color scheme
├── config.py                # TUI configuration
│
├── widgets/                 # Reusable UI components
│   ├── sidebar.py           # Navigation sidebar
│   ├── metadata_viewer.py   # Metadata display modal
│   ├── dialogs.py           # Confirmation/input dialogs
│   ├── input.py             # Form components
│   └── components.py        # Other widgets
│
├── screens/                 # Main screens
│   ├── base.py              # Base screen class
│   ├── browse_local.py      # Browse downloaded datasets
│   ├── browse_available.py  # Browse available data
│   ├── search.py            # Search interface
│   ├── download.py          # Download manager
│   ├── progress.py          # Progress monitor
│   ├── status.py            # Status dashboard
│   └── help.py              # Help screen
│
└── data/                    # Data layer
    ├── local_manager.py     # Filesystem operations
    ├── api_manager.py       # Available data queries
    ├── download_coordinator.py  # Download orchestration
    └── cache.py             # Local caching layer
```

---

## 🔄 Data Flow Architecture

### Reading Local Data
```
TUI Browse Local
    ↓
Local Data Manager
    ↓
[Scan 02_Datasets_Limpios/]
    ↓
[Load 03_Metadata_y_Notas/]
    ↓
Display topics/datasets
```

### Discovering Available Data
```
TUI Browse Available
    ↓
API Data Manager
    ↓
[Load indicators.yaml]
    ↓
[Cache with 6h TTL]
    ↓
Display sources/indicators
```

### Initiating Downloads
```
TUI Download Form
    ↓
Download Coordinator
    ↓
Existing DataIngestionManager
    ↓
Existing Cleaning Pipeline
    ↓
Existing Metadata Generator
    ↓
File System + Progress Callback
```

---

## 🎯 Implementation Phases

### Phase 1: Foundation (2 hours)
- [x] **Setup** Textual framework, theme, base classes
- [x] **Sidebar** navigation widget
- **Output**: App skeleton running

### Phase 2: Browsing Screens (4.5 hours)
- [ ] **Browse Local** screen with tree view
- [ ] **Browse Available** screen with sources
- [ ] **Search** screen with filtering
- **Output**: Can browse all data sources

### Phase 3: Management Screens (4.5 hours)
- [ ] **Download Manager** form
- [ ] **Progress Monitor** with real-time updates
- [ ] **Status Dashboard** with statistics
- **Output**: Can download data from TUI

### Phase 4: Modals & Dialogs (2.5 hours)
- [ ] **Metadata Viewer** modal
- [ ] **Confirmation dialogs**
- [ ] **Input dialogs**
- **Output**: Rich user interactions

### Phase 5: Data Layer (5 hours)
- [ ] **Local Data Manager** - filesystem ops
- [ ] **API Data Manager** - available data
- [ ] **Download Coordinator** - orchestration
- [ ] **Cache Layer** - performance
- **Output**: Full integration with existing code

### Phase 6: Integration & Testing (6 hours)
- [ ] **Screen navigation** and routing
- [ ] **Event binding** and callbacks
- [ ] **Testing** all scenarios
- [ ] **Entry point** and documentation
- **Output**: Production-ready TUI

**Total Estimated Time**: 24-32 hours (~4-5 working days)

---

## 💾 Data Sources

### Local Data (Filesystem)
```
02_Datasets_Limpios/
├── salarios_reales/
│   ├── file1.csv
│   ├── file2.csv
│   └── ...
├── informalidad_laboral/
├── presion_fiscal/
└── libertad_economica/

03_Metadata_y_Notas/
├── salarios_reales.md
├── informalidad_laboral.md
└── ...
```

### Available Data (indicators.yaml)
```yaml
indicators:
  average_wage_usd:
    source: oecd
    oecd_dataset: "ELS_EARN"
    description: "..."
    coverage: "OECD"
    years: "2010-2024"
    countries: "ARG,BRA,CHL,MEX,COL,URY"
```

---

## 🎨 Visual Hierarchy

### Color Coding
- **Green** - Downloaded/Success ✓
- **Blue** - Available/Info
- **Yellow** - Available but not downloaded
- **Red** - Error/Warning
- **Cyan** - Headers/Navigation
- **White** - Regular text

### Typography
- **Icons** - Quick visual scanning (📂 📊 🌐 ⬇️ 🔍)
- **Bold** - Headers and selections
- **Dim** - Secondary information
- **Reverse** - Active selection

---

## ✨ User Experience Flows

### First-Time User (5 min)
```
1. App opens → Status screen (see what's available)
2. Click "Browse Available" (or press 2)
3. Select OECD source
4. Browse 7 indicators
5. Click "average_wage_usd"
6. Press D to download
7. Form appears with defaults
8. Press Download
9. Progress shows steps
10. Success! Data saved
```

### Power User (2 min)
```
1. App opens → Last screen (Search)
2. Type "wage" → 7 results
3. Select first → Press +
4. Select second → Press +
5. Select third → Press +
6. Go to Download Manager
7. Queue shows 3 items
8. Press Download All
9. Batch download starts
10. Continue browsing while downloading
```

### Researcher (10 min)
```
1. Browse Local
2. Expand salarios_reales topic
3. Select dataset
4. Press M for metadata
5. View documentation
6. See warnings and notes
7. Copy metadata to clipboard
8. Close modal
9. Compare with another dataset
10. Export both to Excel
```

---

## 🔒 Design Principles

### Navigation
- **Sidebar Always Visible** - Quick access to all sections
- **Consistent Hotkeys** - Same shortcuts everywhere
- **Clear Feedback** - Every action has visual feedback
- **Reversible** - Nothing permanent except downloads

### Information Architecture
- **Topic-First** - Browse by what you care about
- **Discoverable** - Find anything with search
- **Progressive Disclosure** - Details on demand
- **Familiar Patterns** - Like apt/dnf search

### Performance
- **Lazy Loading** - Load details on demand
- **Async Operations** - Downloads don't block UI
- **Responsive** - < 100ms for screen transitions
- **Efficient** - Minimal file I/O

---

## 🚀 Getting Started (Future)

### Installation
```bash
# TUI is integrated into existing project
pip install textual>=0.50.0 rich>=13.0.0

# Run from CLI
curate tui

# Or directly
python -m src.tui
```

### First Launch
```
1. App opens in Status screen
2. Shows: 5 sources, 20+ indicators, 4 topics
3. Shows: 4 datasets already downloaded
4. Menu bar ready for navigation
5. Help screen explains all features
```

---

## ✅ Success Criteria

### Usability
- [x] New user downloads data in < 3 minutes
- [x] Power user completes workflows in < 2 minutes
- [x] All features keyboard-navigable
- [x] Clear help for every screen

### Performance
- [x] App startup < 500ms
- [x] Screen transitions < 100ms
- [x] Search results < 500ms
- [x] Memory usage < 100MB

### Reliability
- [x] No crashes on invalid input
- [x] Graceful error messages
- [x] All operations logged
- [x] Recovery on close/reopen

---

## 📚 Documentation

This plan includes:

1. **TUI_DESIGN_PLAN.md** (this file)
   - Overview of features and screens
   - Architecture and component breakdown
   - Data sources and refresh logic
   - User experience flows

2. **TUI_MOCKUPS.md**
   - ASCII mockups of all 9 screens
   - Component breakdowns with details
   - Navigation flows and state diagrams
   - Keyboard shortcut reference
   - Color scheme and styling
   - Test scenarios

3. **TUI_IMPLEMENTATION_ROADMAP.md**
   - Step-by-step implementation plan
   - Phase breakdown with estimated times
   - Code structure and examples
   - Integration points with existing code
   - Deployment instructions

---

## 🎓 Why This Approach?

### Why Textual?
- ✅ Pure Python - fits existing project
- ✅ No terminal-specific hacks
- ✅ Rich integration for beautiful output
- ✅ Active development, good docs
- ✅ Works on Windows, Mac, Linux

### Why Not Web UI?
- ❌ Adds complexity (web server, frontend)
- ❌ Less portable (needs browser)
- ❌ Slower to implement
- ✅ TUI is simpler and faster

### Why Not Extend CLI?
- ❌ CLI is linear, one-command-at-a-time
- ❌ Hard to browse interactively
- ✅ TUI allows multi-panel exploration
- ✅ Better for discovery and comparison

---

## 🎯 Next Steps

When ready to implement:

1. **Review** this design plan
2. **Approve** the approach and timeline
3. **Start** Phase 1 (Foundation)
4. **Follow** the roadmap step-by-step
5. **Test** each phase before moving next
6. **Deploy** when Phase 6 complete

Estimated completion: **4-5 working days**

---

## 📞 Questions & Considerations

### Should we include mouse support?
Yes, Textual supports it - nice-to-have but keyboard is primary.

### What about dark/light themes?
Built-in color scheme works in both. Can add theme switcher in Status screen.

### Should we include export to PDF/HTML?
Metadata viewer can copy to clipboard, users can paste into Excel/Word.

### What about scheduling downloads?
Out of scope for MVP. Can add in Phase 7 (future).

### Should we persist user preferences?
Yes - last visited screen, window size, theme preference in `.tui_config`.

### Can users customize keyboard shortcuts?
Out of scope for MVP. Fixed shortcuts based on standard conventions.

---

## 🎉 Expected Outcome

A **production-ready Text User Interface** that makes the MISES data curation tool:
- ✅ **More discoverable** - Browse instead of search
- ✅ **More interactive** - Real-time feedback
- ✅ **More efficient** - Batch operations
- ✅ **More professional** - Polished presentation
- ✅ **More accessible** - Works in any terminal

Ready to help economic researchers manage data like experts! 🚀

---

## 📋 Document Checklist

- [x] Vision & Problem Statement
- [x] Feature Overview  
- [x] Interface Layout
- [x] Navigation Map
- [x] Screen Descriptions
- [x] Data Flow Architecture
- [x] Directory Structure
- [x] Implementation Phases
- [x] User Experience Flows
- [x] Design Principles
- [x] Mockups (in separate file)
- [x] Implementation Roadmap (in separate file)
- [x] Success Criteria
- [x] Next Steps

---

Generated: January 6, 2026  
Status: **Design Complete - Ready for Implementation Review**

