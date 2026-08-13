#!/usr/bin/env python3
"""
Omega Guardian Engine — Local/Public/Supplied Source Sensor

Reads supplied local sources and explicit public URLs, extracts metadata/events,
and writes Guardian sensor events into JSONL and ledger.db.
"""

from census_engine.guardian import main

if __name__ == "__main__":
    main()
