# TUI QUICK REFERENCE CARD

## LAUNCH

```bash
python -m src.tui
```

---

## SCREEN NAVIGATION

| Key | Screen | Purpose |
|-----|--------|---------|
| `1` | 📊 Status | Project overview |
| `2` | 📂 Local | Your datasets |
| `3` | 📥 Available | Available sources |
| `4` | 🔍 Search | Find indicators |
| `5` | ⬇️ Download | Get new data |
| `6` | 📈 Progress | Track downloads |
| `7` | ℹ️ Help | Keyboard guide |

---

## GLOBAL SHORTCUTS

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `H` | Help |
| `/` | Search |
| `Esc` | Back |

---

## NAVIGATION

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move in list |
| `←` / `→` | Move in menus |
| `Tab` | Next field |
| `Enter` | Select/Submit |

---

## SCREEN ACTIONS

| Key | Action |
|-----|--------|
| `D` | Download/Delete |
| `M` | View metadata |
| `Space` | Toggle selection |

---

## COMMON TASKS

### Browse Your Data
1. Press `2` (Browse Local)
2. Use `↑`/`↓` to navigate
3. Press `M` to view metadata

### Search for Indicators
1. Press `4` (Search)
2. Type your search term
3. View results with details

### Download Data
1. Press `5` (Download)
2. Select source & indicator
3. Configure parameters
4. Press `D` to queue

### Monitor Progress
1. Press `6` (Progress)
2. See real-time download status
3. View logs and timing

---

## STATUS SCREEN (Press 1)

Shows:
- Project summary
- Total datasets
- Data sources
- Recent activity

---

## BROWSE LOCAL (Press 2)

Shows:
- Your downloaded data by topic
- File size & row count
- Modification dates
- Metadata available

Actions:
- `↑`/`↓` - Navigate topics
- `→` - Expand topic
- `M` - View metadata
- `D` - Delete dataset

---

## BROWSE AVAILABLE (Press 3)

Shows:
- Data sources (5 sources)
- Available indicators
- Coverage information
- Update status

Actions:
- `↑`/`↓` - Navigate sources
- `→` - View indicators
- `Space` - Filter by source

---

## SEARCH (Press 4)

Shows:
- Search results
- Matching indicators
- Source information
- Coverage details

Actions:
- Type to search
- `/` or Tab to search
- `↑`/`↓` - Navigate results
- `Enter` - View details

---

## DOWNLOAD MANAGER (Press 5)

Shows:
- Download form
- Source selection
- Indicator selection
- Parameters

Actions:
- `Tab` - Move between fields
- `Enter` - Select from dropdown
- `D` - Queue download
- `Esc` - Cancel

---

## PROGRESS MONITOR (Press 6)

Shows:
- Active downloads
- Progress bars (3 steps)
- Download logs
- Timing information

Actions:
- View real-time progress
- See detailed logs
- Cancel button available

---

## HELP (Press 7)

Shows:
- All keyboard shortcuts
- Screen descriptions
- Tip of the day
- Quick reference

---

## DOCUMENTATION

| File | Time | Best For |
|------|------|----------|
| TUI_README.md | 5m | Quick start |
| TUI_QUICKSTART.md | 15m | Learning |
| TUI_IMPLEMENTATION.md | 20m | Architecture |
| TUI_IMPLEMENTATION_COMPLETE.md | 30m | Deep dive |
| TUI_INDEX.md | 10m | Navigation |

---

## TROUBLESHOOTING

**App won't start?**
- Check: `python -m pip install -r requirements.txt`

**No data showing?**
- Download first with Download Manager (Press 5)
- Or use CLI: `python -m src.cli download`

**Keyboard not responding?**
- Try pressing `Esc` first
- Then press `H` for help

**Questions?**
- Press `H` in app
- Read TUI_QUICKSTART.md
- Check TUI_IMPLEMENTATION.md

---

## QUICK STATS

- **Screens**: 7 (all functional)
- **Sources**: 5 (OECD, ILOSTAT, IMF, ECLAC, WorldBank)
- **Indicators**: 20+ economic indicators
- **Topics**: 4 local data categories
- **Status**: Production Ready v1.0.0-beta

---

## NEXT STEPS

1. **Run**: `python -m src.tui`
2. **Explore**: Press 1-7 to try screens
3. **Learn**: Press H for help
4. **Discover**: Use Search (Press 4)

---

## NEEDS HELP?

**In app**: Press `H`  
**User guide**: Read `TUI_QUICKSTART.md`  
**Architecture**: Read `TUI_IMPLEMENTATION.md`  
**Technical**: Read `TUI_IMPLEMENTATION_COMPLETE.md`  

---

**Version**: 1.0.0-beta | Status: Ready | Date: Jan 6, 2026
