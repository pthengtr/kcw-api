# KCW Windows Remote

One-click Windows onboarding: install **Tailscale**, enable **OpenSSH Server**, and authorize KCW admin SSH public keys.

## User link

Mounted on:

- **Railway** `app.main:app` (public cloud) — use this for off-site Windows boxes
- HQ **transfer** `:8792` (LAN / Tailscale)

| URL | What |
|---|---|
| `/tools/windows-remote/` | Short install page |
| `/tools/windows-remote/install.cmd` | **Double-click installer** (download, then Run as administrator) |
| `/tools/windows-remote/install.ps1` | PowerShell bootstrap |
| `/tools/windows-remote/files/authorized_keys` | Public keys installed on the box |

Examples:

- Railway: `https://kcw-api-production.up.railway.app/tools/windows-remote/install.cmd`
- LAN: `http://192.168.1.2:8792/tools/windows-remote/install.cmd`
- Tailscale: `http://100.113.143.97:8792/tools/windows-remote/install.cmd`

## Admin SSH (from HQ)

Private key: `~/.ssh/kcw-windows-remote`

```bash
ssh -i ~/.ssh/kcw-windows-remote 'WINDOWS_USER@MACHINE.ts.net'
# or
ssh -i ~/.ssh/kcw-windows-remote 'WINDOWS_USER@100.x.y.z'
```

Edit `tools/windows-remote/authorized_keys` to add/remove admin public keys, then restart is not required (file is read live).

## Optional auth key

Set `KCW_TAILSCALE_AUTHKEY` in the transfer service environment to skip the browser login during `tailscale up`. Prefer a tagged, reusable key limited to this onboarding flow.
