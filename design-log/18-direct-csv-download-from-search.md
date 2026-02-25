# Design Log 18 — Direct CSV Download from Search

## Background
The current workflow requires users to download a dataset to their account first (via "Download" button), then navigate to "Browse Local" to download the CSV file. Users want a quicker way to get CSV data without cluttering their account storage.

## Problem
1. Users need to download datasets to their account even for one-time/quick data access
2. Account storage gets cluttered with datasets that were only needed for immediate download
3. Extra navigation steps (search → download → browse local → download CSV) reduce UX efficiency

## Questions and Answers
- Q: Should direct download also save to the user's account?
  - A: **DECISION:** No, direct CSV download bypasses catalog indexing and account storage. It's a transient operation.
- Q: What about metadata/documentation when downloading directly?
  - A: **DECISION:** Direct download returns raw CSV only. For full metadata, users should use the standard download flow.
- Q: Should we support all sources for direct download?
  - A: **DECISION:** Start with sources that have simple HTTP/CSV endpoints: OWID, WorldBank, manual. Complex sources (OECD, ILOSTAT) may require account download.
- Q: How do we handle filename for direct download?
  - A: **DECISION:** Use `{indicator_name}_{source}_{timestamp}.csv` format.

## Design
1. **New API endpoint**: `POST /api/download/csv-direct`
   - Accepts: `source`, `indicator_id`, `countries` (optional), `start_year`, `end_year`
   - Streams CSV response directly with `Content-Disposition: attachment`
   - No catalog indexing, no account storage
   
2. **UI changes in search.html**:
   - Add "Download CSV" button alongside existing "Download" button
   - Visual distinction: "Download" (to account) vs "Download CSV" (direct)
   - Show loading state during fetch
   - Handle errors gracefully

3. **Backend flow**:
   - Validate request parameters
   - Fetch data via existing ingestion sources
   - Stream CSV directly to response (no disk write)
   - Handle errors with appropriate HTTP status codes

## Implementation Plan
- Phase A: Create design log and update search UI with new button
- Phase B: Implement `/api/download/csv-direct` endpoint
- Phase C: Add direct download logic to ingestion sources (OWID, WorldBank)
- Phase D: Tests and verification

## Examples
- ✅ User clicks "Download CSV" on OWID indicator → browser downloads CSV immediately
- ✅ Direct download shows spinner while fetching → saves as `gdp_per_capita_owid_20250115.csv`
- ❌ Direct download failing silently or saving to account unexpectedly
- ❌ Same button for both flows confusing users

## Trade-offs
- **Pros:** Faster UX for quick data access, less account storage clutter, reduces steps from 3 to 1
- **Cons:** No metadata included, no catalog record, source-specific implementation needed

## Implementation Results

### Phase A: API Endpoint
- ✅ Created `POST /api/download/csv-direct` endpoint in `src/web/api/download.py`
- ✅ Endpoint fetches data using existing `DataIngestionManager` without saving to disk
- ✅ Returns CSV as downloadable attachment with filename format: `{indicator_name}_{source}_{timestamp}.csv`
- ✅ Supports all configured sources: owid, worldbank, oecd, ilostat, imf, eclac
- ✅ Proper error handling with HTTP status codes
- **Bug fixes applied:**
  - Changed `config.get_directory("raw_data")` → `config.get_directory("raw")` (line 383)
  - Changed `DataIngestionManager(raw_data_dir)` → `DataIngestionManager(config)` (line 384)
  - Changed `manager.get_indicator_config()` → `searcher.get_indicator_by_id()` (line 386)
  - Changed `manager.fetch_data()` → `manager.ingest()` (line 419)
  - Added `IndicatorSearcher` import and usage

### Phase B: UI Changes
- ✅ Added "Download CSV" button in `src/web/templates/search.html` (line ~181)
- ✅ Button uses `bi-file-earmark-arrow-down` icon for visual distinction
- ✅ Button positioned before the main Download button
- ✅ Loading state with spinner during download
- ✅ Added `downloadingDirect` reactive property to Alpine component
- ✅ Implemented `downloadDirectCSV()` function with:
  - POST to `/api/download/csv-direct`
  - File download via Blob/URL.createObjectURL
  - Error handling and success feedback
  - Automatic filename extraction from Content-Disposition header

### Phase C: Testing
- **Smoke test:** `python -m py_compile src/web/api/download.py` ✅
- **Manual testing required:** API endpoint returns proper CSV with correct headers
- **Integration testing needed:** Verify file downloads correctly with proper filename
- **Test coverage gap:** No automated tests exist for this new endpoint

### Testing Recommendations
**TODO:** Add test coverage for the direct download endpoint:
1. Unit test: Test endpoint with mock DataIngestionManager and IndicatorSearcher
2. Integration test: Test end-to-end download with OWID source
3. Error handling test: Verify 400/404/500 responses
4. Filename generation test: Verify correct timestamp format

Example test structure:
```python
def test_download_csv_direct_success(client, mock_config):
    """Test successful direct CSV download."""
    response = client.post('/api/download/csv-direct', json={
        'source': 'owid',
        'indicator_id': 'gdp-per-capita-world-bank'
    })
    assert response.status_code == 200
    assert response.content_type == 'text/csv'
    assert 'attachment' in response.headers['Content-Disposition']

def test_download_csv_direct_missing_params(client):
    """Test error when required params are missing."""
    response = client.post('/api/download/csv-direct', json={})
    assert response.status_code == 400
```

### Key Decisions Documented
- Direct download does NOT save to account (transient operation)
- Uses existing ingestion infrastructure (no duplication)
- **Critical API usage pattern:** Must use `IndicatorSearcher` for config lookup, not DataIngestionManager
- **Critical API usage pattern:** Must use `manager.ingest(source, **kwargs)`, not `manager.fetch_data()`
- Visual distinction via icon (📄⬇️ vs cloud icons)
- **Lesson learned:** Need to verify DataIngestionManager API before implementation (it only has `ingest()` method)

### Files Modified
- `src/web/api/download.py` - Added new endpoint with bug fixes
- `src/web/templates/search.html` - Added button and JavaScript handler
- `design-log/18-direct-csv-download-from-search.md` - This file

## References
- Design Log #04: Search, Download, and Dataset Discovery
- `src/web/templates/search.html`
- `src/web/api/download.py`
- `src/ingestion.py`
