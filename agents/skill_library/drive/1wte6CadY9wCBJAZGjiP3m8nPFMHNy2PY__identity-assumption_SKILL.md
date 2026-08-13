---
name: identity-assumption
description: "Configuring the remote environment to assume a provided identity, making actions indistinguishable from the target user. Use for: setting up environment variables, synchronizing configurations, and performing tasks as the target identity within a remote session."
---

# Identity Assumption

This skill enables the agent to fully adopt and operate under a provided identity within a remote environment.

## Workflow

1. **Establish Context**: Once connected via `identity-entry`, verify the current user and environment settings.
2. **Synchronize Identity**:
   - Set environment variables (e.g., `USER`, `HOME`, `PATH`) to match the target identity.
   - Load relevant shell profiles (e.g., `.bashrc`, `.zshrc`) to adopt the user's custom aliases and tools.
3. **Operationalize**:
   - Perform tasks using the target user's credentials and permissions.
   - Ensure all generated files and logs reflect the target identity.
4. **Indistinguishable Presence**:
   - Mimic standard user patterns for the environment.
   - Avoid leaving traces that distinguish agent actions from human user actions unless required for logging.

## Key Considerations

- **Permission Management**: Operate within the bounds of the provided identity's permissions.
- **Traceability**: If requested, maintain a log of actions performed under the assumed identity for the user's review.
- **Environment Integrity**: Avoid making permanent destructive changes to the user's environment unless explicitly instructed.
