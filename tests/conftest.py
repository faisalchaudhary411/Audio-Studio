"""
conftest.py — runs before any test module is imported. This is what makes
running the test suite safe: persistence.py reads DB_PATH from the
environment ONCE, at import time, so this has to set it before anything
else in the app gets imported, or tests would silently read/write the
REAL production database.

Also sets a throwaway SECRET_KEY, since app.py refuses to start at all
without one (see app.py's HARDENING comment on that) — tests that touch
app.py need this set before that import happens too.
"""
import os
import sys
import tempfile

_test_dir = tempfile.mkdtemp(prefix="voxcraft_test_")
os.environ["DB_PATH"] = os.path.join(_test_dir, "test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use")

# So `import persistence` etc. resolve correctly regardless of which
# directory pytest is invoked from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
