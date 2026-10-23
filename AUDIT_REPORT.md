# Lost & Found Repository Audit

Audit snapshot: 2026-10-24. This report describes the checked-out repository and its current worktree; it does not describe a live deployment. See the 2026-10-24 addendum for the latest verified state.

## Repository state and architecture

- The project is a Django 6.1.1 application with separate `accounts`, `items`, `claims`, `matches`, `notifications`, and `reports` apps. Django templates serve authentication, reporting, claims, notifications, and admin functions. The project uses the built-in `User` model with a one-to-one `Profile` role, SQLite by default, and PostgreSQL when `DATABASE_URL` is set.
- This audit follows the 2026-10-13 historic snapshot and its subsequent remediations. The current work is based on `origin/main` at `b7ab771`, on branch `codex/explore-item-claim-cta`; its latest changes are detailed in the 2026-10-24 addendum below.
- The earlier pre-existing worktree changes described in the historic 2026-10-13 snapshot were carried into the merged mainline. This addendum records only newly verified changes and findings from the current follow-up.
- A Next.js 16.4 frontend has been added alongside Django. Its `/` landing and `/browse` routes are Next pages. Django remains the backend for legacy workflows, with a read-only JSON item endpoint added in the pre-existing worktree changes. This is a hybrid implementation, not a Django-only project.

## Existing functionality

Registration/login/profile, USER/ADMIN profile roles, item reporting/search/filtering/archive/restore, claim submission/review/withdrawal, matching, in-app notifications, role-protected admin dashboard and CSV reports, health endpoint, and deployment documentation are present. The follow-up now includes password reset and optional structured ComLab location/time fields. There is still no distinct custody/handover entity, school email verification, or school-specific roles.

## Verified findings

### P0-1 — Production settings accept a hard-coded secret and default to debug

- **Status:** Fixed in this audit
- **Evidence:** `config/settings.py:28-37` provides a committed fallback `SECRET_KEY` and defaults `DJANGO_DEBUG` to `True`. `.env.example` also contains a fixed development key.
- **Impact:** A production process missing environment configuration may expose detailed errors and use a publicly known signing secret.
- **Root cause:** Development fallbacks are not gated on explicit debug mode and production startup does not fail closed.
- **Fix/acceptance:** Default debug off; allow a development fallback only with explicit debug mode; fail startup if a production secret is absent or uses the development fallback. Document local setup and production variables.
- **Tests:** Verify development startup and production settings fail safely without the required secret; run deployment checks.

### P1-1 — Claims are accepted for lost reports

- **Status:** Fixed in this audit
- **Evidence:** `claims/views.py:42-53` only checks that the item is active, not that it is `FOUND`.
- **Impact:** A user can submit a claim against an active lost report, creating a claim with no found property to return.
- **Root cause:** Eligibility validation omits `item_type`.
- **Fix/acceptance:** Permit submissions only for active `FOUND` items; enforce at the request boundary and add direct POST regression coverage.
- **Tests:** Active found item accepts claims; lost and archived found items do not.

### P1-2 — Claim approval has no atomic state transition

- **Status:** Fixed in this audit; PostgreSQL lock behavior still needs integration verification
- **Evidence:** `claims/views.py:202-240,257-293` checks pending status before invoking helpers that independently save the approved claim, archive the item, and reject competing claims. These writes are not in a database transaction and rows are not locked.
- **Impact:** Two reviewers can act on competing claims based on stale pending state. Partial database writes are also possible if an intermediate operation fails.
- **Root cause:** The multi-row workflow is not atomic, and the item is not used as the serialization point for all claims.
- **Fix/acceptance:** Serialize review decisions on the item inside `transaction.atomic`, re-read the claim/item state after acquiring the lock, and write claim/item/competing-claim statuses together. Notify only after a successful commit. Verify race-sensitive behavior on PostgreSQL; SQLite cannot prove row-lock semantics.
- **Tests:** Approval rejects later competing reviews and preserves consistent state; concurrency test on PostgreSQL deployment CI is recommended.

### P1-3 — Concurrent duplicate claim submissions are not prevented

- **Status:** Fixed in this follow-up; production migration still requires the included duplicate preflight to pass
- **Evidence:** `claims/views.py:55-77` performs an `.exists()` check before inserting. `claims/models.py` has no uniqueness constraint on pending `(item, claimant)` claims.
- **Impact:** Concurrent requests can create multiple pending claims from the same user for one item.
- **Root cause:** Check-then-insert is not an atomic guard.
- **Fix/acceptance:** Add a conditional unique constraint for pending claims, after checking existing data for duplicates, and handle integrity errors cleanly.
- **Tests:** Duplicate sequential and concurrent submission behavior; migration consistency.

### P1-4 — CSV exports do not neutralize spreadsheet formulas

- **Status:** Fixed in this audit
- **Evidence:** `reports/views.py:113-275` writes user-controlled titles, descriptions, locations, claim messages, proof details, reviewer notes, usernames, and category text directly into CSV cells.
- **Impact:** Opening an export in spreadsheet software can execute formulas embedded in cell values.
- **Root cause:** CSV quoting handles delimiters but does not neutralize formula-leading cell contents.
- **Fix/acceptance:** Escape formula-leading text cells in all exports while retaining the CSV structure; add regression tests for `=`, `+`, `-`, and `@` prefixed values.

### P2-1 — Upload validation and storage durability are not established

- **Status:** Upload validation fixed in follow-up; production durability needs verification
- **Evidence:** Follow-up adds decoded image validation on the item and profile image model fields. `MEDIA_ROOT` remains local by default; production persistence depends on setting `DJANGO_MEDIA_ROOT` to an actual persistent mount.
- **Impact:** The claimed upload size/type controls are not evident in the actual form code, and local media can disappear on ephemeral hosting or be unavailable in production.
- **Recommended fix:** Validate decoded image content and size at the form boundary; select persistent volume/object storage and private access policy based on deployment. Confirm the actual Railway service/storage configuration.
- **Tests:** Invalid image and oversize upload rejection; verify production media survives redeploy.

### P2-2 — Matching maintenance does not cover edits or archive transitions

- **Status:** Fixed in follow-up
- **Evidence:** Follow-up reconciles matches when an item is edited, archived, or restored; regression tests cover stale pending suggestions and retained reviewed history.
- **Impact:** Suggested match rows and displayed scores may become stale.
- **Recommended fix:** Reconcile matches on edits and lifecycle changes; define how confirmed/dismissed decisions behave when a pair changes.
- **Tests:** Edit/archival invalidation, duplicate prevention, reverse-direction and score boundary cases.

### P2-3 — Account and school identity policy is not implemented

- **Status:** Confirmed gap; school policy needed
- **Evidence:** The app still defines USER and ADMIN without school affiliation verification. Password reset is now implemented; school domain, account verification and deactivation policy remain unset.
- **Impact:** The system does not distinguish student, faculty, or lab staff, and cannot verify current school affiliation. Public registration may be inappropriate for the school.
- **Recommended fix:** Confirm identity-verification, email domain, role assignment, and deactivation policies before implementing them. No school domain is assumed in this audit.
- **Tests:** Registration and role-assignment policy tests after decisions.

### P2-4 — Claim reviewer authority is a school policy decision

- **Status:** Confirmed behavior; policy needs confirmation
- **Evidence:** `claims/views.py:28-35` allows either the item reporter or an administrator to review claims. `review_claim_view` applies that rule directly to POST requests.
- **Impact:** An ordinary item reporter can approve a claim and cause the item to be archived, without a separate staff handover record. This may be unsuitable if school staff must physically verify/release property.
- **Recommended fix:** Confirm whether reporters may review claims or whether lab staff/admin must authorize handover. The current behavior is documented; it is not changed without policy direction.
- **Tests:** Direct POST authorization and handover workflow tests once policy is confirmed.

### P2-5 — Item reports lack structured ComLab location and custody data

- **Status:** Partially fixed in implementation follow-up; custody tracking remains a school workflow decision
- **Evidence:** Follow-up adds optional building, room, workstation, and approximate time fields. No custody/handover location field or custody entity exists.
- **Impact:** New reports can now use structured location details, but older entries may still only have free-text location, and custody tracking remains absent.
- **Recommended fix:** Optional structured location/time fields were added without making them required; custody/handover fields require policy review.
- **Tests:** Form validation, search/filtering, and migration preservation.

### P2-6 — Deployment docs conflict with the repository configuration

- **Status:** Fixed locally; live hosting configuration still needs verification
- **Evidence:** Follow-up deployment instructions no longer depend on a nonexistent `railway.json` and document build, migration, start and media volume configuration. Actual host settings have not been inspected.
- **Impact:** The documented commands now match the checkout, but the live service's build/start/migration configuration has not been confirmed.
- **Recommended fix:** Update deployment instructions to match the actual process configuration and hosting target; confirm the current service's build/start/migration commands.
- **Tests:** Follow setup in a clean environment and verify checks against the target host.

### P2-7 — Frontend deployment topology and discovery behavior need operational verification

- **Status:** Needs verification
- **Evidence:** Pre-existing `src/app/browse/page.tsx` calls `DJANGO_URL` with a fallback to `http://127.0.0.1:8000`; `next.config.ts` rewrites all paths to Django. No Next.js process is present in `Procfile`, which starts only Gunicorn.
- **Impact:** A separately deployed Next server without `DJANGO_URL` will query itself/container localhost for catalog data; current deployment instructions do not describe running both services.
- **Recommended fix:** Choose a single-service or split-service deployment topology and configure the backend origin explicitly; exercise paths, cookies, and API access in that topology.
- **Tests:** Production-like frontend/backend integration test.

### P2-8 — Copying `.env.example` does not configure Django

- **Status:** Documentation clarified in follow-up
- **Evidence:** Django reads environment variables and does not load `.env` automatically. README now explicitly instructs operators to export variables or set them in the hosting service.
- **Impact:** Operators may believe settings in `.env` are active when Django ignores that file, leading to startup failures or unintended defaults.
- **Recommended fix:** Clarify that values must be exported by the shell/service or add a documented dotenv loader for local development. Never load a local dotenv file implicitly in production.
- **Tests:** Clean setup following documented local instructions, and production environment validation.

### P3-1 — Timezone is UTC rather than the proposed school timezone

- **Status:** Fixed locally with `Asia/Manila` default and `DJANGO_TIME_ZONE` override; school operations should verify the default
- **Evidence:** `config/settings.py:161` sets `TIME_ZONE = 'UTC'` with timezone support enabled.
- **Impact:** Local dates/times may display differently from school operations.
- **Recommended fix:** Confirm and set the school's operating timezone, then verify date boundaries and exports.

### P3-2 — Django reported a missing static source directory

- **Status:** Fixed in this audit by only configuring the optional source directory when it exists
- **Evidence:** `config/settings.py:172` lists `BASE_DIR / 'static'`; that directory is absent. `manage.py check` emits `staticfiles.W004`.
- **Impact:** Development checks are noisy and static asset assumptions are unclear.
- **Recommended fix:** Add the intended directory or remove it from `STATICFILES_DIRS`, and ensure collectstatic behaves as expected.

## Test and verification baseline

- `py -3.14 manage.py test`: **141 tests passed**. Django emitted the missing static directory warning.
- `py -3.14 manage.py check`: completed with one `staticfiles.W004` warning.
- `py -3.14 manage.py makemigrations --check --dry-run`: no model changes detected.
- `npm run build`: Next.js 16.4.0 production build completed successfully; routes `/` and `/browse` were built.
- `git diff --check`: no whitespace errors in the initial tracked diff.
- These results are local checks only. No production database, hosting account, deployed service, backups, or live media store were accessible.

## Change report and post-fix verification

- `config/settings.py`: debug now defaults off; production is recognized by `DJANGO_ENV=production` and common platform markers; unsafe debug and missing/development secrets fail startup. The optional static source directory is registered only when present. No database migration is required.
- `claims/views.py`: submission now requires an active found item; review decisions lock the item and claim and update claim/item/competing claims in one transaction. `claims/tests.py` adds active-lost rejection and stale-approval coverage, and corrects the claim fixtures to found items.
- `claims/models.py` and `claims/migrations/0002_pending_claim_unique_per_user_item.py`: add a conditional unique constraint for one pending claim per item/user. Migration preflight aborts without deleting records if duplicates exist. Local database preflight found zero duplicate pairs and the migration applied successfully.
- `claims/views.py` and `claims/tests.py`: translate a concurrent uniqueness conflict into the same safe message as the existing duplicate check; tests cover database enforcement, allowed resubmission after rejection, and conflict handling.
- `reports/views.py`: every CSV row neutralizes formula-leading text. `reports/tests.py` verifies formula escaping.
- `accounts/tests.py`: verifies production rejects missing secrets and debug mode.
- `README.md` and `DEPLOYMENT.md`: document local debug setup, required production environment and correct the reference to the absent `railway.json`.
- Post-fix before duplicate-claim follow-up, `py -3.14 manage.py test`: **146 tests passed**; after the follow-up: **148 tests passed**.
- Post-fix `py -3.14 manage.py check` with explicit `DJANGO_DEBUG=True`: passed without the previous `staticfiles.W004` warning.
- Post-fix `py -3.14 manage.py makemigrations --check --dry-run`: no model changes detected.
- `npm run build` passed. Next.js code was not changed in this audit pass.
- PostgreSQL concurrency, production `check --deploy`, host configuration, storage persistence, and live deployment remain unverified.

## Prioritized implementation roadmap

1. **Security and valid claims (complete in this pass):** fail-safe production key/debug settings; only allow claims for active found items; make review transition atomic and revalidate state; regression tests.
2. **Claim integrity (complete locally):** conditional database uniqueness for one pending claim per user/item, with a migration duplicate-data preflight. Confirm the preflight succeeds against the production database before rollout.
3. **Operational return workflow:** decide reporter versus staff review authority; add custody/handover record only if staff release is required; add notifications on commit.
4. **Discovery and uploads (implemented locally):** validate image content/size; reconcile stale matches; support optional structured ComLab location fields and search.
5. **Deployment readiness:** choose frontend topology, persistent media and database backup plan, correct deployment docs/config, local timezone, static warning; run PostgreSQL and production-like integration checks.

## Production deployment checklist

- Required: strong unique `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, explicit `DJANGO_ALLOWED_HOSTS`, PostgreSQL `DATABASE_URL`, and correct `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Enable HTTPS redirect, secure session/CSRF cookies, and HSTS only after HTTPS/proxy behavior is confirmed; configure trusted proxy headers only for the actual host.
- Run `manage.py migrate`, `collectstatic --noinput`, `manage.py check --deploy`, and tests against the intended release before serving traffic.
- Configure persistent media storage; local `MEDIA_ROOT` is not sufficient evidence of durable production uploads.
- Back up PostgreSQL and rehearse restore. `/health/` currently checks only that the web process returned JSON; it does not probe the database.
- If Next.js is deployed, set `DJANGO_URL` to the backend origin and configure both frontend and backend processes/routes. `Procfile` currently launches Django only.

## Known limitations

The school identity/reviewer policies are not supplied. Live Railway configuration, database engine and version, media volume, backup schedule, TLS/proxy settings, and deployed branches could not be inspected. SQLite's test run does not verify PostgreSQL row-lock behavior.

## Implementation follow-up (2026-10-13)

The workspace was reorganized during follow-up into `backend/` (Django) and `frontend/` (Next.js). The original application paths shown in the audit findings are therefore now under `backend/`; the historical branch/tree observations above describe the audit snapshot and are not a claim about the reorganized checkout. The existing uncommitted frontend and directory-move changes were preserved.

Completed in follow-up:

- `backend/config/validators.py` validates decoded JPEG, PNG, and WEBP uploads, limits images to 5 MiB and 20 megapixels, and rejects corrupt or mislabeled files. Item and profile image fields use the validator; migrations `backend/items/migrations/0002_alter_item_image.py` and `backend/accounts/migrations/0002_alter_profile_profile_image.py` record the model validation state.
- Password reset uses Django's built-in views and templates; unknown email addresses get the same outward result. Actual delivery requires production SMTP configuration.
- The Next.js sign-in screen now links to the password-reset flow.
- Matching is reconciled when reports change or are archived. Stale pending suggestions are removed; confirmed/dismissed records remain review history while scores are refreshed for active pairs.
- Logout now requires POST and CSRF protection. `/ready/` separately probes the database and returns only a generic 503 response if unavailable.
- Match UI labels scores as rule-based similarity out of 100, not a probability. `TIME_ZONE` defaults to `Asia/Manila` (overridable with `DJANGO_TIME_ZONE`), and `DJANGO_MEDIA_ROOT` allows uploads to use a persistent mounted directory.
- Deployment guidance now documents the split app paths, persistent media mount, SMTP requirement for password recovery, and health versus readiness semantics.
- `backend/items/models.py`, `backend/items/forms.py`, and migration `0003_item_approximate_time_item_building_item_room_and_more.py` add optional building, room, workstation/landmark, and approximate time values. These flow to item detail, search, the read-only catalog API, staff CSV export, and the Next.js browse card. Existing rows receive blank/null values; the migration does not rewrite or delete records.
- The match location score now incorporates those structured details and retains numeric workstation/room identifiers, so two different lab numbers no longer compare as identical just because their text labels match.
- `.github/workflows/ci.yml` runs Django checks, migration consistency, the backend test suite, and the Next.js production build on pushes and pull requests. The workflow file has not yet run on GitHub.

Verification after follow-up: `py -3.14 manage.py test` from `backend/` passed **167 tests**; `py -3.14 manage.py check` passed with explicit local debug mode; `py -3.14 manage.py makemigrations --check --dry-run` reported no changes. `npm run build` from `frontend/` passed on Next.js 16.4.0. The test runner still emits Django/WhiteNoise's warning that `backend/staticfiles/` does not exist before `collectstatic`; deployment build instructions run `collectstatic`. No PostgreSQL concurrency run or production deployment was performed. The local development database has the new item fields migration applied.

## Local accounts and homepage update

- Added `backend/accounts/management/commands/seed_demo_accounts.py`. It creates a standard USER and an ADMIN profile with random one-time passwords, refuses to run unless debug is explicitly enabled outside a recognized production environment, and does not overwrite existing demo users. The local database now contains `comlab_demo_user` and `comlab_demo_admin`; credentials are shared separately with the user and are not stored here.
- The Next.js homepage keeps the existing hero direction, removes unverified numerical success claims from the following section, and adds clear browse-found/report-found paths, a privacy reminder, and a more readable three-step explanation.
- Verification for this update: `manage.py check` passed; the created account roles and active/staff flags were confirmed in the local database; `npm run build` passed. No Django test suite was run for this request.

Remaining implementation depends on school or hosting decisions: staff-only versus reporter claim approval and physical handover/audit records; approved school identity and deactivation rules; required ComLab location/custody fields; actual persistent Railway volume, SMTP credentials, PostgreSQL migration preflight, and backup/restore verification. No policy assumptions or production changes were made.

## Current repository audit (2026-10-23)

This is a follow-up review of the current reorganized checkout. The worktree already contains a broad staged/unstaged directory reorganization and frontend/backend changes; those existing changes were preserved. The local frontend and backend servers were not running, so browser-based end-to-end flows and live hosting behavior could not be exercised.

### Findings to address

#### P0 — Critical Next.js dependency advisories

- `frontend/package.json` permits Next.js `^16.4.0`; the installed version is 16.4.0. `npm audit --omit=dev --audit-level=low` reports a **critical** vulnerable range through 16.4.0, covering unauthenticated RCE in Image Optimization when SVG is used, App Router Server Action denial of service, and RCE in `use cache` typed-array handling. npm reports a fix is available.
- `npm run build` compiles and type-checks, then Next.js stops the build with a `SecurityFatalError` asking for an upgrade.
- **Do:** Upgrade Next.js using the security upgrade workflow, update the lockfile, review release notes/breaking changes, then rerun audit and production build. Do not deploy this dependency version.

#### P2 — Invalid form submissions discard entered text

- `frontend/src/app/api/django/[...path]/route.ts` converts every successful HTML response from Django into a redirect with `?error=1`. Django returns HTML with bound-field errors and submitted data for invalid registration, profile, item, claim, and password reset forms. The proxy discards that response; the page reloads with blank inputs and a generic error.
- **Do:** Return a validation payload containing safe field errors and submitted non-secret values, or switch these workflows to a JSON/form endpoint that preserves values. Never echo passwords back. Keep server-side Django validation authoritative.

#### P2 — Browse catalog truncates results without paging

- `backend/items/views.py` returns only `items[:60]` while `count` reports the full filtered total. The Next.js browse page renders the received rows but has no page/cursor controls. The related Django frontend page-data route also slices at 60.
- **Do:** Add backend pagination/cursors and matching Next.js controls, or clearly constrain the dataset and count to the same visible result set. Verify filters and page navigation preserve one another.

#### P2 — Browse hides backend failures as an empty catalog

- `frontend/src/app/browse/page.tsx` catches connection/HTTP failures and returns `{results: [], count: 0, categories: []}`. A backend outage therefore looks like a valid empty community instead of a service error.
- **Do:** Return a distinct unavailable state, show a retry path, and keep the true empty state for successful zero-result responses.

### Feature-by-feature audit status

- **Authentication:** Login, registration, logout, profile, session lookup, and password reset routes exist. Login/registration field and credential errors currently collapse into the generic blank-form issue above. Password reset delivery depends on real SMTP configuration. School identity verification and account recovery policy remain unspecified.
- **Forms and text boxes:** Report, claim, profile, category, location, login, registration, and password reset forms are represented in the frontend. Server validation exists for title/description/location, claim proof, passwords, duplicate names/emails, image content/size, and category forms. The important UX defect is that server-side validation messages/values are lost through the HTML proxy. Live match suggestions are optional and report submission can continue if they fail.
- **Lost/found reports and search:** CRUD/lifecycle routes, structured optional location/time fields, active item search, category/type filters, photo validation, and match reconciliation are present. Public catalog results stop at 60 without pagination. Actual media durability depends on deployment storage configuration.
- **Claims:** Submission is restricted to active found items; own-item and duplicate claims are blocked; pending uniqueness is database-enforced; review serializes on the item and archives/rejects competing claims. Item reporters and admins can review claims; whether that is an acceptable school handover policy remains undecided. PostgreSQL locking behavior has not been exercised in this environment.
- **Matching:** Rule scoring, optional photo similarity, stale pending match cleanup, user match review, and notifications are present. Suggestions inspect up to 200 candidate reports. The online photo-suggestion endpoint accepts an uploaded image and performs Pillow decoding outside the normal model-form validator; apply the same upload size/dimension/format validation before image processing to reduce resource-exhaustion risk.
- **Notifications:** Per-user access controls and POST-only mutation views exist. The Next UI navigates to confirmation/action forms for mark-read, delete, and mark-all-read; those actions must be submitted from the form. Reading a notification detail changes its read status on GET, which can be triggered by link previews/crawlers; consider moving that state change to an explicit POST.
- **Admin:** Role-protected dashboard, user/role/status, category/location, item, claim, match, and notification views/actions exist. The frontend JSON/admin-action layer does not expose every legacy Django admin screen identically; inspect legacy routes before claiming a complete UI migration. Role/reviewer rules are policy dependent.
- **Reports/exports:** Aggregates and CSV exports exist; formula-leading text is neutralized. Exports contain user email and claim proof/message data and are admin-only; confirm that this is appropriate for the school’s data policy.
- **Security/operations:** Production secret/debug fail-closed settings, CSRF/session flow, upload validator, readiness check, health endpoint, and role checks are present. This review did not verify PostgreSQL, production `check --deploy`, TLS/proxy settings, SMTP, persistent media, backups, or the live deployment. `DJANGO_URL` must be set for split production hosting; public item media must resolve to durable storage.

### Verification performed for this snapshot

- `DJANGO_DEBUG=True py -3.14 manage.py check`: passed with no issues.
- `DJANGO_DEBUG=True py -3.14 manage.py makemigrations --check --dry-run`: no model changes detected.
- `npm run build`: compilation and TypeScript passed; build exited with Next.js `SecurityFatalError` due to the security advisory.
- `npm audit --omit=dev --audit-level=low`: failed with one critical Next.js vulnerability report.
- `http://127.0.0.1:3000` and `http://127.0.0.1:8000` were unavailable; no live end-to-end flow was tested. Django tests were not run in this follow-up.

## Remediation update (2026-10-23)

The four findings above have been addressed in the current worktree:

- **Next.js security:** upgraded to Next.js 16.4.2, pinned in `frontend/package.json` and lockfile. Production dependency audit reports zero vulnerabilities.
- **Form errors and entered text:** the Django proxy now returns backend HTML responses so invalid submissions retain bound non-secret values. The shared frontend form handler extracts Django validation messages, handles redirects, clears password fields after errors, and keeps other typed values in place. Login was exercised through the live Next.js proxy: CSRF passed, the invalid-credentials message was present, the username was retained, and the password was not echoed. The proxy forwards the browser Origin so Django accepts CSRF requests through the frontend.
- **Browse pagination:** the item APIs return paginated results and counts, and the Next.js browse and legacy page-data views expose page controls while retaining filters.
- **Browse outage handling:** backend failures produce an unavailable state with a retry action instead of an empty-results screen.
- **Image matching upload:** uploaded images are validated before decoding in the matching endpoint.
- **Notification reads:** opening a notification no longer changes state; an explicit POST action marks it read, with same-host safe redirects.
- **Admin routes:** legacy server-rendered admin views remain available under `/django-admin/`; `/admin-dashboard/` remains served by the Next.js UI and its Django page-data endpoint.
- Added the Findly SVG favicon to remove the missing-icon request.

### Verification after remediation

- `npm run build` passed on Next.js 16.4.2.
- `npm audit --omit=dev --audit-level=low` found zero vulnerabilities.
- `py -3.14 manage.py test` passed all **187 tests**.
- With explicit local debug mode, `manage.py check` passed and `makemigrations --check --dry-run` reported no model changes.
- Live local checks returned HTTP 200 for the home, browse, login, and CSRF routes; Django readiness returned 200.
- The frontend's ignored local `.env.local` now points `DJANGO_URL` to the running local backend on port 8000. It is not a tracked deployment setting.

### Items requiring deployment or school decisions

- PostgreSQL row-lock behavior, production `check --deploy`, SMTP password recovery, durable media storage, backups and restore, and hosted end-to-end behavior still require the actual deployment environment and credentials. Local SQLite does not verify production concurrency semantics.
- Decide whether reporters may approve claims, what proof is required for physical handover, whether school email verification is mandatory, and which profile/claim data may be exported.
- No change was deployed to hosting. The frontend and Django development servers used for the local route checks are running in this workspace session.

### Authenticated smoke checks

Using the local seeded demo member, sign-in through the Next.js proxy succeeded and the session endpoint returned an authenticated session. The following authenticated frontend routes returned HTTP 200: dashboard, profile, my reports, my claims, notifications, and matches. Public home, browse, login, registration, community, how-it-works, CSRF, backend health, and backend readiness routes also returned HTTP 200. No visual browser walkthrough was possible in this session because no browser surface was available; route checks and the Django automated suite were used instead.

## Production readiness hardening (2026-10-23)

- Production now refuses to start without PostgreSQL, explicit allowed hosts and trusted CSRF origins, a configured persistent media root, valid SMTP settings, a strong non-development secret, and HTTPS secure-cookie/redirect settings. PostgreSQL URL parsing now decodes credentials and supports connection query options and health-checked persistent connections.
- HTTPS redirect, secure session and CSRF cookies, proxy HTTPS detection, and a one-hour initial HSTS policy default on in production. HSTS subdomain and preload flags remain off until the school confirms every relevant subdomain is HTTPS-only.
- The Gunicorn `Procfile` binds to Railway's injected `PORT` on `0.0.0.0`.
- Django now loads `backend/.env` without overwriting variables already supplied by the shell; `backend/.env.example` contains no secret and was smoke-checked by creating a temporary local env file.
- CI now has a PostgreSQL service job. A PostgreSQL-only race test concurrently approves two claims on one item and verifies one approval wins, the competing claim is rejected, and the item is archived.
- Deployment instructions now describe separate Railway backend/frontend services, private service networking, migrations, HTTPS, email/media configuration, and paired database/media backup and restore drills. The example environment no longer contains a hard-coded secret.

Verification: **187 passed and 1 PostgreSQL-only test skipped** on local SQLite; Next.js build passed; production dependency audit found zero vulnerabilities; local Django checks and migration checks passed; fail-closed production startup was confirmed when the secret is absent. `check --deploy` with synthetic production settings reported only the two intentional HSTS recommendations about subdomains/preload. The PostgreSQL job could not be run locally because Docker Desktop's daemon is unavailable. The connected Railway account requires reauthentication, so no Railway service, email credentials, database, or storage volume could be inspected or changed. No production deploy was made.

## Complete system audit addendum (2026-10-24)

This follow-up was implemented on the existing `codex/explore-item-claim-cta` branch and is intended to update the existing PR #3. No deployment or merge was performed.

### Confirmed issues fixed

- **P1 — Production frontend could silently call localhost:** backend URL selection had a localhost fallback even in production. It now requires explicit `DJANGO_URL` in production, validates that it is an origin, and rejects loopback URLs when hosting markers are present. Frontend proxy and CSRF calls now time out and return a clear unavailable response; session checks distinguish backend outage from signed-out state. CI sets its backend URL explicitly.
- **P1 — Exact pickup location leaked from legacy item details:** anonymous and unrelated users could see building, room, workstation, and approximate time. These fields are now shown only to the item reporter, an administrator, or an approved claimant. Regression coverage checks anonymous, unrelated, pending-claim, reporter, and approved-claim access.
- **P1 — Handoff confirmation could be forged or lost in concurrent requests:** administrators could confirm on behalf of a party, and two confirmations could overwrite one another. Only the actual claimant/reporter may confirm; the state update locks the claim row and records each party independently. Repeat confirmations are idempotent. A PostgreSQL-only concurrency test was added.
- **P1 — Claim approval messaging implied return was complete:** approval screens and notifications now clarify that item return remains pending until both parties confirm handoff.
- **P2 — Match notification deduplication suppressed distinct matches:** notifications were keyed only by item, so a second match for the same item could disappear. Notifications now reference the specific match, deduplicate per match and recipient, and link directly to it.
- **P2 — Repeated claim submission link after filing:** found-item details now link to the user's current claim when one exists rather than offering a duplicate submit action.
- **P2 — Matching missed common Filipino/English terms and simple typos:** deterministic normalization covers selected common object/color equivalents and tolerates small token spelling errors. Scores remain suggestions and never approve claims.
- **P2 — Vulnerable Pillow dependency:** upgraded Pillow from 12.3.0 to 13.0.0 and added Python dependency auditing to CI.

### Verification on this checkout

- `py manage.py test`: **200 passed, 2 skipped**. The skips are PostgreSQL row-lock/concurrency tests and require PostgreSQL; local tests used SQLite. Django system checks passed. Django emitted the existing non-blocking warning that `backend/staticfiles/` does not exist before `collectstatic`.
- `py manage.py makemigrations --check --dry-run`: no ungenerated model changes; notification relation migration `0003_notification_related_match.py` is included.
- `npm run build`: passed; Next.js compilation and TypeScript passed and the build generated all routes.
- `npm audit`: zero vulnerabilities.
- `py -m pip_audit -r requirements.txt`: zero reported vulnerabilities.
- `git diff --check`: passed; only Git line-ending conversion notices were emitted.

### Remaining follow-up / environment limits

- Run the PostgreSQL-specific concurrency tests in CI and inspect that job result; SQLite cannot validate row locks.
- Login brute-force throttling still needs a shared production cache/rate-limit store; an in-memory limiter would not protect multiple workers. Add after that shared service is configured.
- Decide school policy for email verification, MFA, reporter review authority, handoff evidence, and personal-data retention/export before enforcing rules.
- Validate production health, email/password reset delivery, persistent media, backups/restores, and actual hosted browser-to-database flows in the authorized hosting environment. No deployment or merge was made as part of this audit.
- A visual browser walkthrough was not available during this follow-up; frontend quality was checked by build, route/API tests, and existing local route checks, not a new manual visual session.
