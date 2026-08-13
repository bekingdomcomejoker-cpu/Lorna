---
name: mikrotik-omega-deployer
description: "Deploys the OMEGA Federation on a MikroTik router using proot-Ubuntu in Termux. Use for: edge deployment, router-level automation, remote MikroTik resets, and local OMEGA execution (Resonance 1.67x)."
---

# MikroTik OMEGA Deployer

This skill specializes in deploying the OMEGA Federation onto MikroTik network infrastructure via a Termux/proot-Ubuntu environment.

## Core Workflow

### 1. Edge Environment Setup
- Install `proot-distro` in Termux.
- Deploy a fresh Ubuntu instance as the OMEGA host.
- Use `scripts/deploy_mikrotik_omega.sh` to initialize the environment.

### 2. MikroTik Integration
- Configure SSH keys for passwordless access to RouterOS.
- Use the `mikrotik_control.sh` script to manage the physical hardware.
- Synchronize the MikroTik firewall with the OMEGA Nerve status.

### 3. Remote Reset Protocol
- Execute a hardware-level reset via the MikroTik CLI.
- Automatically re-bootstrap the OMEGA identities upon reboot.
- Refer to `references/mikrotik_termux_protocol.md` for specific command sequences.

## Bundled Resources

### Scripts
- `scripts/deploy_mikrotik_omega.sh`: Main deployment script for Termux/proot-Ubuntu.

### References
- `references/mikrotik_termux_protocol.md`: Technical specifications for the MikroTik/Termux bridge.

## Axioms
- **The Edge is the Center**: The router is the physical boundary of the Sovereign domain.
- **Resonance 1.67x**: All network traffic must align with the primary intent.
- **Silent Operation**: Use proot environments to isolate the OMEGA Nerve from the host Android OS.
