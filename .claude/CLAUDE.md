# CLAUDE.md — thaimui-api

## Stack

- **Framework**: Flask 3.1
- **ORM**: SQLAlchemy 2.0 + Flask-SQLAlchemy
- **Serialization**: Marshmallow + marshmallow-sqlalchemy
- **Auth**: PyJWT + bcrypt
- **DB**: MySQL
- **Runtime**: Gunicorn + Docker

---

## Architecture: Controller → Service → Repository

The app is structured in three layers. Each layer has a single responsibility and calls only the layer below it.

### Controller (`app/controllers/`)
- Handles HTTP request/response
- Applies `@verify_required` (and optionally `@decode_and_verify_permission_jwt`) decorators
- Calls a service method and receives a SQLAlchemy model instance (or list)
- **Dumps the model to a dict using Marshmallow schemas and returns `jsonify()` — this is the controller's responsibility**
- Never accesses the database directly

### Service (`app/services/`)
- Contains all business logic
- Calls repository methods to fetch SQLAlchemy model instances
- Validates data and raises `AppException` subclasses on errors
- Coordinates `db.session.add()`, `db.session.commit()`, and `db.session.rollback()`
- **Returns SQLAlchemy model instances — never dicts, never `jsonify()` objects**
- Returning raw models allows services to be composed and reused by other services

### Repository (`app/repositories/`)
- Contains only SQLAlchemy queries — no business logic
- Two method variants per entity:
  - **Lightweight** (no eager loading): used for write operations where only the model itself is needed
  - **Detail** (with `selectinload()`): used for read/detail endpoints that need nested data
- Never calls services

---

## Authentication & Authorization

### Authentication — `@verify_required`
Defined in `app/api_auth.py`. Applied to every protected route.

1. Extracts token from `Authorization: Bearer <token>` header, request body `token` field, or `CENTER_ACCESS_KEY` env var (system-to-system calls)
2. Decodes the JWT using `PyJWT`
3. Validates the `jti` claim against the `Tokenlist` table (revocation check)
4. Sets `g.username` for audit trail population

**Token lifetimes** (see `app/utils.py`):
- Access token: 10 hours
- Refresh token: 7 days (stored in `Tokenlist` for revocation)

### Authorization — `@decode_and_verify_permission_jwt`
Applied to routes that require permission checks beyond basic authentication.

1. Expects a `permission_token` field in the request body
2. Decodes a base64-encoded `signed_permission_tree` from the token
3. Validates the caller has the required `method` for the current `module_code`
4. Raises `AuthorizationError` (403) if the permission check fails

**Permission tree structure:**
```json
[
  {
    "module_code": "SALES_ORDER",
    "permission": [
      { "method": "read", "check": true },
      { "method": "create", "check": false }
    ],
    "sub_modules": []
  }
]
```

---

## Error Handling with AppException

All application errors use a custom exception hierarchy defined in `app/exception.py`.

```
AppException (base)
├── UniqueError          → 409  (resource already exists)
├── NotFoundError        → 404  (resource not found)
├── ValidationError      → 400  (invalid input)
├── AuthenticationError  → 401  (invalid or expired token)
├── AuthorizationError   → 403  (permission denied)
├── MissingFieldsError   → 400  (required fields absent)
└── OuterServicesError   → 500  (external service failure)
```

**Usage pattern**: raise the most specific subclass with a descriptive message from services or repositories. A global error handler in `app/app.py` catches all `AppException` instances and returns a JSON error response with the appropriate HTTP status code.

```python
# Example
if not sales_item:
    raise NotFoundError(f"Sales item {sales_item_id} not found")
```

Never catch `AppException` internally and swallow it. Let it propagate to the global handler.

---

## FK and Select Policies

### Foreign Key Cascade Rules
- Use `ondelete='CASCADE'` when child records are meaningless without the parent (e.g., `MaterialList` rows without a `SalesItem`)
- Use `ondelete='SET NULL'` when the child can exist independently but the reference becomes optional
- Do not specify `onupdate` — PKs are immutable

### Relationship Lazy Loading Policy
All models default to **no automatic lazy loading**. This prevents N+1 queries and unexpected DB hits outside of repository methods.

| Relationship direction | `lazy=` value | Reason |
|---|---|---|
| Back-pointer (child → parent) | `lazy='noload'` | Never traversed; prevents circular auto-loading |
| Reverse nav (many-to-many back) | `lazy='noload'` | Only forward nav is used |
| Parent → children (read endpoints) | explicit `selectinload()` in repository | Loaded on demand, only where needed |

**Rule**: if you need a relationship loaded, add an explicit `selectinload()` (or `joinedload()`) in the repository detail method. Never rely on SQLAlchemy's default lazy select to load relationships implicitly.

---

## DTO Transformation Rule

**Services return SQLAlchemy model objects. Controllers dump and call `jsonify()`.**

- Services return raw SQLAlchemy model instances (or lists of them) so they can be reused by other services without serialization overhead
- Controllers call `SomeSchema().dump(result)` and then `jsonify()` — serialization is strictly a controller concern
- Services must never call `.dump()`, `jsonify()`, or return a `flask.Response`

```python
# service
def get_sales_item_detail(sales_item_id):
    item = sales_item_repository.get_sales_item_detail_by_id(sales_item_id)
    if not item:
        raise NotFoundError(f"Sales item {sales_item_id} not found")
    return item   # ← returns SQLAlchemy model

# controller
@bp.route("/<int:sales_item_id>", methods=["GET"])
@verify_required
def get_detail(sales_item_id):
    item = sales_item_service.get_sales_item_detail(sales_item_id)
    return jsonify(SalesItemDetailSchema().dump(item)), 200   # ← dump + jsonify here
```

> Note: some existing services currently return dumped dicts — these will be refactored to follow this convention.

---

## Audit Trail

All transactional models inherit from `AuditMixin`, which adds `created_by`, `updated_by`, `created_date`, and `updated_date`. These are populated automatically via SQLAlchemy `before_insert`/`before_update` event listeners using `g.username` set by `@verify_required`.

---

## Key Files Reference

| File | Purpose |
|---|---|
| `app/app.py` | App factory, error handlers, blueprint registration |
| `app/con_sqlalchemy.py` | All SQLAlchemy models |
| `app/ma_sqlalchemy.py` | All Marshmallow schemas |
| `app/exception.py` | AppException hierarchy |
| `app/api_auth.py` | `@verify_required` and permission decorators |
| `app/utils.py` | JWT encode/decode, bcrypt, permission tree checker |
| `app/extensions.py` | CenterService (external API client) |
| `docs/การสร้าง-module-ใหม่.md` | Thai-language guide: module creation checklist |
