# Cursor Cloud environment

This project targets Python 3.11 and uses the Supabase CLI for database
migrations. Run commands below from the repository root (`/workspace`).

## Python application checks

The expected virtual environment path is `/workspace/.venv`.

```bash
python3.11 -m venv /workspace/.venv
source /workspace/.venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Useful checks that do not need production credentials:

```bash
source /workspace/.venv/bin/activate
python -m pip check
python -m compileall -q app src
```

Importing `app.main` initializes the OpenAI and Supabase clients at import
time. For an import-only smoke check, use non-secret placeholders:

```bash
OPENAI_API_KEY="placeholder" \
SUPABASE_DB_URL="https://placeholder.supabase.co" \
SUPABASE_SERVICE_ROLE_KEY="placeholder" \
python -c "from app.main import app; print(app.title)"
```

Use real credentials only when exercising routes or jobs that call external
services.

## Supabase CLI

Verify the CLI is available:

```bash
supabase --version
```

If it is missing on a Linux x86_64 Cursor Cloud machine, install the latest
release binary:

```bash
SUPABASE_VERSION="$(
  curl -fsSL https://api.github.com/repos/supabase/cli/releases/latest |
  /workspace/.venv/bin/python -c "import json, sys; print(json.load(sys.stdin)['tag_name'])"
)"
TMPDIR="$(mktemp -d)"
curl -fsSL \
  "https://github.com/supabase/cli/releases/download/${SUPABASE_VERSION}/supabase_linux_amd64.tar.gz" \
  -o "${TMPDIR}/supabase_linux_amd64.tar.gz"
tar -xzf "${TMPDIR}/supabase_linux_amd64.tar.gz" -C "${TMPDIR}"
sudo install -m 0755 "${TMPDIR}/supabase" /usr/local/bin/supabase
rm -rf "${TMPDIR}"
supabase --version
```

The repository already contains `supabase/config.toml` and migration files in
`supabase/migrations/`.

## Supabase migration workflows

Local Supabase commands (`supabase start`, `supabase db reset`, and
`supabase migration list --local`) require Docker. Remote migration commands do
not require Docker, but they require a Supabase access token, project ref, and
database password.

Remote setup:

```bash
supabase login --token "$SUPABASE_ACCESS_TOKEN"
supabase link \
  --project-ref "$SUPABASE_PROJECT_REF" \
  --password "$SUPABASE_DB_PASSWORD"
```

Inspect or dry-run migrations before applying them:

```bash
supabase migration list --linked --password "$SUPABASE_DB_PASSWORD"
supabase db push --linked --dry-run --password "$SUPABASE_DB_PASSWORD"
```

Apply pending migrations:

```bash
supabase db push --linked --password "$SUPABASE_DB_PASSWORD"
```

The Supabase CLI stores link metadata under `supabase/.temp/`, which is ignored
by git. Do not commit access tokens, database passwords, `.env`, or any files
containing secret values.

## Required secret names

Configure these as Cursor environment secrets or local `.env` values as needed.
Do not commit real values.

### Supabase CLI migrations

- `SUPABASE_ACCESS_TOKEN` - personal access token for `supabase login --token`.
- `SUPABASE_PROJECT_REF` - target hosted Supabase project ref for `supabase link`.
- `SUPABASE_DB_PASSWORD` - hosted Postgres password used by `supabase link`,
  `supabase migration list`, and `supabase db push`.

### Application database and Supabase API

- `SUPABASE_DB_HOST`
- `SUPABASE_DB_PORT`
- `SUPABASE_DB_NAME`
- `SUPABASE_DB_USER`
- `SUPABASE_DB_PASSWORD`
- `SUPABASE_URL`
- `SUPABASE_DB_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_IMAGE_BUCKET`
- `SUPABASE_IMAGE_BASE_FOLDER`
- `SUPABASE_KB_SCHEMA`
- `SUPABASE_KB_RPC`
- `SUPABASE_KB_TABLE`
- `SUPABASE_KB_IMAGE_BUCKET`

### External services and runtime tuning

- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_EMBED_MODEL`
- `OPENAI_TIMEOUT_SECONDS`
- `AI_FORMAT_KB_ENABLED`
- `AI_FORMAT_KB_MODEL`
- `KB_MATCH_COUNT`
- `KB_AUTO_THRESHOLD`
- `KB_MIN_GAP`
- `KB_MAX_IMAGES`
- `WORKER_NAME`
- `WORKER_POLL_SECONDS`
- `HEARTBEAT_INTERVAL_SECONDS`
- `WORKER_COMMAND_TIMEOUT_SECONDS`
- `WORKER_RESULT_MAX_CHARS`
- `WORKER_JOB_<JOB_NAME>_ENABLED`
- `WORKER_JOB_<JOB_NAME>_COMMAND`
- `WORKER_JOB_<JOB_NAME>_CWD`
- `WORKER_JOB_<JOB_NAME>_TIMEOUT_SECONDS`
- `WORKER_JOB_<JOB_NAME>_SHELL`
