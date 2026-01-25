import sys
import os
from pathlib import Path

# Add legacy tools to path for tests that haven't been refactored yet
legacy_tools_path = str(Path(__file__).parent.parent.parent / "src" / "tools" / "legacy")
if legacy_tools_path not in sys.path:
    sys.path.insert(0, legacy_tools_path)
