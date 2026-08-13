---
name: identity-entry
description: "Automated establishment of remote desktop sessions using provided identity credentials and access codes. Use for: connecting to remote computers via Google Remote Desktop, extracting access codes from images or text, and initiating secure remote sessions."
---

# Identity Entry

This skill provides a workflow for establishing a remote connection to a target computer while adopting a provided identity.

## Workflow

1. **Identify the Target**: Obtain the remote desktop URL and the required identity credentials (e.g., Google account email).
2. **Extract the Access Code**: 
   - If the user provides an image, use multimodal analysis to extract the 12-digit access code (formatted as XXXX XXXX XXXX).
   - If the user provides text, extract the code directly.
3. **Navigate to Remote Support**:
   - Open the browser and navigate to `https://remotedesktop.google.com/support`.
   - Ensure the browser is signed in with the target identity.
4. **Initiate Connection**:
   - Locate the "Connect to another computer" section.
   - Enter the 12-digit access code into the "Access code" field.
   - Click "Connect" and wait for the session to establish.
5. **Verification**: Confirm successful connection by observing the remote desktop environment.

## Key Considerations

- **Credit Efficiency**: Prioritize direct shell commands once inside the remote session to minimize credit usage.
- **Security**: If account verification is required, prompt the user to take over the browser or provide necessary verification details securely.
- **Persistence**: Maintain the session active for as long as required to complete the assigned tasks.
