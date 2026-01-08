# TUI Quick Start

## Installation

The TUI is already built and ready to use!

```bash
cd c:\dev\data-curator
python -m src.tui
```

## First Time Setup

1. **Activate the virtual environment** (if not already active)
   ```bash
   .\venv\Scripts\Activate.ps1  # Windows
   source venv/bin/activate      # Linux/Mac
   ```

2. **Verify dependencies** (should be installed)
   ```bash
   python -m pip list | grep -i textual
   ```

3. **Launch the TUI**
   ```bash
   python -m src.tui
   ```

## Main Screens (Press these keys)

| Key | Screen | Purpose |
|-----|--------|---------|
| `1` | 📊 Status | View project overview & stats |
| `2` | 📂 Local | Browse downloaded datasets |
| `3` | 📥 Available | Explore available data sources |
| `4` | 🔍 Search | Search indicators by keyword |
| `5` | ⬇️ Download | Download new datasets |
| `6` | 📈 Progress | Monitor active downloads |
| `7` | ℹ️ Help | Keyboard shortcuts & help |

## Quick Tutorial

### 1. View Your Data
Press `2` → Browse Local Data
- Shows all datasets organized by topic
- Use `↑↓` arrow keys to navigate
- Press `M` to view metadata

### 2. Find Available Data
Press `3` → Browse Available Data
- Shows all 5 data sources
- List of 20+ economic indicators
- Use `↑↓` to navigate sources

### 3. Search for Indicators
Press `4` → Search
- Type to search by keyword (e.g., "wage", "unemployment")
- View results with details
- See download status

### 4. Download Data
Press `5` → Download Manager
- Select source, indicator, topic
- Choose year range and countries
- Click Download or add to queue
- Monitor progress on screen `6`

### 5. Get Help
Press `7` → Help Screen
- Full keyboard shortcut reference
- Navigation guide
- Tips & tricks

## Essential Keyboard Shortcuts

```
Global:
  [Q]   - Quit the application
  [H]   - Show help anytime
  [1-7] - Jump to any screen
  [/]   - Quick search

Navigation:
  [↑↓]  - Move up/down in lists
  [Tab] - Move between fields
  [Esc] - Go back

Actions (vary by screen):
  [M]   - View metadata
  [D]   - Delete/download
  [+]   - Add to queue
  [S]   - Start download
  [C]   - Cancel
```

## Common Tasks

### Browse What You Have
1. Press `2` (Local)
2. Use `↑↓` to see all topics
3. Press `M` to view metadata for selected topic

### Search for Wage Data
1. Press `4` (Search)
2. Type: `wage`
3. Press `↑↓` to see results
4. Select and press `D` to download

### Download OECD Data
1. Press `5` (Download)
2. Set Source: OECD
3. Pick an indicator
4. Set Topic: salarios_reales
5. Press `D` to download
6. Watch progress on screen `6`

### View Project Statistics
1. Press `1` (Status)
2. See total datasets, topics, indicators
3. Check which topics have data

## Troubleshooting

### "No datasets found"
- You haven't downloaded any data yet
- Use Download Manager (screen `5`)
- Or run CLI: `python -m src.cli download ...`

### Application won't start
- Check Python: `python --version`
- Install deps: `python -m pip install -r requirements.txt`
- Try: `python -m src.tui` (vs `python src/tui`)

### Can't find an indicator
- Use Search (screen `4`) to find it
- Check Browse Available (screen `3`)
- All indicators listed in `indicators.yaml`

### Slow or freezing
- Large datasets? Try filtering by year/country
- Close other apps using disk/network
- Download indicators one at a time

## File Locations

```
Data:
  📁 02_Datasets_Limpios/     - Your downloaded data
  📁 03_Metadata_y_Notas/     - Auto-generated docs
  📁 01_Raw_Data_Bank/        - Raw data from APIs

Config:
  📄 indicators.yaml          - Available indicators
  📄 config.yaml              - Tool configuration
  📄 requirements.txt         - Python dependencies

Code:
  📁 src/tui/                 - TUI source code
  📁 src/cli.py               - Old CLI (still works!)
```

## Advanced Usage

### Queue Multiple Downloads
1. Select indicators on Download screen (screen `5`)
2. Press `+` to add to queue
3. Do this for multiple indicators
4. Press `S` (Start) to download all at once

### Filter Datasets
1. Go to Browse Local (screen `2`)
2. Navigate with arrow keys
3. Only first 10 per topic shown (for speed)

### Export Data
- Datasets are standard CSV files
- Located in `02_Datasets_Limpios/{topic}/`
- Can open in Excel, Python, R, etc.

## Tips & Tricks

✅ **Fast Navigation**
- Use `1-7` keys instead of sidebar
- Press `/` for quick search anytime
- Use `Q` to quit quickly

✅ **Batch Operations**
- Queue multiple downloads
- Download runs in background
- Browse while downloading

✅ **Organization**
- Topics help organize related data
- Metadata shows data transformations
- Auto-generated documentation saved

✅ **Data Quality**
- All data is cleaned automatically
- Country codes standardized
- Missing values reported
- Transformations documented

## Next Steps

1. **Explore**: Browse your data (screen `2`)
2. **Search**: Find new indicators (screen `4`)
3. **Download**: Get fresh data (screen `5`)
4. **Export**: Use the CSV files in your analysis

## Support

**Documentation**:
- `TUI_IMPLEMENTATION_COMPLETE.md` - Full technical overview
- `TUI_DESIGN_PLAN.md` - Architecture & design
- `TUI_IMPLEMENTATION_ROADMAP.md` - Detailed implementation

**Code**:
- Press `H` in app for help
- Check `src/tui/` for screen implementations
- All managers in `src/tui/data/`

---

**Have fun exploring economic data!** 📊

For data sources and updates, see `INDEX.md`
