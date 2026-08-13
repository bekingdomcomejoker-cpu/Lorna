# Original Mission — CENSUS Engine

## Mission statement

CENSUS was originally intended as a population-scale civic intelligence and witness system for government/tender review. Its core purpose is to join witnessed records — names, dates, places, source files, incidents, household/service-delivery context, and timeline markers — into an auditable map of civic pressure, need, continuity, and risk.

The mission is **not** to steal data, secretly score citizens, or give any institution unreviewable power. The mission is to make hidden patterns visible in a way that can be audited, corrected, appealed, and used for service delivery, planning, and citizen self-knowledge.

## Original operating formula

```text
CENSUS gathers the field.
Discernment speaks the field.
Evidence grades the field.
The Bridge carries the same truth across scale without changing it.
```

## What CENSUS does

1. Ingests source records and preserves provenance.
2. Extracts event candidates.
3. Promotes records through a review ladder.
4. Separates canon, witness, repair, and private records.
5. Produces safe witness packets.
6. Shows what is known, inferred, weak, missing, or private.
7. Supports civic planning and voluntary pilot review.

## What CENSUS must not do

1. It must not become a secret citizen scoring system.
2. It must not automate adverse decisions.
3. It must not replace courts, social workers, elected officials, or human appeal.
4. It must not treat weak date/source/speaker fields as final truth.
5. It must not expose private data raw.
6. It must not turn witness material into coercive enforcement.

## Current completion state

The extraction loop closed at v5. The deployable prototype uses the redacted one-night closeout package:

- `canon_core`: strongest working canon.
- `source_filename_date_witness`: useful witness material, date not final.
- `date_repair_required`: repair queue.
- `unconfirmed_review`: weak/unconfirmed queue.
- private/sensitive records: sealed and not included raw.

