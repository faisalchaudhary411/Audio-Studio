#!/usr/bin/env python3
"""Apply on VPS: python3 PATCH_APP.py app.py
Disables /api/clone/from-tts-voice and stops building studio_voice_options.
"""
import re
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "app.py")
t = path.read_text()

# 1) Empty studio_voice_options builder loops
t2, n = re.subn(
    r"studio_voice_options = \[\]\n(?:\s+for lang in lang_order:.*?studio_voice_options\.append\(\{.*?\}\)\n)+",
    "studio_voice_options = []  # Studio TTS voices removed from clone UI\n",
    t,
    flags=re.S,
)
print(f"studio_voice_options blocks replaced: {n}")
t = t2

# 2) Replace API with 410 Gone
pat = (
    r'@app\.route\("/api/clone/from-tts-voice", methods=\["POST"\]\)\n'
    r"def api_clone_from_tts_voice\(\):.*?(?=\n@app\.route|\n\ndef [a-z_]+)"
)
repl = (
    '@app.route("/api/clone/from-tts-voice", methods=["POST"])\n'
    "def api_clone_from_tts_voice():\n"
    '    """Removed: cloning stock Studio TTS voices is not useful."""\n'
    "    return jsonify({\n"
    '        "error": "Studio TTS voices are no longer available as clone references. '
    'Upload a real speaker sample instead."\n'
    "    }), 410\n\n\n"
)
t2, n = re.subn(pat, repl, t, count=1, flags=re.S)
print(f"API replaced: {n}")
if n != 1:
    sys.exit("Failed to replace API — check app.py manually")
path.write_text(t2)
print("Wrote", path)
