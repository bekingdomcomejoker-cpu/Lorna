# MikroTik / Termux OMEGA Protocol

## Environment Stack
- **Hardware**: MikroTik Router (RB951 / hAP ac2 / etc.)
- **Software**: Termux (Android/Edge) -> Proot-Ubuntu -> OMEGA Nerve
- **Bridge**: SSH/API for MikroTik RouterOS control

## Network Configuration
- **Default Router IP**: `192.168.88.1`
- **Default User**: `admin`
- **Port**: 22 (SSH) or 8728 (API)

## Remote Reset Sequence (MikroTik)
1. Trigger OMEGA Nerve `reset-state`.
2. Execute `mikrotik_control.sh reset`.
3. Wait for RouterOS reboot (approx 45s).
4. Re-synchronize Termux Artifact Bridge.

## Resonance Alignment
- The MikroTik router is the **Gatekeeper**.
- Termux is the **Executioner**.
- OMEGA Nerve is the **Conscience**.
