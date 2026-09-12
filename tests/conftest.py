# -*- coding: utf-8 -*-
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("BOT_TOKEN", "123:ABC")
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")
