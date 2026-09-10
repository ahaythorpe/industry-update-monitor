# Dashboard

The web dashboard for the Industry Update Monitor. It reads the digest the
Python monitor writes to `lib/digest.json` — see the
[project README](../README.md) for the full workflow, guardrails and CLI.

```bash
cd ..                          # repo root
python src/monitor.py --json   # write lib/digest.json
cd web
npm install
npm run dev                    # http://localhost:3000
npm test                       # vitest
```

The digest is read on every request, so re-running the monitor shows up on the
next reload without a rebuild. Email, WhatsApp and AI stay off until they are
configured; `/api/status` reports what this deployment can actually do.
