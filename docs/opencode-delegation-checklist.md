# OpenCode delegation checklist (Cursor → Spark)

Cursor must fill **every section** before `opencode run`. If any section is blank, do not delegate — finish in Cursor or ask the user.

## 1. Domain lock (first 10 lines — non-negotiable)

```
PROJECT: <repo + service name>
DOMAIN: <one sentence — what this IS>
NOT THIS: <bullet list of common wrong interpretations>
THAI TERMS: <exact operator words; what they mean here>
COMMANDS: <exact LINE command strings>
```

Example (kcw-transfer):

```
DOMAIN: HQ↔SYP inventory stock transfer (โอนสินค้า between branches)
NOT THIS:
  - bank transfer / โอนเงิน / send money
  - pay-notes AP / PVMAS
  - generic HTTP "transfer" encoding
COMMANDS: โอนสินค้า, โอน, transfer (stock only)
```

## 2. Scope fence

- **IN:** numbered file list + one phase only
- **OUT:** explicit FORBIDDEN list (files not to create, features not to implement)
- **Reference files:** paths Spark must read before writing (copy patterns from these)

## 3. Acceptance gate

```bash
cd <project-root> && .venv/bin/python -m pytest <exact test paths> -q
```

Spark must not report success until this exits 0. Cursor re-runs the same command after Spark finishes.

## 4. Cursor review (always)

After Spark exits 0, Cursor must verify:

- [ ] No forbidden files created
- [ ] Domain terms match (grep for wrong words, e.g. `โอนเงิน` in transfer code)
- [ ] API signatures match existing patterns (`get_site_engine("syp")` not invented args)
- [ ] PARTS9 column names match kcw-docs dictionaries (`ICLOW.ID` not `ICLOW_ID`)
- [ ] Integration wired (router, env flags, docs)

## 5. When NOT to delegate

- Architecture / first implementation of a new service shell
- UI/UX polish (wife-test quality)
- Security-sensitive writer grants
- Anything where the plan still has open Phase 0 discovery

Delegate: bulk codegen **after** pattern exists, scoped phase, mocked tests, clear copy-from files.
