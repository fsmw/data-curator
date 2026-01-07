# TUI Design - Visual Overview & Quick Reference

## 🎨 Main Screen Layout

```
┌────────────────────────────────────────────────────────────────┐
│ MISES Data Curation TUI                             [Q:Quit H:Help] │
├──────────────────┬──────────────────────────────────────────────┤
│   NAVIGATION     │ MAIN CONTENT AREA                            │
│ ┌──────────────┐ │                                              │
│ │ 📂 Local (1) │ │  ┌─────────────────────────────────────────┐│
│ │ 📥 Avail (2) │ │  │ Current Screen Content                  ││
│ │ 🔍 Search(3) │ │  │                                          ││
│ │ ⬇️ Dnld (4)   │ │  │ [Dynamic based on selected menu item]  ││
│ │ 📊 Status(5) │ │  │                                          ││
│ │ ℹ️ Help (6)   │ │  │                                          ││
│ └──────────────┘ │  └─────────────────────────────────────────┘│
│                  │                                              │
│ Active: Local    │  Keyboard Hint Area                          │
└──────────────────┴──────────────────────────────────────────────┘
```

---

## 📊 Screen Map & Flow

```
                    ┌─────────────┐
                    │   START     │
                    │   Status    │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
    ┌───▼──┐         ┌────▼────┐      ┌─────▼────┐
    │Local │         │Available │     │  Search  │
    └───┬──┘         └────┬────┘      └─────┬────┘
        │                 │                 │
        │            ┌────▼────┐            │
        └───────────►│ Download │◄──────────┘
                     └────┬────┘
                          │
                     ┌────▼────┐
                     │Progress  │
                     └──────────┘
                          │
                    ┌─────▼─────┐
                    │ Success!  │
                    └───────────┘
```

---

## 🎯 Feature Comparison Matrix

| Feature | CLI | TUI |
|---------|-----|-----|
| Search Indicators | ✓ Sequential | ✓ Interactive |
| Browse Data | ✓ List only | ✓ Tree view |
| View Metadata | ✗ File editor | ✓ Built-in viewer |
| Download | ✓ One at time | ✓ Batch queue |
| Progress | ✓ Text logs | ✓ Visual bars |
| Parameters | ✓ Manual entry | ✓ Validated form |
| Metadata Copy | ✗ N/A | ✓ Clipboard |
| Dataset Compare | ✗ N/A | ✓ Side-by-side |
| Theme | N/A | ✓ Color scheme |

---

## 🎨 Visual Design System

### Color Palette
```
Primary Colors:
  Cyan    (#00D7FF) - Headers, highlights
  Green   (#00FF00) - Success, downloaded
  Blue    (#0087FF) - Available, info
  Yellow  (#FFFF00) - Pending, awaiting
  Red     (#FF0000) - Error, failed
  Orange  (#FF8700) - Warning

Neutral:
  Black   (#000000) - Background
  White   (#FFFFFF) - Text
  Gray    (#808080) - Secondary
```

### Icon Set
```
📂  Folder / Topic
📊  Dataset / Indicator
🌐  Source / Online
📥  Input / Download
⬇️  Download action
🔍  Search / Find
📝  Metadata / Notes
🧹  Clean / Process
✓   Success / Confirmed
✗   Failed / Denied
⚠️  Warning
ℹ️  Information
```

---

## 📱 Responsive Behavior

### Extra Small (80×24)
```
┌────────────────────────────┐
│ TUI [Q:Quit]               │
├────────────────────────────┤
│ MENU            │ CONTENT  │
├────────────────────────────┤
│ Status line here           │
└────────────────────────────┘
```

### Small (120×30)
```
┌──────────────────────────────────────────┐
│ MISES TUI                    [Q:Quit]    │
├──────────────┬──────────────────────────┤
│ NAVIGATION   │ MAIN                     │
├──────────────┼──────────────────────────┤
│              │ DETAILS                  │
└──────────────┴──────────────────────────┘
```

### Large (200×50+)
```
┌─────────────────────────────────────────────────────┐
│ MISES Data Curation TUI              [Q:Quit H:Help]│
├──────────────┬─────────────────┬────────────────────┤
│ NAVIGATION   │ MAIN CONTENT    │ DETAILS PANEL      │
│              │                 │                    │
│              │                 │                    │
├──────────────┼─────────────────┼────────────────────┤
│ Recent Activity               │ Quick Help        │
└──────────────┴─────────────────┴────────────────────┘
```

---

## ⌨️ Keyboard Shortcut Reference

### Global Shortcuts
```
Q           Quit application
H           Help screen
Enter       Select/confirm
Esc         Back/cancel
Tab         Next field
Shift+Tab   Previous field
Space       Toggle checkbox
```

### Navigation Shortcuts (any screen)
```
1           Browse Local Data
2           Browse Available Data
3           Search Indicators
4           Download Manager
5           Status Dashboard
6           Help Screen
```

### Screen Shortcuts (context-dependent)
```
D           Download / Delete
M           Metadata / More info
V           View / View Details
E           Export
C           Copy / Clear
S           Save / Search
P           Preview
A           Add to queue
R           Refresh / Re-import
```

### Text Input Shortcuts (search box)
```
/           Open search from any screen
Ctrl+A      Select all text
Ctrl+U      Clear line
Ctrl+H      Backspace
Arrow keys  Move cursor
```

---

## 🔄 Data Flow Diagram

### Local Data Flow
```
File System (02_Datasets_Limpios/)
    ↓
Local Data Manager [scan folders]
    ↓
Topic Cache (in-memory)
    ↓
TUI Browse Local Screen
    ↓
User selects topic → Expand tree
    ↓
User selects dataset → Show details
    ↓
User presses M → Load metadata
    ↓
Metadata Viewer Modal [render markdown]
```

### Available Data Flow
```
indicators.yaml
    ↓
API Data Manager [parse YAML]
    ↓
Indicator Cache (6h TTL)
    ↓
TUI Browse Available Screen
    ↓
User selects source → Filter indicators
    ↓
User selects indicator → Show details
    ↓
User presses D → Jump to Download
```

### Download Flow
```
User configures download
    ↓
Download Coordinator [build spec]
    ↓
DataIngestionManager [existing code]
    ↓
Ingest Step [API call]
    ↓
Clean Step [standardize]
    ↓
Document Step [generate metadata]
    ↓
Progress screen shows 3 steps
    ↓
On completion: Return to Browse Local
```

---

## 📈 User Journey Maps

### Journey 1: First-Time User (New to Tool)
```
START
  │
  ├─ App opens → Status Dashboard
  │             (Shows overview of all data available)
  │
  ├─ User feels overwhelmed, presses H
  │ └─ Help screen explains features
  │
  ├─ Closes help, clicks "Browse Available"
  │
  ├─ Sees 5 sources, clicks OECD
  │
  ├─ Sees 7 indicators, clicks "average_wage_usd"
  │
  ├─ Reads description, clicks D for Download
  │
  ├─ Download form appears (pre-filled with defaults)
  │
  ├─ User clicks Download
  │
  ├─ Watches progress bar complete 3 steps
  │
  ├─ Success message appears
  │
  └─ Returns to Browse Local to see new dataset
       [Total time: ~5 minutes]
```

### Journey 2: Power User (Batch Operations)
```
START
  │
  ├─ App opens → Last screen (Search)
  │
  ├─ Types "wage" in search box
  │
  ├─ 7 results appear
  │
  ├─ Selects result, presses +
  │ └─ Added to queue (shows notification)
  │
  ├─ Selects another, presses +
  │
  ├─ Selects third, presses +
  │
  ├─ Navigates to Download Manager (presses 4)
  │
  ├─ Queue shows 3 items ready
  │
  ├─ Clicks Download All
  │
  ├─ Background mode: Can continue browsing while downloading
  │
  ├─ Checks Status screen → See downloads in progress
  │
  └─ All 3 complete, appears in Browse Local
       [Total time: ~2 minutes]
```

### Journey 3: Researcher (Data Review)
```
START
  │
  ├─ App opens → Browse Local (last screen)
  │
  ├─ Expands "salarios_reales" topic
  │
  ├─ Sees 4 datasets listed
  │
  ├─ Selects first dataset
  │ └─ Details panel shows: source, years, coverage, size
  │
  ├─ Presses M for metadata
  │
  ├─ Modal opens with full documentation
  │
  ├─ Reads sections: Variables, Coverage, Transformations, Warnings
  │
  ├─ Sees warning about missing 2023 data for Mexico
  │
  ├─ Copies metadata to clipboard (presses C)
  │
  ├─ Closes modal (presses Esc)
  │
  ├─ Selects second dataset, repeats
  │
  ├─ Presses E to export both to Excel
  │
  └─ Opens Excel, pastes cleaned data
       [Total time: ~10 minutes for 2 datasets]
```

---

## 🎯 Task Flow Diagrams

### Task: Download GINI from World Bank
```
1. Search Screen [press 3]
   │
   └─ Type "gini" → Results: 2 matches
      │
      ├─ wage_inequality_gini (OECD)
      └─ gini_coefficient (World Bank) ← Select
         │
         └─ Press D → Download Manager
            │
            └─ Form fills with World Bank params
               │
               ├─ Source: World Bank [auto]
               ├─ Indicator: SI.POV.GINI [auto]
               ├─ Topic: [libertad_economica ▼] select
               ├─ Countries: [All selected]
               ├─ Years: [2010-2024]
               │
               └─ Press Download
                  │
                  └─ Progress 3 steps
                     │
                     └─ Success → Browse Local shows new dataset
```

### Task: Compare 3 Wage Datasets
```
1. Browse Local [press 1]
   │
   ├─ Expand "salarios_reales" topic → 5 datasets
   │
   ├─ Select dataset 1 → M for metadata
   │  │
   │  └─ Read & review
   │
   ├─ Esc to close → Select dataset 2 → M
   │  │
   │  └─ Compare with dataset 1
   │
   ├─ Esc to close → Select dataset 3 → M
   │  │
   │  └─ Compare with datasets 1 & 2
   │
   └─ Make informed decision on which to use
      for analysis
```

---

## 💾 Data Organization

### Local Data Structure (What TUI sees)
```
02_Datasets_Limpios/
├── salarios_reales/
│   ├── salarios_reales_oecd_latam_2010_2023.csv
│   ├── salarios_reales_oecd_latam_2010_2024.csv
│   ├── salarios_reales_worldbank_latam_2010_2024.csv
│   └── salarios_reales_eclac_latam_2010_2024.csv
│
├── informalidad_laboral/
│   ├── informalidad_latam_ilostat_2010_2024.csv
│   └── informalidad_latam_eclac_2010_2024.csv
│
├── presion_fiscal/
│   ├── presion_fiscal_oecd_latam_2010_2023.csv
│   └── presion_fiscal_eclac_latam_2010_2024.csv
│
└── libertad_economica/
    ├── libertad_economica_worldbank_latam_2010_2024.csv
    ├── libertad_economica_imf_latam_2010_2024.csv
    └── [... more]
```

### Available Data Structure (indicators.yaml)
```
indicators.yaml
├── indicator_name:
│   ├── source: ilostat | oecd | imf | worldbank | eclac
│   ├── [source]_code: "CODE"
│   ├── description: "..."
│   ├── coverage: "Global | OECD | LAC"
│   ├── years: "2010-2024"
│   └── countries: "ARG,BRA,CHL,COL,MEX,PER,URY"
│
└── [20+ total indicators]
```

---

## 🎛️ Form Design Examples

### Download Form (Dynamic)
```
Source: [OECD ▼]
├─ ILOSTAT
├─ OECD (selected)
├─ IMF
├─ World Bank
└─ ECLAC

If OECD selected:
  Dataset: [ALFS ▼]
  Indicator: [average_wage_usd ▼]

If ILOSTAT selected:
  Indicator: [unemployment_rate ▼]

If IMF selected:
  Database: [WEO ▼]
  Indicator: [NGDP_RPCH ▼]

If World Bank selected:
  Indicator: [SI.POV.GINI ▼]

If ECLAC selected:
  Table: [TFP ▼]

Topic: [salarios_reales ▼]
Coverage: [latam ▼]
Countries: [All selected] ☑
  ☐ Argentina ☐ Brazil ☐ Chile ...
Years: From [2010] To [2024]
```

---

## 🌟 Special Features

### Metadata Viewer Features
```
┌─ Variable Rendering
│  ├─ Code blocks with syntax highlighting
│  ├─ Tables with proper alignment
│  ├─ Bullet lists and nested lists
│  └─ Bold/italic/underline emphasis
│
├─ Copy Features
│  ├─ Copy all metadata to clipboard
│  ├─ Copy individual sections
│  └─ Export as markdown file
│
└─ Navigation
   ├─ Scroll with arrow keys
   ├─ Page up/down
   ├─ Jump to sections
   └─ Search within metadata
```

### Search Features
```
┌─ Input Features
│  ├─ Fuzzy matching ("wag" → finds "wage")
│  ├─ Case insensitive search
│  ├─ Real-time results update
│  └─ Search history (↑↓ in input)
│
├─ Filter Features
│  ├─ By Topic (multi-select)
│  ├─ By Source (multi-select)
│  ├─ By Status (Downloaded/Not/All)
│  └─ Save search queries
│
└─ Result Features
   ├─ Shows match count
   ├─ Highlights matching terms
   ├─ Shows quick metadata
   └─ Action buttons on hover
```

---

## 📊 Statistics & Counters

### Status Dashboard Shows
```
📁 Directories:
   01_Raw_Data_Bank: 12 files (245 MB)
   02_Datasets_Limpios: 4 files (89 MB)
   03_Metadata_y_Notas: 3 files (45 KB)
   04_Graficos_Asociados: 0 files

📊 Data:
   Total Topics: 4
   Downloaded Datasets: 4
   Available Indicators: 20+
   Coverage: 20% (4/20)

🌐 Sources:
   ILOSTAT: 3 indicators, 0 downloaded
   OECD: 7 indicators, 3 downloaded
   IMF: 2 indicators, 0 downloaded
   World Bank: 4 indicators, 1 downloaded
   ECLAC: 4 indicators, 0 downloaded

🔑 Configuration:
   OpenRouter API: ✓ Configured
   (No other API keys needed)
```

---

## 🎓 Help System Structure

### Built-in Help (Press H)
```
Main Help Screen
├─ Navigation Guide
│  ├─ How to access each screen
│  ├─ Menu keyboard shortcuts
│  └─ Screen selection (1-6)
│
├─ Screen Help
│  ├─ Browse Local: How to expand topics, view metadata
│  ├─ Browse Available: How to filter by source
│  ├─ Search: How to use filters and search
│  ├─ Download: How to fill form, validate
│  ├─ Status: What each stat means
│  └─ Help: This screen
│
├─ Common Tasks
│  ├─ How to download a dataset
│  ├─ How to view metadata
│  ├─ How to search for data
│  ├─ How to compare datasets
│  └─ How to export data
│
└─ Troubleshooting
   ├─ App not starting? Try...
   ├─ Screen not loading? Try...
   ├─ Download failed? Try...
   └─ Contact support: [email]
```

---

## ✅ Implementation Checklist

### Phase 1: Foundation
- [ ] Textual app class created
- [ ] Theme colors defined
- [ ] Base screen class
- [ ] Sidebar navigation

### Phase 2: Browsing
- [ ] Browse Local screen + tree view
- [ ] Browse Available screen + source cards
- [ ] Search screen + fuzzy matching

### Phase 3: Management
- [ ] Download Manager form
- [ ] Progress Monitor
- [ ] Status Dashboard

### Phase 4: Modals
- [ ] Metadata Viewer modal
- [ ] Confirmation dialogs
- [ ] Input dialogs

### Phase 5: Data Layer
- [ ] Local Data Manager
- [ ] API Data Manager
- [ ] Download Coordinator
- [ ] Cache system

### Phase 6: Integration
- [ ] Navigation system
- [ ] Event binding
- [ ] Testing
- [ ] Documentation

---

## 🚀 Launch & Usage

### Starting the TUI
```bash
# Method 1: Direct
python -m src.tui

# Method 2: Via CLI alias
curate tui

# Method 3: From package
from src.tui import MisesApp
app = MisesApp()
app.run()
```

### First Run
```
1. App opens in Status screen
2. Shows overview of all data
3. Sidebar ready for navigation
4. Help available on H key
5. Can start exploring immediately
```

---

## 📚 Document Navigation

This is the **Visual Overview** document. Related documents:

1. **TUI_DESIGN_SUMMARY.md** - Executive summary
2. **TUI_DESIGN_PLAN.md** - Comprehensive design (9 detailed screens)
3. **TUI_MOCKUPS.md** - ASCII mockups & flows
4. **TUI_IMPLEMENTATION_ROADMAP.md** - Step-by-step implementation

---

**Status**: ✅ Design Complete - Ready for Implementation Review

**Complexity**: Medium (24-32 hours of development)

**Impact**: Transforms CLI tool into interactive explorer

