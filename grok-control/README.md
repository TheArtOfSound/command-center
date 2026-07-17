# Qira Grok Ops

A local ACP control plane for Grok Build, organized around Bryan Leonard's active Qira portfolio rather than a generic coding-chat interface.

## What the first version does

- Starts a real `grok agent stdio` process for the selected project.
- Performs the ACP `initialize`, authentication, and `session/new` handshake.
- Streams `session/update` events into a dedicated control-board UI.
- Displays agent messages, tool calls, terminal activity, completion state, errors, and raw protocol events.
- Implements ACP filesystem and terminal client capabilities.
- Restricts file and terminal working-directory access to the selected project root.
- Shows ACP permission requests in the UI and defaults to explicit approval.
- Injects project-specific objectives, traction, and non-negotiable operating rules into every task.
- Resolves projects from `~/Documents/GitHub`, environment-variable overrides, or folder candidates.

The initial registry prioritizes Ah Crap Cleanup, Qira Business Systems, WeSearch, Qira HQ, QEV/My Digital, LOLM/NFET, The Constructed Subject Argument, and AutoHustle. Secondary Qira products remain visible but are explicitly placed in maintenance tiers.

## Install Grok Build

```bash
curl -fsSL https://x.ai/cli/install.sh | bash
grok login
grok version
```

Use an API key instead of cached login when needed:

```bash
export XAI_API_KEY="xai-..."
```

## Run

From this directory:

```bash
chmod +x start.sh
./start.sh
```

Open manually:

```bash
open http://127.0.0.1:8787
```

## Workspace paths

The default workspace root is:

```text
~/Documents/GitHub
```

Override it globally:

```bash
export QIRA_WORKSPACE_ROOT="$HOME/path/to/repos"
./start.sh
```

Projects with uncertain or nonstandard local folder names support explicit environment variables, including:

```bash
export WESEARCH_PATH="$HOME/path/to/wesearch"
export QIRA_CONSULTING_PATH="$HOME/path/to/consulting"
export AH_CRAP_PATH="$HOME/path/to/ahcrapcleanup"
```

The complete mapping is in `projects.json`.

## Security model

This is intentionally a local application bound to `127.0.0.1` by default.

- Approval mode defaults to `ask`.
- `always approve` is available but should only be used on a clean branch or isolated worktree.
- ACP file reads and writes are confined to the selected project root.
- ACP terminal working directories are confined to the selected project root.
- The control plane does not store the xAI API key; Grok inherits the local login or `XAI_API_KEY` environment variable.
- Do not expose port `8787` publicly without adding authentication and transport security.

## Current limitations

- Sessions are in-memory and disappear when the local server stops. Grok's own session storage remains available under `~/.grok/sessions`.
- The UI does not yet include a Monaco diff editor, Git worktree creation, GitHub PR creation, deployment adapters, or persisted task queues.
- Terminal output is available to Grok through ACP; a dedicated live terminal panel is a next-phase feature.
- Project metrics are operating context, not automatically synchronized analytics.

## Next implementation layer

1. Persistent SQLite session/task/event ledger.
2. Git worktree isolation and branch controls.
3. Structured diff review before approval.
4. Deployment and health adapters for Cloudflare, DigitalOcean, GitHub, Stripe, and project-specific services.
5. Cross-project portfolio scheduler with explicit dependency and verification state.
6. Voice task input and mobile-safe approval flow.
