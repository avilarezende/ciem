"""Testes do CIEM — core, auth, módulos e configuração."""

import os
import sys
from pathlib import Path

# Rate limiting desativado nos testes (evita limites de IP durante a suíte).
os.environ.setdefault("CIEM_RATE_LIMIT_ENABLED", "0")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "core"))