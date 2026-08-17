# eaubbies/eaubbies/src/tests/conftest.py
"""Shared pytest fixtures / environment setup.

Several modules (``service``, ``app``) instantiate a :class:`YamlConfigLoader`
at import time, which by default targets ``/config`` (only writable inside the
container). To keep the suite runnable on a developer host and in CI, we point
the config + frames paths at a temporary directory *before* those modules are
imported by any test.
"""

import os
import tempfile

# Create a throwaway config root for the whole test session and expose it via
# the same environment variables the configuration loader reads. This must run
# at import time (module top-level) so it is set before any test imports the
# app/service modules.
_TEST_ROOT = tempfile.mkdtemp(prefix="eaubbies-tests-")
os.environ.setdefault("CONFIG_PATH", _TEST_ROOT)
os.environ.setdefault(
    "DEFAULT_CONFIG_FILE", os.path.join(_TEST_ROOT, "eaubbies", "main.yaml")
)
os.environ.setdefault(
    "DEFAULT_FRAMES_PATH", os.path.join(_TEST_ROOT, "eaubbies", "img", "frames")
)
# Skip app.py runtime initialisation (frames dir + cron registration) on
# import so importing the module in tests has no external side effects.
os.environ.setdefault("EAUBBIES_SKIP_INIT", "1")
