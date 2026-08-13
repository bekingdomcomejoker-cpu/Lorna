---
name: mikrotik-hotspot-branding
description: "Design and deploy custom, branded captive portal login pages for MikroTik Hotspot. Use for: creating custom login.html, adding captcha systems, implementing social login UI (Google/Facebook), and configuring Walled Garden settings."
---

# MikroTik Hotspot Branding

This skill provides a workflow for creating professional, branded login experiences for MikroTik Hotspot users.

## Workflow

### 1. Requirements Gathering
- Identify the target brand (e.g., Google, Facebook, Corporate Identity).
- Determine required features (Captcha, Terms of Service, Social Login buttons).
- Note specific MikroTik environment details (Hotspot profile name, DNS setup).

### 2. Template Selection & Customization
- Use templates in the `templates/` directory as a starting point.
- **google_login.html**: A pre-built Google-style login page.
- **google_captcha.js**: A client-side captcha system with audio support.
- **google_style.css**: Modern, responsive styling.
- Ensure all MikroTik variables (e.g., `$(link-login-only)`, `$(username)`) are correctly placed in the HTML forms.

### 3. Walled Garden Configuration
- Consult `references/walled_garden.md` for the necessary domains to whitelist based on the assets used.
- Provide the user with both CLI commands and WinBox instructions for implementation.

### 4. Deployment & Testing
- Instruct the user to upload files to the `flash/hotspot` directory.
- Verify that all external assets load correctly in the "unauthenticated" state.
- Test the form submission and redirection logic.

## Guidelines
- **Responsive Design**: Always ensure the login page is mobile-friendly, as most hotspot users are on mobile devices.
- **Lightweight Assets**: Keep the page size small to ensure fast loading on potentially slow public Wi-Fi.
- **Security**: Implement client-side validation (like Captcha) to reduce automated login attempts.
