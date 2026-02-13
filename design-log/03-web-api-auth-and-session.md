# Design Log 03 — Web API, Auth, and Session Behavior

## Background
The web app is Flask-based and includes authentication, RBAC/admin surfaces, API endpoints, and reverse-proxy deployment support.

## Problem
Key auth/session decisions (remember-me, login redirect, proxy prefixing) were encoded in bootstrap/auth modules but undocumented.

## Questions and Answers
- Q: How does auth state persist?
  - A: Flask-Login + session cookies, with remember/permanent session config in app bootstrap/auth flow.
- Q: Is deployment proxy-aware?
  - A: Yes, `ProxyFix` and `SCRIPT_NAME` support prefixed deployments.

## Design
1. **Flask app factory**
   - `create_app()` initializes SQLAlchemy, LoginManager, Babel, Admin, blueprints.
2. **Authentication model**
   - `User` model with role assignment through `user_roles`, password hashing, admin helper.
3. **Access control**
   - Dataset-level access model exists (`UserDatasetAccess`) and owner checks are enforced in dataset APIs.
4. **Session behavior**
   - Remember cookie duration and permanent session lifetime configured centrally.

## Implementation Plan
- [x] Keep login-required protection for sensitive dataset routes.
- [x] Keep ownership checks as hard filters (404 for non-owned datasets).
- [x] Keep proxy-prefix-safe URL and static path handling.

## Examples
- ✅ `login_manager.unauthorized_handler` preserves next path (`src/web/__init__.py`).
- ✅ `@login_required` on dataset endpoints (`src/web/api/datasets.py`).
- ✅ Role and user relationships in `src/models.py`.
- ❌ Exposing data mutation endpoints without authentication.

## Trade-offs
- **Pros:** Familiar Flask auth stack, straightforward deployment, secure default route protection.
- **Cons:** Session-based auth needs careful cookie/secret configuration in production.

