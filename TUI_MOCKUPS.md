# TUI Mockup Wireframes & Flow Diagrams

## 🗺️ Navigation Map

```
                          ┌─────────────────────┐
                          │   MAIN APP START    │
                          │  (Status Dashboard) │
                          └──────────┬──────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
         ┌───────▼────────┐  ┌──────▼────────┐  ┌──────▼─────────┐
         │ Browse Local   │  │ Browse Avail  │  │     Search     │
         │                │  │                │  │                │
         │ Topics List ─┐ │  │ Sources List─┐ │  │ Keyword Box ─┐ │
         │ ↓ Expand     │ │  │ ↓ Expand     │ │  │ + Filters    │ │
         │ Datasets ────┼─┼→ │ Indicators ──┼─┼→ │ Results List ─┤ │
         │ ↓ Select     │ │  │ ↓ Select     │ │  │ ↓ Select     │ │
         │ Metadata ────┴─┴→ │ Details Panel┴─┴→ │ [Download]   ─┤ │
         └─────────────────┘  └──────────────┘  └────────────────┘
                 │                   │                   │
                 │                   │                   │
         ┌───────┴─────┐      ┌──────┴──────┐      ┌────┴─────────┐
         │[Delete]     │      │[Download]   │      │[Download]    │
         │[Export]     │      │[Details]    │      │[View Details]│
         │[View Meta]  │      │[Queue]      │      │[Add Queue]   │
         └─────────────┘      └─────────────┘      └───────┬──────┘
                                                           │
                                      ┌────────────────────┴─────────────┐
                                      │                                  │
                                   ┌──▼────────────────┐      ┌────────▼──┐
                                   │ Download Manager  │      │  Progress │
                                   │                  │      │   Monitor │
                                   │ [Form]           │      │           │
                                   │ [Parameters]     │      │[Progress] │
                                   │ [Country Select] │──┐   │[Status]   │
                                   │ [Preview]        │  │   │[Logs]     │
                                   │ [DOWNLOAD BTN]   │──┤   │[Cancel]   │
                                   └──────────────────┘  │   └───────────┘
                                                         │
                                     ┌───────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │   Data Saved!   │
                            │ Return to Browse│
                            └─────────────────┘
```

---

## 🎯 Detail View Flows

### Flow 1: Browse Local Data → View Metadata

```
Browse Local Screen
│
├─ Topics Level
│  └─ [salarios_reales] (5 datasets)
│     [informalidad_laboral] (3 datasets)
│     [presion_fiscal] (3 datasets)
│     [libertad_economica] (9 datasets)
│
├─ Press ENTER on topic
│  └─ Topic Expands
│     ├─ salarios_reales_oecd_latam_2010_2023.csv
│     ├─ salarios_reales_wb_latam_2010_2024.csv
│     ├─ salarios_reales_worldbank_latam_2010_2024.csv
│     └─ [more...]
│
├─ Press M on dataset
│  └─ Metadata Modal Opens
│     ├─ Description
│     ├─ Variables
│     ├─ Coverage
│     ├─ Transformations Applied
│     ├─ Warnings & Notes
│     └─ [Scroll for more]
│
└─ ESC to Close Modal
   └─ Back to Datasets List
```

### Flow 2: Search → Filter → Download

```
Search Screen
│
├─ Type "wage" in search box
│  └─ Results filtered to 7 matches
│     ├─ wage_inequality_gini (OECD, salarios_reales, ✓ DL)
│     ├─ average_wage_usd (OECD, salarios_reales, ✓ DL)
│     ├─ minimum_wage (OECD, salarios_reales, ✗)
│     ├─ real_wage_index (OECD, salarios_reales, ✓ DL)
│     └─ [...]
│
├─ Press SPACE to add filter
│  └─ Select "Source: OECD only"
│     └─ Results narrow to 4 matches
│
├─ Press Enter on "minimum_wage"
│  └─ Details show:
│     ├─ Source: OECD
│     ├─ Dataset: LAB_STAT
│     ├─ Indicator: MIN_WAGE
│     ├─ Coverage: OECD
│     ├─ Years: 2010-2024
│     ├─ Status: Not Downloaded
│     └─ [D] Download
│
├─ Press D
│  └─ Download Form Opens
│     ├─ Topic: [salarios_reales] (auto-detected)
│     ├─ Countries: [All selected]
│     ├─ Years: 2010-2024
│     ├─ [PREVIEW] → Shows what will download
│     └─ [DOWNLOAD]
│
└─ Download Started
   └─ Progress monitor shows 3 steps
      ├─ Step 1: Ingest (downloading from API)
      ├─ Step 2: Clean (standardizing data)
      └─ Step 3: Document (generating metadata)
```

---

## 📊 Screen Component Breakdown

### Browse Local Screen Components

```
┌─ Header
│  └─ Title: "MISES Data Curation - Browse Local Data"
│
├─ Sidebar (Left 20%)
│  ├─ Navigation Menu
│  │  ├─ [▶] 📂 Browse Local (active)
│  │  ├─[ ] 📥 Browse Available
│  │  ├─[ ] 🔍 Search
│  │  ├─[ ] ⬇️  Download
│  │  ├─[ ] 📊 Status
│  │  └─[ ] ℹ️ Help
│  │
│  └─ Footer
│     └─ [Active: Browse Local]
│
├─ Main Content (Left 40%)
│  ├─ Topics Tree
│  │  ├─ 📂 salarios_reales (5) [EXPANDED]
│  │  │  ├─ 📊 dataset1.csv
│  │  │  ├─ 📊 dataset2.csv
│  │  │  └─ 📊 ...
│  │  ├─ 📂 informalidad_laboral (3)
│  │  ├─ 📂 presion_fiscal (3)
│  │  └─ 📂 libertad_economica (9)
│  │
│  └─ Scroll Indicator: ↕ if needed
│
├─ Details Panel (Right 40%)
│  ├─ Dataset Details
│  │  ├─ Name: salarios_reales_oecd_latam_2010_2023.csv
│  │  ├─ Location: 02_Datasets_Limpios/salarios_reales/
│  │  ├─ Records: 127
│  │  ├─ Source: OECD
│  │  ├─ Coverage: latam
│  │  ├─ Years: 2010-2023
│  │  ├─ Updated: 2024-12-15
│  │  └─ Metadata: ✓ Available
│  │
│  └─ Action Buttons
│     ├─ [M] Metadata
│     ├─ [D] Delete
│     ├─ [E] Export
│     └─ [R] Reimport
│
└─ Footer Status Bar
   └─ [↑↓] Navigate | [M] View Metadata | [D] Delete | [E] Export
```

### Search Screen Components

```
┌─ Header
│  └─ Title: "MISES Data Curation - Search"
│
├─ Filter Panel (Top)
│  ├─ 🔍 Search Box
│  │  └─ "wage" (with cursor)
│  │
│  ├─ Filter Controls (Row)
│  │  ├─ 📂 Topic: [All Topics ▼]
│  │  ├─ 🌐 Source: [All Sources ▼]
│  │  └─ ✓ Status: [All ▼]
│  │
│  └─ [APPLY FILTERS] button
│
├─ Results Panel
│  ├─ Results Header: "7 matches for 'wage'"
│  │
│  ├─ Result Items (scrollable)
│  │  ├─ 📊 wage_inequality_gini
│  │  │  ├─ Topic: salarios_reales
│  │  │  ├─ Source: OECD
│  │  │  └─ Status: ✓ Downloaded (2024-12-15)
│  │  │
│  │  ├─ 📊 average_wage_usd (current selection ← highlight)
│  │  │  ├─ Topic: salarios_reales
│  │  │  ├─ Source: OECD
│  │  │  └─ Status: ✓ Downloaded (2024-12-15)
│  │  │
│  │  ├─ 📊 minimum_wage
│  │  │  ├─ Topic: salarios_reales
│  │  │  ├─ Source: OECD
│  │  │  └─ Status: ✗ Not Downloaded
│  │  │
│  │  └─ [MORE...]
│  │
│  └─ Quick Details (for selected item)
│     ├─ Description: "Average nominal wage in USD..."
│     ├─ Parameters: Dataset=ELS_EARN, Indicator=AVGRNL
│     └─ [D] Download | [A] Add to Queue | [V] View Details
│
└─ Footer
   └─ [Type] Search | [↑↓] Results | [Enter] View | [D] Download
```

### Download Manager Components

```
┌─ Header
│  └─ Title: "MISES Data Curation - Download"
│
├─ Form Panel (left 50%)
│  ├─ Source Selection
│  │  └─ Source: [OECD ▼]
│  │           ├─ ILOSTAT
│  │           ├─ OECD (← selected)
│  │           ├─ IMF
│  │           ├─ World Bank
│  │           └─ ECLAC
│  │
│  ├─ Source-Specific Params
│  │  ├─ Dataset: [ALFS ▼]
│  │  ├─ Indicator: [average_wage_usd ▼]
│  │  └─ (varies by source)
│  │
│  ├─ Topic Selection
│  │  └─ Topic: [salarios_reales ▼]
│  │         ├─ salarios_reales (← selected)
│  │         ├─ informalidad_laboral
│  │         ├─ presion_fiscal
│  │         └─ libertad_economica
│  │
│  ├─ Coverage
│  │  └─ Coverage: [latam ▼]
│  │
│  ├─ Year Range
│  │  ├─ Start Year: [2010 ← 1990 ... 2024]
│  │  └─ End Year:   [2024 ← 2000 ... 2024]
│  │
│  └─ Country Selection
│     ├─ [✓] All (ARG,BRA,CHL,COL,MEX,PER,URY)
│     ├─ [ ] Argentina (ARG)
│     ├─ [ ] Brazil (BRA)
│     ├─ [ ] Chile (CHL)
│     ├─ [ ] Colombia (COL)
│     └─ [MORE...]
│
├─ Preview Panel (right 50%)
│  ├─ Download Summary
│  │  ├─ Source: OECD (average_wage_usd)
│  │  ├─ Topic: salarios_reales
│  │  ├─ Countries: 7 selected
│  │  ├─ Years: 2010-2024
│  │  └─ Expected Rows: ~127
│  │
│  ├─ Destination
│  │  ├─ Raw Data: 01_Raw_Data_Bank/OECD/
│  │  ├─ Clean Data: 02_Datasets_Limpios/salarios_reales/
│  │  └─ Metadata: 03_Metadata_y_Notas/
│  │
│  └─ Action Buttons (centered)
│     ├─ [PREVIEW]
│     ├─ [DOWNLOAD]
│     └─ [CLEAR]
│
└─ Footer
   └─ [Tab] Move | [Space] Toggle | [Enter] Download | [C] Clear
```

---

## 🔄 State Management Flow

```
App State
│
├─ Current Screen
│  ├─ browse_local
│  ├─ browse_available
│  ├─ search
│  ├─ download
│  ├─ progress
│  ├─ status
│  └─ help
│
├─ Navigation History
│  └─ [Screen A] → [Screen B] → [Screen C]
│     (allows Back/Forward)
│
├─ Session Data
│  ├─ Last Downloaded Dataset
│  ├─ Last Viewed Topic
│  ├─ Last Search Query
│  ├─ Download Queue
│  └─ Settings Preferences
│
├─ Cached Data
│  ├─ Local Datasets (refreshed on enter browse local)
│  ├─ Available Indicators (refreshed on demand)
│  ├─ API Responses (6-hour TTL)
│  └─ Metadata Cache
│
└─ Active Operations
   ├─ Current Download
   ├─ Progress %%
   ├─ Logs
   └─ Errors
```

---

## 🎨 Color Scheme & Styling

### Color Palette
```
Primary Colors:
  ├─ Header: Cyan (#00D7FF)
  ├─ Active: Green (#00FF00)
  ├─ Downloaded: Blue (#0087FF)
  ├─ Available: Yellow (#FFFF00)
  ├─ Error: Red (#FF0000)
  ├─ Warning: Orange (#FF8700)
  └─ Background: Black (#000000)

Emphasis:
  ├─ Selected Item: Reverse video or highlight box
  ├─ Links: Blue with underline
  ├─ Success: Green checkmark ✓
  ├─ Failure: Red X ✗
  └─ Neutral: White text
```

### Icons
```
📂 Folder/Topic
📊 Dataset/Indicator
🌐 Source/Online
📥 Input/Download
⬇️  Download action
🔍 Search
📝 Metadata/Notes
🧹 Clean
✓  Success
✗  Failure
⚠️  Warning
ℹ️  Information
```

---

## ⌨️ Keyboard Shortcut Reference

### Global Shortcuts (any screen)
```
Q           Quit application
H           Help screen
Tab         Next field/element
Shift+Tab   Previous field/element
Esc         Back/Close
Enter       Select/Confirm
Space       Toggle checkbox
```

### Navigation Shortcuts
```
1           Browse Local
2           Browse Available
3           Search
4           Download
5           Status
6           Help
```

### Action Shortcuts
```
D           Download / Delete
M           Metadata / More info
V           View Details
S           Save / Search
E           Export
C           Copy / Clear
R           Refresh / Reimport
P           Preview
```

### Text Input (Search)
```
/           Start search (from any screen)
Ctrl+A      Select all text
Ctrl+U      Clear line
Ctrl+H      Backspace
```

---

## 📱 Responsive Design

### Minimum Size: 80×24
```
TUI adapts to:
├─ Collapse sidebar when < 100 cols
├─ Stack panels vertically when < 120 cols
├─ Hide non-essential info when < 30 rows
└─ Show scroll indicators when content overflow
```

### Large Size: 200×50+
```
TUI adapts to:
├─ Show multi-column layouts
├─ Display rich metadata previews
├─ Show detailed progress bars
└─ Display more list items without scrolling
```

---

## 🔄 Data Refresh Logic

### Auto-Refresh Triggers
```
Enter Browse Local Screen
  └─ Check for file changes in 02_Datasets_Limpios/
     └─ If changed: Reload dataset list

Enter Search Screen
  └─ Query indicators.yaml for latest data

Enter Status Screen
  └─ Recalculate directory sizes
  └─ Check API connectivity

Every 5 minutes
  └─ Background check for file changes
```

### Manual Refresh
```
R key
  ├─ Current Screen data
  ├─ Folder/API data
  └─ Clear cache
```

---

## 🧪 Test Scenarios

### Scenario 1: First-time User
1. App opens → Status Dashboard
2. See 5 sources available, 0 datasets downloaded
3. Click "Browse Available"
4. See OECD source with 7 indicators
5. Click first indicator
6. Click "Download"
7. Form auto-fills with defaults
8. Click "Download"
9. Progress screen shows 3 steps
10. Success → Returns to status showing 1 downloaded

### Scenario 2: Power User
1. App opens → Last screen (Search)
2. Type "wage" → 7 results
3. Select first result
4. Press D for details
5. Check if already downloaded
6. If not: Add to queue
7. Move to next indicator
8. Add 3 to queue
9. Go to Download Manager
10. Queue shows 3 items
11. Click "Download All"
12. Batch download starts
13. Can continue browsing while downloading

### Scenario 3: Data Review
1. Open Browse Local
2. Expand "salarios_reales" topic
3. Select "salarios_reales_oecd_*"
4. Press M for metadata
5. Metadata modal shows full details
6. Scroll through transformations
7. See warnings about missing values
8. Press C to copy metadata to clipboard
9. Close modal with Esc
10. Continue browsing other datasets

---

## ✅ Implementation Checklist

- [ ] Phase 1: Core TUI Framework
  - [ ] Textual app class
  - [ ] Screen manager
  - [ ] Sidebar navigation
  
- [ ] Phase 2: Data Browsing
  - [ ] Browse Local screen
  - [ ] Browse Available screen
  - [ ] Search screen
  
- [ ] Phase 3: Data Management
  - [ ] Download Manager screen
  - [ ] Progress Monitor
  - [ ] Status Dashboard
  
- [ ] Phase 4: Modals & Dialogs
  - [ ] Metadata Viewer modal
  - [ ] Confirmation dialogs
  - [ ] Input dialogs
  
- [ ] Phase 5: Data Layer
  - [ ] Local Data Manager
  - [ ] API Data Manager
  - [ ] Download Coordinator
  
- [ ] Testing
  - [ ] All screens work
  - [ ] Keyboard navigation
  - [ ] Data accuracy
  - [ ] Error handling

---

## 📈 Success Metrics

✅ **Usability**
- New user completes first download in < 3 minutes
- Power user can queue 5 downloads in < 2 minutes
- Help available for every screen

✅ **Performance**
- App startup: < 500ms
- Screen changes: < 100ms
- Search results: < 500ms
- Download initiation: immediate

✅ **Reliability**
- No crashes on invalid input
- Graceful error messages
- All operations logged
- Recovery on close/reopen

