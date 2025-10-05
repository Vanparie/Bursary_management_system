## 📅 2025-09-12

### ✅ Work Done
- Implemented signup logic with mock verification for ID/NEMIS.
- Updated login form to allow "National ID / NEMIS number" + password.
- Added UpgradeToID view so students can switch from NEMIS login to ID login when they get IDs.

### ❌ Issues / Challenges
- Confusion about whether both NEMIS and ID should be stored.
- Concern about duplicate logins if both are allowed.

### 💡 Decisions / Rationale
- Students start with NEMIS (if minors).
- They can upgrade to ID later (unique, stronger identifier).
- Username field = whichever credential they use (not both).

### 🔜 Next Steps
- Test system functionality with mock verification API.
- Write migrations for new model changes.
- Add success message after signup (no auto-login).

### 📝 Notes / Ideas
- Consider adding officer-level view to track student login attempts.
- Later: replace mock verification with real API once integrated.
