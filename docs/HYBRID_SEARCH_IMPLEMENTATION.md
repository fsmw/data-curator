# Hybrid Search Implementation

## Overview

Implementation of dynamic search that combines local curated indicators with comprehensive remote API searches, solving the issue where users expected 95 results but only saw 3.

**Date**: January 8, 2026  
**Status**: ✅ Complete and tested  
**Commit**: ef36f24

---

## Problem Statement

### User Expectation vs Reality

**OWID Website Search**:
```
Query: "tax" → 95 results
```

**Our Tool (Before)**:
```
Query: "tax" → 3 results
```

**Issue**: Users expected comprehensive coverage but only saw locally configured indicators.

---

## Solution Architecture

### Hybrid Search Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                     User Search Query                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
         ┌─────────────────────────────┐
         │     DynamicSearcher         │
         │   (Coordinator/Merger)      │
         └──────────┬──────────────────┘
                    │
        ┌───────────┴───────────┐
        ↓                       ↓
┌──────────────┐        ┌──────────────┐
│LOCAL SEARCH  │        │REMOTE SEARCH │
│   (instant)  │        │   (2-5s)     │
└──────┬───────┘        └──────┬───────┘
       │                       │
       ↓                       ├─→ OWIDSearcher
indicators.yaml                ├─→ OECDSearcher
                              └─→ [Future: IMF, WB, etc.]
       │                       │
       └───────────┬───────────┘
                   ↓
            ┌──────────────┐
            │ SearchCache  │
            │  (5min TTL)  │
            └──────────────┘
                   ↓
         Merged Results (100+)
```

---

## Implementation Details

### 1. New Module: `src/dynamic_search.py`

#### Classes

**`SearchCache`**
- In-memory cache with configurable TTL
- Default: 5 minutes
- Methods: `get()`, `set()`, `clear()`

**`OWIDSearcher`**
- Queries: `https://ourworldindata.org/api/search`
- Returns: Standardized indicator format
- Max results: 100 per query
- Timeout: 10 seconds

**`OECDSearcher`**
- Current: Curated dataset list
- Future: OECD catalog API integration
- Keywords: tax, gdp, unemployment, wage, etc.

**`DynamicSearcher`**
- Main coordinator class
- Combines local + remote searches
- Returns: `{local_results, remote_results, metadata}`
- Parallel API calls for performance

#### Key Methods

```python
DynamicSearcher.search(
    query: str,
    include_remote: bool = True,
    max_local: int = 100,
    max_remote: int = 100
) -> Dict[str, Any]
```

**Returns**:
```python
{
    "query": "tax",
    "local_results": [...],      # From indicators.yaml
    "remote_results": [...],     # From APIs
    "total_local": 3,
    "total_remote": 97,
    "total": 100,
    "sources": {
        "local": 3,
        "owid": 95,
        "oecd": 2
    }
}
```

---

### 2. API Changes: `src/web/routes.py`

#### Updated `/api/search` Endpoint

**Before**:
```python
# Only searched indicators.yaml
searcher = IndicatorSearcher(config)
results = searcher.search(query)
return jsonify({"results": results})
```

**After**:
```python
# Hybrid search with API integration
dynamic_searcher = DynamicSearcher(config)
search_results = dynamic_searcher.search(query, include_remote=True)

# Returns metadata + results
return jsonify({
    "results": [...],
    "total": 100,
    "query": "tax",
    "sources": {"local": 3, "owid": 95, "oecd": 2}
})
```

#### New Response Fields

**Per Result**:
- `remote: true/false` - Distinguishes API vs local
- `slug` - For OWID charts (enables direct links)
- `downloaded: true/false` - Only for local indicators

**Response Metadata**:
- `total` - Total number of results
- `sources` - Breakdown by source
- `query` - Echo of search query

---

### 3. UI Updates: `src/web/templates/search.html`

#### Results Summary

```html
<span x-text="results.length"></span> Resultados para: <strong x-text="query"></strong>

<!-- Breakdown badges -->
<span class="badge bg-secondary">
  Local: <span x-text="searchMetadata.sources.local"></span>
</span>
<span class="badge bg-info">
  OWID API: <span x-text="searchMetadata.sources.owid"></span>
</span>
<span class="badge bg-info">
  OECD: <span x-text="searchMetadata.sources.oecd"></span>
</span>
```

#### Result Row Enhancements

**Remote Indicator Badge**:
```html
<span x-show="result.remote" class="badge bg-info">
  <i class="ms-Icon ms-Icon--Cloud"></i> API
</span>
```

**Action Buttons (Conditional)**:

1. **Local Indicators**: Show download button
```html
<button x-show="!result.remote && !result.downloaded">
  <i class="ms-Icon ms-Icon--Download"></i> Descargar
</button>
```

2. **OWID Remote**: Show link to chart
```html
<a x-show="result.remote && result.source === 'OWID'" 
   :href="'https://ourworldindata.org/grapher/' + result.slug" 
   target="_blank">
  <i class="ms-Icon ms-Icon--OpenInNewWindow"></i> Ver en OWID
</a>
```

3. **Other Remote**: Show info button
```html
<button x-show="result.remote && result.source !== 'OWID'">
  <i class="ms-Icon ms-Icon--Info"></i> Info
</button>
```

---

## Performance Characteristics

### Search Timing

| Operation | Time | Notes |
|-----------|------|-------|
| Local search | <10ms | Instant, from memory |
| OWID API call | ~2-3s | Network + parsing |
| OECD search | <10ms | Curated list (in-memory) |
| **First search** | **~2-3s** | **Local + remote** |
| **Cached search** | **<10ms** | **Within 5min TTL** |

### Cache Strategy

- **TTL**: 5 minutes (configurable)
- **Storage**: In-memory (lost on restart)
- **Key format**: `{query}:{include_remote}:{max_local}:{max_remote}`
- **Future**: Consider Redis for persistent cache

---

## Testing Results

### Test Query: "tax"

```bash
$ python3 test_search.py
```

**Output**:
```
================================================================================
SEARCH RESULTS FOR: 'tax'
================================================================================
✓ Found 95 results from OWID
✓ Found 2 results from OECD

📊 SUMMARY
Total: 100 results
  💾 Local (configured): 3
  ☁️  OWID API: 95
  ☁️  OECD Catalog: 2

💾 LOCAL RESULTS (Downloadable):
  • Tax Revenue (% GDP) (OWID)
  • Tax Revenue (% GDP) (OECD)
  • Tax Pressure (ECLAC)

☁️  REMOTE RESULTS (First 10 of 97):
  • Tax revenues as a share of GDP (OWID)
    🔗 https://ourworldindata.org/grapher/tax-revenues-as-a-share-of-gdp-unu-wider
  • Income share of the richest 1% (before tax) (OWID)
    🔗 https://ourworldindata.org/grapher/income-share-top-1-before-tax-wid
  [... 87 more results ...]

================================================================================
✅ SUCCESS! Now showing all available indicators from APIs
================================================================================
```

### Comparison

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Total results for "tax" | 3 | 100 | 33x |
| Search speed (first) | <10ms | ~2-3s | Slower (acceptable) |
| Search speed (cached) | <10ms | <10ms | Same |
| OWID coverage | 1 | 95 | Complete |
| User expectation match | ❌ | ✅ | Fixed |

---

## User Experience Flow

### Search Workflow

1. **User enters "tax" and clicks search**
2. **UI shows loading spinner** (2-3s)
3. **Results appear with badges**:
   - 💾 "Tax Revenue (% GDP) - OWID" → [Descargar] button
   - 💾 "Tax Revenue (% GDP) - OECD" → [Descargar] button
   - 💾 "Tax Pressure - ECLAC" → [Descargar] button
   - ☁️ "Tax revenues as a share of GDP - OWID" → [Ver en OWID] link
   - ☁️ "Income share of top 1% (before tax) - OWID" → [Ver en OWID] link
   - ... 95 more results
4. **Results summary shows**: "100 Resultados • Local: 3 • OWID API: 95 • OECD: 2"

### Actions Available

**For Local Indicators (💾)**:
- Click "Descargar" → Downloads to 02_Datasets_Limpios/
- Shows "Ya Descargado" badge if already downloaded

**For OWID Remote (☁️)**:
- Click "Ver en OWID" → Opens chart in new tab
- User can explore data on OWID website
- Future: One-click import to local indicators

**For Other Remote (☁️)**:
- Click "Info" → Shows configuration instructions
- Explains how to add to indicators.yaml

---

## Future Enhancements

### Phase 2: Expand Data Sources

**Add API Integrations**:
- ✅ OWID Search API (complete)
- ✅ OECD Curated List (complete)
- ⏳ OECD Full Catalog API
- ⏳ IMF Data Explorer API
- ⏳ World Bank Data Catalog
- ⏳ ECLAC CEPALSTAT API

### Phase 3: Remote Indicator Import

**One-Click Configuration**:
```
User finds remote indicator → Click "Import" → 
  → Auto-detect parameters →
  → Add to indicators.yaml →
  → Now downloadable
```

**Implementation**:
- Modal dialog for parameter configuration
- Auto-populate fields from API metadata
- Validate parameters before saving
- Update indicators.yaml programmatically

### Phase 4: Advanced Features

1. **Favorites/Bookmarks**
   - Save remote indicators for quick access
   - Personal curated lists

2. **Persistent Cache**
   - Redis or SQLite for cache storage
   - Survives server restarts

3. **Search Filters**
   - Filter by: topic, country availability, time range
   - Sort by: relevance, name, source

4. **Search Analytics**
   - Track popular queries
   - Suggest related indicators
   - Pre-cache common searches

---

## Maintenance

### Cache Management

**Clear Cache**:
```python
from src.dynamic_search import DynamicSearcher
from src.config import Config

searcher = DynamicSearcher(Config())
searcher.clear_cache()
```

**Check Cache Size**:
```python
cache_size = len(searcher.cache.cache)
print(f"Cached queries: {cache_size}")
```

### API Rate Limits

**OWID**:
- No documented rate limits
- Recommend: Max 10 req/min
- Current: 1 req per search (cached 5min)

**Future Considerations**:
- Implement rate limiting
- Add retry with exponential backoff
- Monitor API health

### Error Handling

**API Failures**:
- Graceful degradation to local results
- Log errors without breaking UI
- Show warning if remote search fails

**Example**:
```python
try:
    owid_results = self.owid_searcher.search(query)
except Exception as e:
    print(f"✗ OWID search failed: {e}")
    owid_results = []  # Continue with local results
```

---

## Configuration

### Environment Variables

Currently none required. Future considerations:

```bash
# .env
OWID_API_URL=https://ourworldindata.org/api/search
OWID_API_TIMEOUT=10
SEARCH_CACHE_TTL_MINUTES=5
ENABLE_REMOTE_SEARCH=true
```

### Runtime Configuration

```python
# Custom cache TTL
searcher = DynamicSearcher(config, cache_ttl_minutes=10)

# Disable remote search
results = searcher.search(query, include_remote=False)

# Limit results
results = searcher.search(query, max_remote=50)
```

---

## Known Limitations

1. **OECD Search**: Currently uses curated list, not full API
   - Only ~10 common indicators included
   - Need to expand with catalog API

2. **Cache Persistence**: In-memory only
   - Lost on server restart
   - No distributed cache

3. **Remote Downloads**: Cannot directly download remote indicators
   - Must configure in indicators.yaml first
   - Future: Auto-configuration feature

4. **API Dependencies**: Requires internet connection
   - No offline mode
   - Falls back to local if APIs fail

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `src/dynamic_search.py` | NEW: Hybrid search module | +337 |
| `src/web/routes.py` | Updated search API | +77 |
| `src/web/templates/search.html` | UI enhancements | +21 |
| **Total** | | **+435 lines** |

---

## Related Documentation

- [OWID_FIX_SUMMARY.md](./OWID_FIX_SUMMARY.md) - OWID API integration details
- [WEB_DOWNLOAD_STATUS.md](./WEB_DOWNLOAD_STATUS.md) - Complete web features
- [OECD_PARAMETER_FIX.md](./OECD_PARAMETER_FIX.md) - OECD configuration

---

## Conclusion

✅ **Problem Solved**: Users now see 100+ results matching OWID's coverage  
✅ **Performance**: Fast with caching, acceptable 2-3s initial search  
✅ **UX**: Clear distinction between local/remote with appropriate actions  
✅ **Extensible**: Easy to add more data sources (IMF, World Bank, etc.)  

**Next Steps**: Test with users, gather feedback, plan Phase 2 enhancements.
