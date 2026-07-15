# Direct Linux Access

QuoteOps development can be reached in two independent ways:

- Windows/Codex Desktop -> SSH to the Linux host.
- Mobile SSH client -> directly to the Linux host, without Windows or Codex Desktop.

## LAN Hosts

| Host | Address | SSH | Codex CLI | tmux | Status |
|---|---|---:|---:|---:|---|
| RalphiIA main | `192.168.1.4` | 22 | `0.130.0`, ChatGPT login active | 3.4 | Ready for direct LAN SSH |
| RalphiIA AMD | `192.168.1.5` | 22 | Not installed | 3.6 | SSH ready; CLI bootstrap blocked by missing Node/npm and sudo auth |

## Mobile Connection

Use Termius, ConnectBot, Blink or an equivalent SSH client. Create two hosts:

```text
Host: 192.168.1.4
User: rlopez
Port: 22

Host: 192.168.1.5
User: rlopez
Port: 22
```

Prefer an SSH key stored in the mobile client. Do not enable password/root login for convenience.

## Persistent Coding Sessions

On the main server:

```bash
ssh rlopez@192.168.1.4
tmux new -As codex-ralfia
cd /home/rlopez/projects/ralphiia-quoteops
codex
```

On the AMD server after Codex CLI is installed:

```bash
ssh rlopez@192.168.1.5
tmux new -As codex-amd
cd /home/rlopez/projects
codex
```

Detach with `Ctrl-b`, then `d`; reconnect later with `tmux attach -t codex-ralfia` or `tmux attach -t codex-amd`.

## Current Blockers

- `192.168.1.5` has no Node.js/npm, so the official Codex CLI cannot be bootstrapped with the normal package flow yet.
- `sudo -n` requires authentication on both hosts; Rafael must authorize the system package installation or complete it interactively.
- No Tailscale client is currently detected. Direct access currently works on the local network; remote access from outside the LAN requires an approved VPN such as Tailscale or an existing secure network path.

Production services were not modified by this audit.
