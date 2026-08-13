# Audit of the Claude-produced scaffold

The pasted scaffold was useful as a project-tree sketch, but its claim that
everything was production-ready was unsupported.

## Defects corrected

1. **Claude-only routing**
   - Stage 4 forwarded only to an Anthropic proxy.
   - Replaced with provider-neutral federation routing.

2. **Missing Hearing channel**
   - The audit counted only sight, touch, smell and taste.
   - Five-Sense Witness now includes Hearing.

3. **Average-score false verification**
   - A missing ABCDE gate could be averaged away.
   - Hard-gate rules now cap or block the verdict.

4. **Unsupported 7^7 claim**
   - The scaffold equated `7^7 = 823,543` with a KJV word count without a
     defined edition, source hash, tokenization standard, headings policy or
     reproducible evidence.
   - The verifier now requires a local source, expected count and declared
     tokenization method.

5. **Invented shadow triggers**
   - Fixed references to a person/name, a "slowcooker" phrase and a date anchor
     were treated as universal distortions without source authority.
   - Replaced by configurable, disabled-by-default rules.

6. **Broken dependency declarations**
   - Source imported `@anthropic-ai/sdk`, but package metadata listed
     `anthropic`.
   - CLI used `commander` without declaring it.
   - `npm ci` was promised without guaranteed lockfiles.
   - SQLite database path handling was inconsistent.

7. **Not the original UI**
   - The frontend was explicitly simplified and omitted the Aletheia stage,
     escalation stage and source distinctions.

8. **No existing bridge integration**
   - It ignored `oroute`, local llama.cpp, the Sovereign Bus, CAT→EOF,
     Google Drive, Dropbox and Agent Mode.

9. **No proof**
   - No build logs, tests, live provider calls or reproducible artifact were
     supplied.

## Preserved ideas

- one shared local ledger;
- a browser control panel;
- CLI access;
- inventory and voice audits;
- final packet/export;
- optional container packaging.
