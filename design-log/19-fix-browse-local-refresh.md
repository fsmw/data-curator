# Design Log #19: Fix Browse Local Refresh and Auto-Indexing

## Problem

Users report that:
1. **Refresh button in /browse_local doesn't find new datasets** - Only re-indexes existing ones, doesn't scan for new CSV files
2. **Statistics don't update after downloading** - Total datasets and database size remain stale
3. **Newly downloaded datasets don't appear** - Even though files exist in 02_Datasets_Limpios/{username}/

## Root Cause

The `/datasets/refresh` endpoint was only:
- Searching datasets already in the catalog database
- Re-indexing those existing entries
- **Not scanning the filesystem** for new CSV files

## Design

### Changes

1. **New method in DatasetCatalog**: `index_user_datasets(username, force=False)`
   - Scans user's directory: `02_Datasets_Limpios/{sanitized_username}/**
   - Indexes all CSV files found
   - Returns stats: indexed, skipped, errors, total_files

2. **Modified /datasets/refresh endpoint**:
   - Calls `index_user_datasets()` to find new files
   - Then re-indexes existing datasets (preserving previous logic)
   - Returns updated statistics after refresh

3. **Download endpoint already correct**:
   - Already calls `catalog.index_dataset()` after saving file
   - Forces re-index with `force=True`

### Flow

```
User clicks Refresh → index_user_datasets() scans dir → indexes new files → 
re-indexes existing → returns updated stats → UI updates

User downloads → save file → index_dataset() → catalog updated → 
statistics available immediately
```

## Implementation

### DatasetCatalog.index_user_datasets()

```python
def index_user_datasets(self, username: str, force: bool = False) -> Dict[str, int]:
    """Index all CSV files for a specific user.
    
    Returns:
        Dictionary with indexed, skipped, errors, total_files
    """
    stats = {'indexed': 0, 'skipped': 0, 'errors': 0, 'total_files': 0}
    
    owner_segment = sanitize_username(username)
    if not owner_segment:
        return stats
    
    # Build user directory path: 02_Datasets_Limpios/{username}/
    user_dir = self.datasets_dir / owner_segment
    if not user_dir.exists():
        return stats
    
    csv_files = list(user_dir.rglob("*.csv"))
    stats['total_files'] = len(csv_files)
    
    for csv_file in csv_files:
        result = self.index_dataset(csv_file, force=force)
        if result:
            stats['indexed'] += 1
        elif result is None:
            stats['errors'] += 1
        else:
            stats['skipped'] += 1
    
    return stats
```

### Modified /datasets/refresh

```python
@api_bp.route("/datasets/refresh", methods=["POST"])
@login_required
def refresh_datasets() -> Response:
    # ... existing setup ...
    
    # NEW: Index new files from user's directory
    new_stats = catalog.index_user_datasets(current_user.username, force=force)
    
    # Then re-index existing datasets (preserve previous logic)
    user_datasets = catalog.search(...)
    for ds in user_datasets:
        # ... existing re-index logic ...
    
    # NEW: Get updated statistics
    updated_stats = catalog.get_statistics(owner_username=owner_segment)
    
    return jsonify({
        "status": "success",
        "message": "Catalog refreshed",
        "stats": {**stats, **new_stats},
        "statistics": updated_stats  # NEW
    })
```

## Files Modified

- `src/dataset_catalog.py` - Added `index_user_datasets()` method
- `src/web/api/datasets.py` - Modified `/datasets/refresh` endpoint

## Testing Checklist

- [ ] Click Refresh button with new CSV files → Files appear in list
- [ ] Statistics update (total datasets, database size)
- [ ] Download new dataset → Appears immediately in browse_local
- [ ] Existing datasets are preserved during refresh
- [ ] Error handling for invalid usernames

## Examples

### ✅ Good: New files indexed

User has files:
```
02_Datasets_Limpios/fsanmartin/general/
  - old_dataset.csv (already in catalog)
  - new_dataset_1.csv (new file)
  - new_dataset_2.csv (new file)
```

After clicking Refresh:
- `index_user_datasets()` finds 3 files
- old_dataset.csv: skipped (already indexed, no changes)
- new_dataset_1.csv: indexed ✓
- new_dataset_2.csv: indexed ✓
- Statistics updated: +2 datasets, +size

### ❌ Bad: Previous behavior

Same files, old endpoint:
- Only searches catalog database
- Finds old_dataset.csv
- Re-indexes old_dataset.csv only
- new_dataset_1.csv and new_dataset_2.csv: **never found**

## Trade-offs

- **Performance**: Scanning filesystem is O(n) where n = number of files
  - Mitigation: Only scans user's directory, not all directories
  - Typically < 100 files per user, acceptable latency
- **Consistency**: May find files that are mid-write (corrupted)
  - Mitigation: Existing index_dataset validates file can be read as CSV

## Implementation Results

### 2026-02-16
- Added `index_user_datasets()` method to DatasetCatalog
- Modified `/datasets/refresh` endpoint to scan for new files
- Verified syntax of modified files
- Statistics now included in refresh response

### Deviation from Design
None - implemented as designed.

### Test Results
Pending - requires manual testing in UI:
1. Place new CSV in 02_Datasets_Limpios/{username}/
2. Click Refresh in /browse_local
3. Verify new file appears
4. Verify statistics updated
</content>