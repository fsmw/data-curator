# Localization Implementation Plan (en_US, es_CL)

## Overview
Add bilingual support (English/US en_US, Spanish/Chile es_CL) to Mises Data Curator web application. Users will select their preferred language in their profile configuration.

## Current State Analysis

### Database
- **UserWorkspace** model (src/models.py:237-293) already has `language` field (default 'en')
- No language selection UI exists in profile template

### Web UI Components Requiring Localization

#### 1. **Base Template** (src/web/templates/base.html)
- Navigation items: NAV_ITEMS in src/const.py
- Header: "Help", "New Analysis" buttons
- User menu: "Profile", "Change Password", "Admin Panel", "Logout"
- Footer version text

#### 2. **Page Templates**
- **status.html**: Welcome text, stats labels, quick links
- **search.html**: Search form, quick filters, results table, modals, messages
- **browse_local.html**: Search/filter form, statistics, table/cards view, modals, ~900+ lines of JS in template
- **profile.html**: Form labels, buttons messages
- **auth/login.html**: Login form
- **auth/change_password.html**: Password change form
- **copilot_chat.html**: Chat interface
- **visualization_*.html**: Visualization tools
- **help.html**: Instructions, keyboard shortcuts

#### 3. **JavaScript Code in Templates**
- search.html: ~500+ lines of Alpine.js with English strings
- browse_local.html: ~450+ lines with English messages, confirm dialogs
- Error messages, loading states, validation messages

#### 4. **Python Backend**
- src/web/auth.py: Flash messages, error messages
- API routes: Response messages, error handling
- Date formatting: Currently uses English format (e.g., "February 8, 2026")

#### 5. **Constants**
- NAV_ITEMS list in src/const.py (English labels only)

## Technology Choice

**Selected Framework: Flask-Babel (.po/.mo files)**

### Rationale
- Standard Flask localization solution
- .po files provide context for translators
- Supports pluralization, gender, complex grammar
- Easy extraction with `pybabel extract`
- Supports lazy translation (gettext_lazy)
- Extensive documentation and community support

### Requirements to Add
```
flask-babel>=4.0.0
```

## Implementation Plan

### Phase 1: Infrastructure Setup

#### 1.1 Install Dependencies
```bash
pip install flask-babel>=4.0.0
```

#### 1.2 Configuration
Add Babel configuration to Flask app:

**src/web/__init__.py**:
```python
from flask_babel import Babel, gettext, ngettext

babel = Babel()

@babel.localeselector
def get_locale():
    if current_user.is_authenticated:
        user_language = current_user.workspace.language
        return user_language.replace('_', '-') if user_language else 'en'
    return 'en'
```

#### 1.3 Create Babel Configuration File
Create `babel.cfg`:
```ini
[python: **/*.py]
[jinja2: **/templates/**.html]
extensions = jinja2.ext.i18n
silent = true
```

#### 1.4 Create Locale Directories
```
src/translations/
  ├── en_US/
  │   └── LC_MESSAGES/
  │       ├── messages.po (generated)
  │       └── messages.mo (compiled)
  └── es_CL/
      └── LC_MESSAGES/
          ├── messages.po
          └── messages.mo
```

### Phase 2: Database Schema Update

#### 2.1 Update UserWorkspace Model
**src/models.py**:
```python
class UserWorkspace(db.Model):
    # ... existing fields ...
    language = db.Column(db.String(10), default='en_US')  # Changed from 'en'
```

#### 2.2 Database Migration
Create migration script:
```bash
python -m flask db upgrade -m "Update language field default to en_US"
# Or manual update
ALTER TABLE user_workspaces ALTER COLUMN language SET DEFAULT 'en_US';
UPDATE user_workspaces SET language = 'en_US' WHERE language = 'en';
```

### Phase 3: Add Language Selection to Profile UI

#### 3.1 Update Profile Template
**src/web/templates/auth/profile.html**:
Add language selector:
```html
<div class="mb-3">
  <label for="language" class="form-label">{{ _('Language') }}</label>
  <select class="form-select" id="language" name="language">
    <option value="en_US" {% if workspace.language == 'en_US' %}selected{% endif %}>
      {{ _('English (United States)') }}
    </option>
    <option value="es_CL" {% if workspace.language == 'es_CL' %}selected{% endif %}>
      {{ _('Spanish (Chile)') }}
    </option>
  </select>
</div>
```

#### 3.2 Update Profile Route
**src/web/auth.py**:
```python
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form.get('email')
        language = request.form.get('language')

        if email:
            current_user.email = email

        if language and language in ['en_US', 'es_CL']:
            if current_user.workspace:
                current_user.workspace.language = language
            else:
                from src.models import UserWorkspace
                current_user.workspace = UserWorkspace(user_id=current_user.id, language=language)
            db.session.commit()
            flash(_('Profile updated successfully.'), 'success')
        else:
            flash(_('Language is required.'), 'error')

    return render_template('auth/profile.html', user=current_user, workspace=current_user.workspace)
```

### Phase 4: Extract All Strings for Translation

#### 4.1 Mark Strings for Extraction

Create a script to systematically mark strings:

**base.html**:
```html
{% trans %}Help{% endtrans %}
{% trans %}New Analysis{% endtrans %}
{% trans %}Profile{% endtrans %}
{% trans %}Logout{% endtrans %}
```

**const.py**:
```python
NAV_ITEMS = [
    {"slug": "status", "label": gettext_lazy("Status"), "icon": "house"},
    {"slug": "search", "label": gettext_lazy("Search"), "icon": "search"},
    # ...
]
```

**JavaScript in templates**:
Move common strings to i18n JSON, render in template:
```html
<script>
  const i18n = {{ i18n_strings | tojson }};
</script>
```

In Python routes:
```python
return jsonify({
    'status': 'success',
    'message': gettext('Download completed')
})
```

#### 4.2 Extract and Create .po Files
```bash
# Extract strings
pybabel extract -F babel.cfg -o messages.pot .

# Initialize Spanish translation
pybabel init -i messages.pot -d translations -l es_CL

# Update English (template for reference)
pybabel init -i messages.pot -d translations -l en_US
```

### Phase 5: Translate to Spanish (es_CL)

#### 5.1 Translate .po File
Edit `src/translations/es_CL/LC_MESSAGES/messages.po`:

Key patterns to translate:
- Navigation items: "Search" → "Buscar", "Help" → "Ayuda"
- Forms: "Username" → "Nombre de usuario", "Email" → "Correo electrónico"
- Buttons: "Download" → "Descargar", "Search" → "Buscar"
- Messages: "Download completed" → "Descarga completada"
- Status: "Loading..." → "Cargando..."
- Quick filters: "LATAM + Spain" → "LATAM + España"

#### 5.2 Translate JavaScript Strings
Move common JS strings to template:

**search.html**:
```html
<script>
  window.i18nMessages = {
    searching: {{ _('Searching...') | tojson }},
    download: {{ _('Download') | tojson }},
    error: {{ _('Error') | tojson }},
    // ... more translations
  };
</script>
<script>
  // Use in Alpine.js
  loadingMessage: window.i18nMessages.searching
</script>
```

#### 5.3 Compile Translations
```bash
pybabel compile -d translations
```

### Phase 6: Date/Time Localization

Use Babel date formatting:

In templates:
```html
{{ user.created_at|format_date }}
```

Custom filter:
```python
@app.template_filter('format_date')
def format_date(dt, format='medium'):
    from flask_babel import format_date as babel_format_date
    return babel_format_date(dt, format=format)
```

JavaScript date formatting:
```javascript
// In browse_local.js
const dateFormatter = new Intl.DateTimeFormat(
  '{{ get_locale() }}',
  { year: 'numeric', month: 'long', day: 'numeric' }
);
```

### Phase 7: Update API Responses

Mark API response messages:

**src/web/api/datasets.py** (example):
```python
from flask_babel import gettext as _

@bp.route('/statistics')
def get_statistics():
    # ...
    return jsonify({
        'status': 'success',
        'message': _('Statistics loaded successfully')
    })
```

**Important**: API responses should use the requesting user's language.

Add helper:
```python
def get_user_locale():
    if current_user.is_authenticated:
        return current_user.workspace.language.replace('_', '-') or 'en'
    return 'en'
```

### Phase 8: Update Authentication Routes

**src/web/auth.py**:
```python
flash(_('Your account has been disabled.'), 'error')
flash(_('Invalid username or password.'), 'error')
flash(_('Profile updated successfully.'), 'success')
flash(_('Current password is incorrect.'), 'error')
```

### Phase 9: Testing

#### 9.1 Test Scenarios

1. **Profile Language Selection**
   - Navigate to /auth/profile
   - Select "Spanish (Chile)" from dropdown
   - Save
   - Verify workspace.language = 'es_CL' in database
   - Refresh page → verify UI in Spanish

2. **UI Translation Coverage**
   - Start page (status.html): All labels in correct language
   - Search page: All buttons, filters, messages translated
   - Browse local: Table headers, modals, JS messages
   - Profile: Form labels, buttons, messages

3. **JavaScript Localization**
   - Search page: "Searching...", download status messages
   - Browse local: "Loading...", delete confirm dialog
   - Error messages: All JS strings use i18n JSON

4. **Date Formatting**
   - English: "February 8, 2026"
   - Spanish: "8 de febrero de 2026"

5. **API Response Messages**
   - Check error messages in browser network tab
   - Verify they're in selected language

6. **Persistence**
   - Login, change language, logout, login → language persists
   - Switch browser → language persists

### Phase 10: Extraction Script

Create **scripts/extract_translations.py**:
```python
#!/usr/bin/env python
import subprocess
import sys

def run_command(cmd):
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Error: {cmd}")
        sys.exit(1)

def main():
    print("Extracting strings for translation...")
    run_command("pybabel extract -F babel.cfg -o messages.pot .")

    print("Updating translations...")
    run_command("pybabel update -i messages.pot -d translations")

    print("Compiling translations...")
    run_command("pybabel compile -d translations")

    print("Done! Review and edit .po files.")

if __name__ == "__main__":
    main()
```

Usage:
```bash
python scripts/extract_translations.py
```

### Phase 11: Documentation

Create **docs/LOCALIZATION.md**:
```markdown
# Localization Guide

## Adding New Translations

1. Mark strings with `_()` or gettext_lazy()
2. Run extraction script
3. Update .po files
4. Compile translations

## Supported Languages
- en_US: English (United States)
- es_CL: Spanish (Chile)

## Adding a New Language
1. `pybabel init -i messages.pot -d translations -l <locale>`
2. Translate .po file
3. Compile with `pybabel compile -d translations`
```

## Implementation Phases Summary

| Phase | Tasks | Estimated Effort |
|-------|-------|------------------|
| 1 | Setup Flask-Babel infrastructure | 2h |
| 2 | Update database schema | 1h |
| 3 | Add language selector to profile | 2h |
| 4 | Extract all strings (~5000 strings) | 4h |
| 5 | Translate to Spanish (es_CL) | 8h |
| 6 | Date/time localization | 2h |
| 7 | Update API responses | 3h |
| 8 | Update authentication routes | 2h |
| 9 | Testing & fixes | 4h |
| 10 | Create extraction script | 1h |
| 11 | Documentation | 1h |

**Total Estimated Effort**: ~30 hours

## Key Challenges & Solutions

### 1. JavaScript Strings inTemplates
**Challenge**: search.html and browse_local.html have 900+ lines of JS with English strings.

**Solution**:
- Extract common UI strings to i18n JSON object
- Render in template: `<script>const i18n = {{ i18n_strings | tojson }};</script>`
- Use in Alpine.js: `x-text="i18n.searching"`

### 2. Date Formatting
**Challenge**: Python templates, JavaScript both need localized dates.

**Solution**:
- Python: Use `format_date()` template filter with Babel
- JavaScript: Use `Intl.DateTimeFormat` with user's locale

### 3. API Language Determination
**Challenge**: API responses need user's preferred language.

**Solution**:
- Check `current_user.workspace.language` in API routes
- Store locale in session for anonymous users
- Use `babel.get_locale()` context

### 4. Pluralization
**Challenge**: English "1 item" vs "2 items", Spanish may be different.

**Solution**:
- Use `ngettext()` in Python: `ngettext('%(num)d item', '%(num)d items', count)`
- Add plural forms to .po file

### 5. Long Templates (search.html: 928 lines)
**Challenge**: Marking all strings in large files is tedious.

**Solution**:
- Use systematic extraction with babel
- Review extraction results in messages.pot
- Validate no missing strings

## Files Modified

### New Files
- `babel.cfg` - Babel extraction config
- `src/translations/en_US/LC_MESSAGES/messages.po` - English translation (template)
- `src/translations/es_CL/LC_MESSAGES/messages.po` - Spanish translation
- `scripts/extract_translations.py` - Translation helper script
- `docs/LOCALIZATION.md` - Localization documentation

### Modified Files
- `requirements.txt` - Add flask-babel
- `src/models.py` - Update UserWorkspace.language default
- `src/web/__init__.py` - Initialize Babel
- `src/web/auth.py` - Update profile route with language selection
- `src/web/templates/base.html` - Mark UI strings
- `src/web/templates/auth/profile.html` - Add language selector
- `src/web/templates/*.html` - Mark strings for extraction
- `src/const.py` - Mark NAV_ITEMS with gettext_lazy
- `src/web/api/*.py` - Mark response messages

## Testing Checklist

- [ ] User can select language in profile
- [ ] Language preference persists across sessions
- [ ] Navigation items translated
- [ ] All page templates translated
- [ ] JavaScript strings translated
- [ ] API messages in correct language
- [ ] Date/time formatted correctly
- [ ] Error messages localized
- [ ] Loading states localized
- [ ] Pluralization works correctly
- [ ] No English strings visible when language is es_CL

## Next Steps After Implementation

### 1. Review and Refine Translations
- Have native Spanish speakers review translations
- Check context-specific translations (e.g., technical terms)
- Adjust for natural phrasing

### 2. Add More Languages
The framework supports adding additional languages:
```bash
pybabel init -i messages.pot -d translations -l pt_BR  # Portuguese (Brazil)
pybabel init -i messages.pot -d translations -l fr_FR  # French (France)
```

### 3. Consider Translation Management
For larger scale, consider:
- Web-based translation tools (Transifex, Crowdin)
- Translation memory for consistency
- Automated translation updates with AI (with human review)

## Examples

### Before Translation
```html
<button class="btn btn-primary">
  <i class="bi bi-download"></i> Download
</button>
```

### After Translation
```html
<button class="btn btn-primary">
  <i class="bi bi-download"></i> {{ _('Download') }}
</button>
```

### JavaScript Before
```javascript
this.message = 'Loading datasets...';
```

### JavaScript After
```html
<script>
  window.i18n = {{ {
    'loading_datasets': _('Loading datasets...'),
  } | tojson }};
</script>
<script>
  this.message = window.i18n.loading_datasets;
</script>
```

### Python Before
```python
flash('Profile updated successfully.', 'success')
```

### Python After
```python
flash(_('Profile updated successfully.'), 'success')
```

---

**Last Updated**: 2026-02-08
**Languages**: en_US (template), es_CL (target)