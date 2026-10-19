"""一次性 CLI 出口检查,跑完即删。"""
import subprocess
import sys
import tempfile
from pathlib import Path

text = Path(__file__).with_name("test_validate.py").read_text(encoding="utf-8")
start = text.index('MINIMAL = """') + len('MINIMAL = """')
body = text[start : text.index('"""', start)]
badge = (
    "[![GitHub stars](https://img.shields.io/github/stars/acme/demo?style=social)]"
    "(https://github.com/acme/demo)\n\n"
)
body = body.replace(badge, "")
path = Path(tempfile.gettempdir()) / "gru-warn-only.md"
path.write_text(body, encoding="utf-8")
root = Path(__file__).resolve().parents[2]
proc = subprocess.run(
    [sys.executable, str(root / "scripts" / "validate.py"), str(path), "--type", "cli"],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
path.unlink(missing_ok=True)
sys.stdout.write(proc.stdout)
print("WARN_ONLY_EXIT", proc.returncode)
raise SystemExit(0 if proc.returncode == 3 else 1)
