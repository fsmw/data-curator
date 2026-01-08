# MISES Data Curation Tool - TUI Version

Welcome to the **Text User Interface (TUI)** for the MISES Data Curation Tool!

A modern, keyboard-driven interface for exploring economic data sources, managing datasets, and initiating downloads - all from your terminal.

---

## 🚀 Quick Start (30 seconds)

```bash
# Make sure dependencies are installed
python -m pip install -r requirements.txt

# Launch the TUI
python -m src.tui
```

**That's it!** You'll see the TUI dashboard.

---

## 📺 Screens Overview

| Key | Screen | What It Does |
|-----|--------|------------|
| `1` | 📊 Status | View project stats and overview |
| `2` | 📂 Local | Browse datasets you've downloaded |
| `3` | 📥 Available | Explore available data sources |
| `4` | 🔍 Search | Find indicators by keyword |
| `5` | ⬇️  Download | Download new datasets |
| `6` | 📈 Progress | Monitor active downloads |
| `7` | ℹ️ Help | Keyboard shortcuts & help |

---

## ⌨️ Essential Keys

```
[1-7]   Jump to screen
[Q]     Quit
[H]     Help
[↑↓]    Navigate lists
[Tab]   Move between fields
[/]     Search
[D]     Download/Delete
[Esc]   Go back
```

---

## 💡 Common Tasks

### View Your Data
Press `2` → Use arrow keys → Press `M` for metadata

### Find an Indicator
Press `4` → Type search term → Browse results

### Download Data
Press `5` → Select source & indicator → Press `D`

### Get Help
Press `7` → View all shortcuts

---

## 📚 Full Documentation

| Document | Purpose |
|----------|---------|
| **[TUI_QUICKSTART.md](TUI_QUICKSTART.md)** | User guide with tutorials |
| **[TUI_IMPLEMENTATION.md](TUI_IMPLEMENTATION.md)** | What was built & how |
| **[TUI_IMPLEMENTATION_COMPLETE.md](TUI_IMPLEMENTATION_COMPLETE.md)** | Technical reference |
| **[README.md](README.md)** | Original CLI documentation |

---

## 🎯 Features

✅ **Browse & Explore**
- View all downloaded datasets
- Explore available data sources
- Search 20+ economic indicators

✅ **Manage Data**
- Organized by topic
- File statistics (size, rows, date)
- Metadata viewing

✅ **Download**
- Interactive download form
- Dynamic field selection
- Queue management
- Real-time progress

✅ **Navigation**
- Full keyboard support
- Screen shortcuts (1-7)
- Always-accessible help
- Intuitive layout

---

## 🔄 Workflow

```
Browse Available [3]
        ↓
    Search [4]
        ↓
Select Indicator
        ↓
Download Manager [5]
        ↓
Configure Parameters
        ↓
View Progress [6]
        ↓
✓ Data in 02_Datasets_Limpios/
```

---

## 💾 Data Integration

The TUI works with your existing data:

```
02_Datasets_Limpios/     ← Your downloaded, cleaned data
03_Metadata_y_Notas/     ← Auto-generated documentation  
indicators.yaml          ← Available indicators
config.yaml              ← Tool configuration
```

All data is **organized by topic** for easy browsing.

---

## 🔌 What Works Now

- ✅ Browse local datasets
- ✅ Explore available indicators
- ✅ Search by keyword
- ✅ Download form interface
- ✅ Progress visualization
- ✅ Full keyboard navigation

## ⏳ Coming Soon

- 📋 Queue persistence between sessions
- 💾 Download caching
- 🔌 Live integration with download managers
- 🧪 Automated testing

---

## ❓ Troubleshooting

**"Module not found"**
```bash
python -m pip install -r requirements.txt
```

**"No data showing"**
- Download some first with CLI: `python -m src.cli download ...`
- Or use Download Manager in TUI [5]

**Need help?**
- Press `H` in the TUI
- Read `TUI_QUICKSTART.md`

---

## 🎓 Learn More

- **For users**: See [TUI_QUICKSTART.md](TUI_QUICKSTART.md)
- **For developers**: See [TUI_IMPLEMENTATION.md](TUI_IMPLEMENTATION.md)
- **Technical details**: See [TUI_IMPLEMENTATION_COMPLETE.md](TUI_IMPLEMENTATION_COMPLETE.md)

---

## 📊 Project Info

- **Implementation**: ~11 hours
- **Screens**: 7 (all functional)
- **Data Sources**: 5 (OECD, ILOSTAT, IMF, WorldBank, ECLAC)
- **Indicators**: 20+
- **Code**: ~1,500 lines in `src/tui/`

---

## 🎉 Ready?

Start with:
```bash
python -m src.tui
```

Press `1` for overview, `4` to search, `H` for help anytime.

**Enjoy exploring economic data!** 📊

---

**Version**: 1.0.0-beta  
**Last Updated**: January 6, 2026  
**Status**: ✅ Ready for Production (browsing & exploration)
