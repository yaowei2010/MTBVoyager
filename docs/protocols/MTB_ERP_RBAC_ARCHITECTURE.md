# MTB ERP role and permission architecture

## Existing platform stack

The implementation extends the current platform instead of introducing a new ERP framework.

- Backend: Django 5, Django REST Framework, SimpleJWT and the existing SQLite authentication database.
- Frontend: React 18, React Router and Material UI.
- Deployment: the existing backend/frontend Docker images and Docker Compose stack.

The Django `auth_user` table remains the source of account identity and password authentication.

## Role model

`accounts.UserProfile` has a one-to-one relationship with Django `User` and stores exactly one role:

- `admin`: account administration, all cases and system-level functions.
- `user`: create and run analyses; edit and generate reports; access owned/assigned cases.
- `viewer`: read-only access to assigned cases.

Superusers are always treated as admins. During the first deployment, existing non-superuser accounts are migrated to `user`; the configured bootstrap account is explicitly assigned `admin`.

## Capability permissions

The UI and API consume capability strings rather than scattering role-name checks throughout analysis modules:

- `analysis.create`, `analysis.run`, `analysis.rerun`
- `analysis.view_all`, `analysis.view_own`, `analysis.view_assigned`
- `analysis.download`, `analysis.delete_any`, `analysis.delete_own`
- `report.edit`, `report.generate_ai`
- `account.manage`, `audit.view`

Roles map to sets of these capabilities in `accounts/roles.py`. Future analysis-specific capabilities can be added without changing the account schema.

## Authentication and enforcement

JWT login remains at `/accounts/token/`. `/accounts/me/` returns the authenticated user, role and capabilities. The legacy `/accounts/user-info` endpoint remains compatible.

Backend permission classes are authoritative. React `PermissionRoute` and permission-aware navigation improve the user experience but are not a security boundary.

The account administration endpoints require both JWT authentication and the admin role. Administrators cannot disable themselves or remove their own admin role.

## Administration API

- `GET /accounts/me/`
- `GET|POST /accounts/users/`
- `GET|PATCH /accounts/users/{id}/`
- `POST /accounts/users/{id}/reset-password/`
- `GET /accounts/audit-logs/`

Public self-registration is disabled. Accounts are created by an administrator.

## Audit trail

Account creation, role/status changes and password resets are written to `accounts_auditlog` with actor, target, timestamp, client address and non-secret metadata.

## Rollout boundary

Phase 1 establishes identity, roles, account administration, route-level UI restrictions and account audit events.

Phase 2 must add ownership/assignment relationships to analysis cases and enforce object-level permissions on every legacy and WGS analysis/result/download endpoint. Client-supplied `user_id` must not be trusted; API ownership decisions must use `request.user`.
