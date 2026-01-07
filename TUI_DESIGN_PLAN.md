# Textual TUI Design Plan

## 🎯 Project Objectives

Build an interactive Text User Interface for the economic data curation tool that enables:
1. **Browse Local Data** - View downloaded datasets and their metadata
2. **Explore Available Data** - Discover indicators across 5 sources
3. **Search & Filter** - Find indicators by keyword, source, or topic
4. **Initiate Downloads** - Launch data downloads from TUI
5. **View Metadata** - Display dataset documentation and cleaning history

---

## 📐 Architecture Overview

### Tech Stack
- **Framework**: Textual (rich TUI framework)
- **Display**: Rich library for formatting
- **Data**: Current JSON/CSV/YAML configuration
- **Python Version**: 3.14.2 (matches project)

### Key Dependencies
```
textual >= 0.50.0
rich >= 13.0.0
pandas >= 2.3.0
pyyaml >= 6.0
```

---

## 🏗️ TUI Structure

### Main Application Layout

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📊 MISES Data Curation Tool v1.0                                   [⚙️ Q:Quit] ║
╠════════════════════╦═════════════════════════════════════════════════════════╣
║  NAVIGATION        ║  MAIN CONTENT AREA                                      ║
║  ━━━━━━━━━━━━━━━━━║                                                         ║
║  📂 Browse Local   ║                                                         ║
║  📥 Browse Avail   ║                                                         ║
║  🔍 Search        ║  [Content dynamically loads here]                       ║
║  ⬇️  Download      ║                                                         ║
║  📊 Status         ║                                                         ║
║  ℹ️ Help           ║                                                         ║
║  ━━━━━━━━━━━━━━━━━║                                                         ║
║                    ║                                                         ║
║  [Active: Browse]  ║                                                         ║
╠════════════════════╩═════════════════════════════════════════════════════════╣
║ Status: Ready | Topics: 4 | Datasets: 4 | Sources: 5 | Indicators: 20+      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Screen 1: Browse Local Data

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📊 MISES Data Curation - Browse Local Data                       [Q:Quit H:Help]║
╠════════════════════╦═════════════════════════════════════════════════════════╣
║  NAVIGATION        ║  TOPICS (Select one)                                    ║
║  ━━━━━━━━━━━━━━━━━║                                                         ║
║ ▶ 📂 Browse Local  ║  📂 salarios_reales (5 datasets)                       ║
║  📥 Browse Avail   ║  📂 informalidad_laboral (3 datasets)                  ║
║  🔍 Search        ║  📂 presion_fiscal (3 datasets)                         ║
║  ⬇️  Download      ║  📂 libertad_economica (9 datasets)                    ║
║  📊 Status         ║                                                         ║
║  ℹ️ Help           ║  ↓ Press ENTER to expand, ESC to collapse             ║
║                    ║                                                         ║
╠════════════════════╬═════════════════════════════════════════════════════════╣
║                    ║  PREVIEW PANEL                                          ║
║                    ║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                    ║                                                         ║
║                    ║  [Select a topic to view its datasets]                 ║
║                    ║                                                         ║
╠════════════════════╩═════════════════════════════════════════════════════════╣
║ [↑↓] Navigate | [Enter] Expand | [D] Delete | [V] View Metadata              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Screen 2: Browse Local Data - Topic Expanded

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📊 MISES Data Curation - Browse Local Data > salarios_reales                 ║
╠════════════════════╦═════════════════════════════════════════════════════════╣
║  NAVIGATION        ║  DATASETS                                               ║
║  ━━━━━━━━━━━━━━━━━║                                                         ║
║ ▶ 📂 Browse Local  ║  ▼ 📂 salarios_reales                                  ║
║  📥 Browse Avail   ║    ├─ 📊 salarios_reales_oecd_latam_2010_2023.csv    ║
║  🔍 Search        ║    ├─ 📊 salarios_reales_oecd_latam_2010_2024.csv    ║
║  ⬇️  Download      ║    ├─ 📊 salarios_reales_worldbank_latam_2010_2024   ║
║  📊 Status         ║    └─ 📊 [MORE...]                                   ║
║  ℹ️ Help           ║                                                         ║
║                    ║                                                         ║
╠════════════════════╬═════════════════════════════════════════════════════════╣
║                    ║  DATASET DETAILS: salarios_reales_oecd_latam_*        ║
║                    ║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                    ║  📁 Location: 02_Datasets_Limpios/salarios_reales/    ║
║                    ║  📊 Records: 127                                       ║
║                    ║  🔗 Source: OECD                                       ║
║                    ║  📍 Coverage: latam (ARG,BRA,CHL,COL,MEX,PER,URY)    ║
║                    ║  📅 Years: 2010-2023                                   ║
║                    ║  ✏️  Last Updated: 2024-12-15                         ║
║                    ║  📝 Metadata: ✓ Available                              ║
║                    ║                                                         ║
╠════════════════════╩═════════════════════════════════════════════════════════╣
║ [↑↓] Navigate | [M] View Metadata | [D] Delete | [E] Export | [R] Reimport   ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Screen 3: View Metadata (Modal)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📝 METADATA: salarios_reales_oecd_latam_2010_2023.csv                        ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  📊 VARIABLES                                                                 ║
║  ─────────────────────────────────────────────────────────────────────────── ║
║  • country (string) - ISO 3166-1 alpha-3 country code                       ║
║  • year (integer) - Year of observation                                     ║
║  • value (float) - Average nominal wage in nominal USD                      ║
║  • indicator (string) - OECD indicator code                                 ║
║                                                                               ║
║  🌍 COVERAGE                                                                  ║
║  ─────────────────────────────────────────────────────────────────────────── ║
║  Countries: Argentina, Brazil, Chile, Colombia, Mexico, Peru, Uruguay       ║
║  Time Period: 2010-2023 (14 years)                                          ║
║  Data Points: 127 total                                                     ║
║                                                                               ║
║  🔧 TRANSFORMATIONS APPLIED                                                   ║
║  ─────────────────────────────────────────────────────────────────────────── ║
║  ✓ Removed 2 empty rows                                                     ║
║  ✓ Standardized country codes to ISO 3166-1 alpha-3                        ║
║  ✓ Normalized date format to YYYY                                           ║
║  ✓ Removed 1 column with 100% missing values                               ║
║                                                                               ║
║  ⚠️  WARNINGS & NOTES                                                         ║
║  ─────────────────────────────────────────────────────────────────────────── ║
║  • Mexico: Missing data for 2023                                            ║
║  • Peru: Only 8 years of data available (2015-2023)                        ║
║  • Values in nominal USD; consider inflation adjustment                    ║
║                                                                               ║
║  [Scroll down for more ↓]                                                    ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║ [↑↓] Scroll | [C] Copy | [D] Download CSV | [P] Print | [Q/ESC] Close       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Screen 4: Browse Available Data

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📊 MISES Data Curation - Browse Available Data                 [Q:Quit H:Help]║
╠════════════════════╦═════════════════════════════════════════════════════════╣
║  NAVIGATION        ║  SOURCES (Select one)                                   ║
║  ━━━━━━━━━━━━━━━━━║                                                         ║
║  📂 Browse Local   ║  🌐 ILOSTAT (3 indicators)                             ║
║ ▶ 📥 Browse Avail  ║  🌐 OECD (7 indicators)                                ║
║  🔍 Search        ║  🌐 IMF (2 indicators)                                  ║
║  ⬇️  Download      ║  🌐 World Bank (4 indicators)                          ║
║  📊 Status         ║  🌐 ECLAC (4 indicators)                               ║
║  ℹ️ Help           ║                                                         ║
║                    ║  ↓ Press ENTER to view source details                  ║
║                    ║                                                         ║
╠════════════════════╬═════════════════════════════════════════════════════════╣
║                    ║  SOURCE DETAILS: OECD                                   ║
║                    ║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                    ║                                                         ║
║                    ║  Organisation for Economic Co-operation &              ║
║                    ║  Development (OECD)                                    ║
║                    ║                                                         ║
║                    ║  🌍 Coverage: 38+ member countries                     ║
║                    ║  📡 API Type: SDMX-JSON REST                           ║
║                    ║  📊 Indicators: 7                                      ║
║                    ║  🔗 Website: https://stats.oecd.org                   ║
║                    ║                                                         ║
║                    ║  Available Topics:                                     ║
║                    ║  • salarios_reales (4 indicators)                      ║
║                    ║  • presion_fiscal (2 indicators)                       ║
║                    ║  • libertad_economica (1 indicator)                   ║
║                    ║                                                         ║
╠════════════════════╩═════════════════════════════════════════════════════════╣
║ [↑↓] Navigate | [Enter] View Indicators | [D] Download | [I] Info            ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Screen 5: Browse Available Data - Indicators

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📊 MISES Data Curation - Available Data > OECD > Indicators    [Q:Quit H:Help]║
╠════════════════════╦═════════════════════════════════════════════════════════╣
║  NAVIGATION        ║  INDICATORS (7 total)                                   ║
║  ━━━━━━━━━━━━━━━━━║                                                         ║
║  📂 Browse Local   ║  📊 real_wage_index                                    ║
║  📥 Browse Avail   ║  📊 average_wage_usd                                   ║
║  🔍 Search        ║  📊 minimum_wage                                        ║
║  ⬇️  Download      ║  📊 tax_revenue_gdp                                    ║
║  📊 Status         ║  📊 income_tax_rate                                    ║
║  ℹ️ Help           ║  📊 labor_productivity                                 ║
║                    ║  📊 wage_inequality_gini                               ║
║                    ║                                                         ║
╠════════════════════╬═════════════════════════════════════════════════════════╣
║                    ║  INDICATOR DETAILS: average_wage_usd                    ║
║                    ║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                    ║                                                         ║
║                    ║  📋 Description:                                        ║
║                    ║  Average nominal wage in USD across OECD countries      ║
║                    ║  and selected partners.                                 ║
║                    ║                                                         ║
║                    ║  🔧 Parameters:                                         ║
║                    ║  • Dataset: ELS_EARN                                    ║
║                    ║  • Indicator: AVGRNL                                    ║
║                    ║  • Coverage: OECD + partners                            ║
║                    ║  • Years Available: 2010-2024                           ║
║                    ║  • Countries: ARG,BRA,CHL,MEX,COL,URY                 ║
║                    ║                                                         ║
║                    ║  📥 Status: Not downloaded                              ║
║                    ║  [D] Download to salarios_reales                      ║
║                    ║                                                         ║
╠════════════════════╩═════════════════════════════════════════════════════════╣
║ [↑↓] Navigate | [Enter] Details | [D] Download | [A] Add to Queue | [C] Copy ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Screen 6: Search Indicators

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📊 MISES Data Curation - Search                                [Q:Quit H:Help]║
╠════════════════════╦═════════════════════════════════════════════════════════╣
║  NAVIGATION        ║  SEARCH FILTERS                                         ║
║  ━━━━━━━━━━━━━━━━━║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  📂 Browse Local   ║                                                         ║
║  📥 Browse Avail   ║  🔍 Keyword: ___________________                       ║
║ ▶ 🔍 Search       ║     (Type to search, Enter to filter)                   ║
║  ⬇️  Download      ║                                                         ║
║  📊 Status         ║  Filter by:                                             ║
║  ℹ️ Help           ║  ☐ Topic: All Topics ▼                                 ║
║                    ║  ☐ Source: All Sources ▼                               ║
║                    ║  ☐ Status: All (Downloaded/Not Downloaded) ▼           ║
║                    ║                                                         ║
║                    ║  [APPLY FILTERS]                                       ║
║                    ║                                                         ║
╠════════════════════╬═════════════════════════════════════════════════════════╣
║                    ║  RESULTS (7 matches)                                    ║
║                    ║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                    ║                                                         ║
║                    ║  📊 wage_inequality_gini                                ║
║                    ║     Topic: salarios_reales | Source: OECD             ║
║                    ║     Status: ✓ Downloaded (2024-12-15)                 ║
║                    ║                                                         ║
║                    ║  📊 gini_coefficient                                    ║
║                    ║     Topic: libertad_economica | Source: World Bank    ║
║                    ║     Status: ✗ Not Downloaded                           ║
║                    ║                                                         ║
║                    ║  📊 [MORE RESULTS...]                                   ║
║                    ║                                                         ║
╠════════════════════╩═════════════════════════════════════════════════════════╣
║ [Type] Search | [↑↓] Results | [Enter] View | [D] Download | [+] Queue       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Screen 7: Download Manager

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📊 MISES Data Curation - Download                              [Q:Quit H:Help]║
╠════════════════════╦═════════════════════════════════════════════════════════╣
║  NAVIGATION        ║  DOWNLOAD FORM                                          ║
║  ━━━━━━━━━━━━━━━━━║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  📂 Browse Local   ║                                                         ║
║  📥 Browse Avail   ║  Source: [OECD ▼]                                      ║
║  🔍 Search        ║  Dataset: [ALFS ▼]                                      ║
║ ▶ ⬇️  Download      ║  Indicator: [average_wage_usd ▼]                       ║
║  📊 Status         ║                                                         ║
║  ℹ️ Help           ║  Topic: [salarios_reales ▼]                            ║
║                    ║  Coverage: [latam ▼]                                    ║
║                    ║                                                         ║
║                    ║  Country Selection:                                     ║
║                    ║  [*] All (ARG,BRA,CHL,COL,MEX,PER,URY)               ║
║                    ║  [ ] Argentina (ARG)                                    ║
║                    ║  [ ] Brazil (BRA)                                       ║
║                    ║  [ ] Chile (CHL)                                        ║
║                    ║  [ ] [MORE...]                                          ║
║                    ║                                                         ║
║                    ║  Year Range: 2010 - 2024                              ║
║                    ║                                                         ║
╠════════════════════╬═════════════════════════════════════════════════════════╣
║                    ║  [PREVIEW]              [DOWNLOAD]      [CLEAR]         ║
║                    ║                                                         ║
║                    ║  Ready to download 1 indicator from OECD               ║
║                    ║  Destination: 01_Raw_Data_Bank/OECD/                  ║
║                    ║                                                         ║
╠════════════════════╩═════════════════════════════════════════════════════════╣
║ [Tab] Move | [Space] Toggle | [Enter] Download | [P] Preview | [C] Clear     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Screen 8: Download Progress

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📊 MISES Data Curation - Download Progress                     [C] Cancel    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Downloading: average_wage_usd from OECD                                     ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  [███████████████░░░░░░░░░░░░░░░░] 45% (Step 1/3: Ingesting)                ║
║                                                                               ║
║  📥 INGEST                                                        [✓]        ║
║     Fetching from OECD API...                                               ║
║     Retrieved 127 records                                                    ║
║                                                                               ║
║  🧹 CLEAN                                                         [ ]        ║
║     Standardizing country codes...                                          ║
║     [Waiting...]                                                             ║
║                                                                               ║
║  📝 DOCUMENT                                                      [ ]        ║
║     [Pending...]                                                             ║
║                                                                               ║
║  Time Elapsed: 2s  |  Estimated Remaining: 8s                               ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                       [✓] Background Mode      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Screen 9: Status Dashboard

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  📊 MISES Data Curation - Status Dashboard                      [Q:Quit H:Help]║
╠════════════════════╦═════════════════════════════════════════════════════════╣
║  NAVIGATION        ║  PROJECT OVERVIEW                                       ║
║  ━━━━━━━━━━━━━━━━━║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  📂 Browse Local   ║                                                         ║
║  📥 Browse Avail   ║  📂 Directories                                         ║
║  🔍 Search        ║  ├─ 01_Raw_Data_Bank: 12 files (245 MB)                ║
║  ⬇️  Download      ║  ├─ 02_Datasets_Limpios: 4 files (89 MB)              ║
║ ▶ 📊 Status        ║  ├─ 03_Metadata_y_Notas: 3 files (45 KB)              ║
║  ℹ️ Help           ║  └─ 04_Graficos_Asociados: 0 files                    ║
║                    ║                                                         ║
║                    ║  📊 Data Summary                                        ║
║                    ║  ├─ Total Topics: 4                                    ║
║                    ║  ├─ Downloaded Datasets: 4                             ║
║                    ║  ├─ Available Indicators: 20+                          ║
║                    ║  └─ Progress: 20% (4/20 indicators)                   ║
║                    ║                                                         ║
║                    ║  🌐 Sources Status                                      ║
║                    ║  ├─ ILOSTAT: ✓ Online (↪ 3 indicators)                ║
║                    ║  ├─ OECD: ✓ Online (↪ 7 indicators, ✓ 3 downloaded)  ║
║                    ║  ├─ IMF: ✓ Online (↪ 2 indicators)                     ║
║                    ║  ├─ World Bank: ✓ Online (↪ 4 indicators, ✓ 1)       ║
║                    ║  └─ ECLAC: ✓ Online (↪ 4 indicators)                   ║
║                    ║                                                         ║
║                    ║  🔑 API Configuration                                   ║
║                    ║  ├─ OpenRouter: ✓ Configured                           ║
║                    ║  └─ (No other API keys required)                       ║
║                    ║                                                         ║
║                    ║  📈 Recent Activity                                     ║
║                    ║  ├─ 2024-12-15 14:32: Downloaded salarios_reales_*   ║
║                    ║  ├─ 2024-12-15 13:45: Generated metadata for oecd    ║
║                    ║  └─ 2024-12-14 09:20: Imported local dataset         ║
║                    ║                                                         ║
╠════════════════════╩═════════════════════════════════════════════════════════╣
║ [R] Refresh | [C] Clear Cache | [S] Settings | [L] Logs | [A] About          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## 🛠️ Implementation Plan

### Phase 1: Core TUI Framework
1. **App Setup** (`tui/app.py`)
   - Main Textual application class
   - Screen management
   - Navigation between views

2. **Navigation Sidebar** (`tui/widgets/sidebar.py`)
   - Main menu with 6 options
   - Active selection highlight
   - Keyboard shortcuts

3. **Screen Manager** (`tui/screens/`)
   - Base screen class
   - Screen lifecycle hooks
   - Data refresh mechanism

### Phase 2: Data Browsing Screens
1. **Browse Local Data** (`tui/screens/browse_local.py`)
   - Tree view of topics
   - Dataset listing
   - Metadata preview

2. **Browse Available Data** (`tui/screens/browse_available.py`)
   - Source selection
   - Indicator listing
   - Details panel

3. **Search Interface** (`tui/screens/search.py`)
   - Search input with autocomplete
   - Filter controls
   - Results display

### Phase 3: Data Management Screens
1. **Download Manager** (`tui/screens/download.py`)
   - Form with all parameters
   - Country selector
   - Queue management

2. **Progress Monitor** (`tui/screens/progress.py`)
   - Real-time progress tracking
   - Step indicators
   - Log output

3. **Status Dashboard** (`tui/screens/status.py`)
   - Project overview
   - Directory sizes
   - Recent activity

### Phase 4: Modals & Dialogs
1. **Metadata Viewer** (`tui/widgets/metadata_viewer.py`)
   - Full markdown display
   - Scrollable content
   - Export options

2. **Confirmation Dialogs** (`tui/widgets/dialogs.py`)
   - Delete confirmation
   - Download confirmation
   - Clear cache confirmation

3. **Input Dialogs** (`tui/widgets/input.py`)
   - Text input fields
   - Dropdown selectors
   - Checkbox groups

### Phase 5: Data Layer
1. **Local Data Manager** (`tui/data/local_manager.py`)
   - Read directory structure
   - Parse metadata files
   - Track modifications

2. **API Data Manager** (`tui/data/api_manager.py`)
   - Query available indicators
   - Filter by source/topic
   - Calculate coverage

3. **Download Coordinator** (`tui/data/download.py`)
   - Queue management
   - Progress tracking
   - Error handling

---

## 📊 Directory Structure

```
src/
├── tui/
│   ├── __init__.py
│   ├── app.py                          # Main Textual app
│   ├── config.py                       # TUI configuration
│   ├── colors.py                       # Theme/color scheme
│   │
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── sidebar.py                  # Navigation sidebar
│   │   ├── metadata_viewer.py           # Metadata display modal
│   │   ├── dialogs.py                  # Confirmation/input dialogs
│   │   └── components.py                # Reusable widgets
│   │
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── base.py                     # Base screen class
│   │   ├── browse_local.py             # Browse downloaded data
│   │   ├── browse_available.py         # Browse available data
│   │   ├── search.py                   # Search interface
│   │   ├── download.py                 # Download manager
│   │   ├── progress.py                 # Download progress
│   │   ├── status.py                   # Status dashboard
│   │   └── help.py                     # Help screen
│   │
│   └── data/
│       ├── __init__.py
│       ├── local_manager.py            # Local data operations
│       ├── api_manager.py              # Available data queries
│       ├── download_coordinator.py     # Download orchestration
│       └── cache.py                    # Local caching
│
└── cli.py                              # Existing CLI (unchanged)
```

---

## 🎨 Design Principles

### Navigation
- **Sidebar Always Visible** - Quick access to all sections
- **Breadcrumb Trail** - Show current location
- **Back/Exit Clear** - ESC to go back, Q to quit
- **Consistent Hotkeys** - D=Download, M=Metadata, V=View, etc.

### Information Architecture
- **Topic-First for Local Data** - Browse by topic you care about
- **Source-First for Available Data** - Discover what each source offers
- **Search-First for Exploration** - Quick access to specific indicators

### Visual Hierarchy
- **Icons + Text** - Use rich symbols for quick scanning
- **Color Coding** - Downloaded=green, Available=blue, Error=red
- **Whitespace** - Clear separation between sections
- **Truncation** - Long names with ellipsis, expandable on focus

### Performance
- **Lazy Loading** - Load details on demand
- **Caching** - Cache API responses locally
- **Async Operations** - Downloads don't block UI
- **Responsive** - Immediate visual feedback

---

## 🔧 Key Features

### Browse Local Data
- **Tree View** - Explore topics hierarchically
- **Metadata Preview** - Quick look at dataset info
- **Bulk Operations** - Multi-select for batch actions
- **Search Within Topic** - Filter datasets in topic

### Browse Available Data
- **Source Cards** - Overview of each data source
- **Indicator Details** - Full parameter information
- **Download Status** - Show if already downloaded
- **Related Data** - Show similar indicators

### Search
- **Fuzzy Matching** - Find indicators by partial name
- **Multi-Filter** - Combine topic/source/status filters
- **Save Searches** - Save frequent searches
- **Quick Stats** - Show match count

### Download Manager
- **Form Validation** - Prevent invalid downloads
- **Preview** - Show what will be downloaded
- **Queue** - Add multiple downloads
- **Background Mode** - Run downloads while browsing

### Metadata Viewer
- **Full Markdown Rendering** - Show rich metadata
- **Syntax Highlighting** - Code blocks, tables
- **Copy to Clipboard** - Copy metadata content
- **Export** - Save as PDF/HTML

---

## 🚀 Launch Mechanism

### Entry Point
```bash
python -m src.tui.app
# or
curate tui    # if CLI aliased
```

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `Q` | Quit |
| `H` | Help |
| `Tab` | Next field |
| `Shift+Tab` | Previous field |
| `Enter` | Select/Confirm |
| `Esc` | Back/Cancel |
| `↑↓←→` | Navigate |
| `D` | Download |
| `M` | Metadata |
| `V` | View |
| `/` | Search |

---

## 📋 Data Sources

### Local Data
- **Source**: File system (`02_Datasets_Limpios/`, `03_Metadata_y_Notas/`)
- **Refresh**: Automatic on folder changes
- **Cache**: Metadata cache with 1-hour TTL

### Available Data
- **Source**: `indicators.yaml` + API queries
- **Refresh**: On-demand with refresh button
- **Cache**: 6-hour TTL for API responses

---

## ✨ User Experience Flow

### First-Time User
1. App opens → Status dashboard (see what's available)
2. Browse Available → Pick first interesting indicator
3. Download → Automatic full pipeline (ingest→clean→document)
4. Browse Local → View downloaded data and metadata
5. Search → Discover related indicators

### Power User
1. App opens → Last visited screen restored
2. Search → Find 3 indicators across sources
3. Download → Queue all 3 for batch download
4. Review → Open metadata for comparison
5. Export → Save datasets for analysis

---

## 🎯 Success Criteria

✅ **Interface Requirements**
- Responsive to all terminal sizes (min 80x24)
- All features keyboard-navigable
- Mouse support optional but nice-to-have
- Works in Windows Terminal, WSL, Linux terminals

✅ **Performance Requirements**
- App startup: < 500ms
- Screen transitions: < 100ms
- Metadata rendering: < 200ms
- Search results: < 500ms

✅ **Usability Requirements**
- New user can download data in < 3 minutes
- All actions reversible (except downloads)
- Clear error messages with solutions
- Built-in help for every screen

---

## 📦 Dependencies

```
textual >= 0.50.0          # TUI framework
rich >= 13.0.0             # Rich formatting
pandas >= 2.3.0            # Data operations
pyyaml >= 6.0              # Config parsing
python-dotenv >= 1.0       # Environment variables
requests >= 2.31.0         # API calls (existing)
openai >= 1.0              # LLM (existing)
click >= 8.1               # CLI (existing)
```

---

## 🎓 Mockup Summary

The TUI provides **9 main screens**:
1. **Main Menu** - Navigation hub
2. **Browse Local** - View downloaded datasets
3. **Browse Local Expanded** - Dataset details & metadata
4. **Metadata Viewer** - Full markdown documentation
5. **Browse Available** - Explore data sources
6. **Available Indicators** - Details per indicator
7. **Search** - Find indicators across sources
8. **Download Manager** - Configure & initiate downloads
9. **Progress & Status** - Monitor downloads and project health

Each screen is **independent but connected**, with **clear navigation** and **consistent design** throughout.

---

## 🔄 Integration with Existing Code

The TUI will:
- ✅ Use existing Config class for configuration
- ✅ Use existing DataIngestionManager for downloads
- ✅ Use existing indicators.yaml for available data
- ✅ Reuse cleaning & metadata generation logic
- ✅ Coexist with CLI (separate entry point)
- ✅ Share same data directories and cache

No modifications needed to existing core code!

