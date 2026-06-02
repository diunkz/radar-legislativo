"""
logger.py
---------
Configuração centralizada de logging.
Importe `log` em todos os módulos — nunca instancie um novo logger diretamente.
"""

import logging

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)