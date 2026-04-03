import os
import shutil
import tempfile
from pathlib import Path


TEST_DATA_DIR = Path(tempfile.gettempdir()) / "trading-bot-test-runtime"

shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
os.environ["TRADING_BOT_DATA_DIR"] = str(TEST_DATA_DIR)
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
