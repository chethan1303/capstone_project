# Application security and admin enhancements

## Implementation checklist

- [x] Improve registration and login validation: normalize identifiers, validate email and username, enforce bcrypt's 72-byte password limit, and reject malformed token subjects.
- [x] Fix session/history ownership: prevent access to foreign, hidden, and legacy unowned sessions; return 404 for inaccessible history; avoid creating sessions during history reads; handle simultaneous session creation.
- [x] Create a first-admin bootstrap: validate inputs, allow only one bootstrap, and reserve bootstrap atomically; later accounts remain managed through the authenticated admin API.
- [x] Add admin conversation filters: filter by status, risk level, and escaped case-insensitive session ID search.
- [x] Add Chart.js admin visualizations for risk and conversation-status distributions.
- [x] Add backend automated tests for auth validation, ownership, admin filters/bootstrap, and dataset labels.
- [x] Add a synthetic labeled prompt-injection evaluation dataset and document its labels and intended use.

## Verification

From `backend`, run `python -m unittest discover -s tests -v`. From `frontend`, run `npm run lint` and `npm run build`.

Bootstrap the initial admin interactively from `backend` with `python create_admin.py`. The command refuses to run again after successful bootstrap.

## ML/NLP evaluation checklist

- [x] Add a TF-IDF word n-gram and logistic-regression prompt-injection classifier.
- [x] Compare the existing rule/heuristic detector baseline with a detection-only classifier in stratified cross-validation.
- [x] Report accuracy, precision, recall, F1, FPR, inference and fit latency, and detector pass-through rate.
- [x] Support optional human-adjudicated end-to-end injection outcomes; report actual injection success as unavailable until those outcomes are supplied.
- [x] Expand the synthetic dataset to balanced classes and document the evaluation limitations.

## Admin role and account management checklist

- [x] Move account creation, listing, role updates, and status changes into a dedicated admin roles router.
- [x] Extract the admin account controls into a dedicated frontend component.
- [x] Add reversible account deactivation while preserving conversation history.
- [x] Block login and existing-token use for deactivated accounts; let administrators reactivate accounts.
- [x] Prevent self-deactivation and demotion/deactivation of the last active administrator, including older account records without an `is_active` field.
- [x] Add backend regression tests for role protections, deactivation, reactivation, and router registration.
- [x] Give user management its own admin route and sidebar navigation item, separate from the dashboard.
