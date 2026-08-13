# Aletheia Perception Integrity Console — Termux

This package joins the four Glass-Chess phases into one practical console:

1. repository completeness and canary auditing;
2. Five-Sense witness packets;
3. Plain-Sight semantic-outsider ranking;
4. conservative voice correction.

It also adds the ABCDE judgment layer, an Unknown Ledger, JSON reports,
JSONL history, and a SQLite evidence ledger.

## Install in Termux

Download and extract the ZIP inside Android Downloads. Shared storage is
normally mounted `noexec`, so invoke the installer through Bash:

```bash
cd ~/storage/downloads
unzip -o ALETHEIA_PERCEPTION_INTEGRITY_CONSOLE_TERMUX.zip
cd aletheia-perception-integrity-console-termux
bash install-termux.sh
```

The package installs into `~/cat_eof` and does not use `/tmp` or `nano`.

## Confirm the installation

```bash
~/cat_eof/tools/aletheia-console status
~/cat_eof/tools/aletheia-console demo
```

The demonstration must report:

```text
Inventory omission: bekingdomcomejoker-cpu/glass-chess
Voice correction:   Manuscriptly -> Node 4 / Manus
Claim decision:     ALLOW
Verification:        PASSED
```

## Interactive claim audit

```bash
~/cat_eof/tools/aletheia-console wizard
```

## Direct claim audit

```bash
~/cat_eof/tools/aletheia-console claim \
  --claim "glass-chess belongs to the canonical repository estate" \
  --subject "bekingdomcomejoker-cpu/glass-chess" \
  --source "authoritative export" \
  --sight "visible in canonical list" \
  --touch "raw inventory inspected" \
  --smell "120 versus 119 mismatch" \
  --taste "two-way set comparison closed" \
  --a pass --b pass --c pass --d pass --e not_applicable
```

## Voice correction

```bash
~/cat_eof/tools/aletheia-console voice "Manuscriptly"
```

Unknown phrases are held for operator correction. They never create a new
entity automatically.

## Inventory audit

```bash
~/cat_eof/tools/aletheia-console inventory \
  --canonical ~/cat_eof/input/repos-canonical.txt \
  --observed ~/cat_eof/input/repos-observed.txt \
  --owner bekingdomcomejoker-cpu \
  --canary glass-chess \
  --fail-on-gap
```

A gap exit code of `1` means the fail-closed gate worked.

## Records

```text
~/cat_eof/state/cat_eof.db
~/cat_eof/state/perception_integrity.jsonl
~/cat_eof/output/perception_integrity/
```

## Governing rule

> Perceive through many channels. Preserve the exact signal. Declare the
> field boundary. Seek the semantic outsider. Measure the unresolved
> remainder. Let no sense certify itself. Move only when ABCD agrees.
