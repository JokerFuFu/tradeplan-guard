#!/usr/bin/env python3
"""Project entrypoint; the independently installable Skill owns the runtime."""
import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SCRIPTS=ROOT/'skills/okx-tradeplan-guard/scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('tradeplan_bot_entry',SCRIPTS/'bot.py')
entry=importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)

if __name__=='__main__':
    sys.exit(entry.main(default_db=ROOT/'data/paper.sqlite3'))
