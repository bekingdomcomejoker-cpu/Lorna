---
name: identity-assumption
description: "Configuring the remote environment to assume a provided identity, making actions indistinguishable from the target user. Optimized for multi-plural Termux environments with cross-device synchronization. Use for: setting up environment variables, managing SSH/Git identities, and synchronizing configurations across Android devices."
---

# Identity Assumption: Termux Multi-Identity Edition

This skill transforms a standard single-user Termux environment into a **multi-plural identity system**. It allows you to switch between different personas (e.g., Work, Personal, Open Source) and keep them synchronized across all your Android devices.

## Core Concepts

### 1. Identity Packs
An identity is a self-contained directory in `~/.termux_profiles/` containing:
- **`env.sh`**: Shell variables and API keys.
- **`.gitconfig`**: Identity-specific Git settings.
- **`ssh/`**: Private/public keys unique to this persona.

### 2. The Switcher Tool (`tp-switch`)
A dedicated script to manage these identities. For environment variables to persist in your current session, use `source tp-switch activate <name>`.

## Enhanced Workflow

### Phase 1: Identity Setup
Create distinct profiles for your different roles:
```bash
tp-switch create developer
tp-switch create personal
```

### Phase 2: Persona Activation
Switching an identity updates your Git config, SSH keys, and shell prompt instantly:
```bash
tp-switch activate developer
```

### Phase 3: Global Synchronization
The `sync` command leverages Git to ensure every Android device you own has the same identity set:
```bash
tp-switch sync
```

## Implementation Strategy for Users

1. **Install**: Copy the `tp-switch` script to your `~/bin` folder.
2. **Bootstrap Sync**:
   - Create a private repository on GitHub/GitLab.
   - Run `tp-switch sync` for the first time.
   - Add your private repo as the origin: `cd ~/.termux_profiles && git remote add origin <url>`.
3. **Daily Use**: Use `tp-switch activate` whenever you start a new project or context.

## Best Practices
- **Security**: Never push your `~/.termux_profiles` to a public repository. Always use a private repo or a local network sync like Syncthing.
- **SSH Persistence**: The script copies keys to `~/.ssh`. Ensure you have appropriate permissions (`chmod 700 ~/.ssh`).
- **Automation**: Add `source tp-switch activate default` to your `.bashrc` or `.zshrc` to ensure a consistent starting point.
