"""
Скрипт с тестированием функционала анлиза и визуализации зон на sample-данных
"""

from pathlib import Path
from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.analysis.zones.pipeline import analyze_zones
from bquant.visualization import (
    ZoneVisualizer,
    plot_zone_detail,
    plot_zones_comparison,
)


# -----------------------------------------------------------------------------
# Output directory for saved figures
# -----------------------------------------------------------------------------
# Output directory for saved figures
# -----------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).parent / "outputs" / "visualization"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Quiet logging for notebook/demo usage
# -----------------------------------------------------------------------------
# Консоль — тихая (ERROR), базовые сообщения NotebookSimulator остаются видимыми.
setup_logging(profile='clean', exceptions={'bquant.core.nb': 'INFO'})

# -----------------------------------------------------------------------------
# Image saving flag (default: False for faster test runs)
# -----------------------------------------------------------------------------
SAVE_IMAGES = False


# -----------------------------------------------------------------------------
# Saving configuration
# -----------------------------------------------------------------------------
# Options:
#   - "html": always save Plotly as HTML (no external deps), Matplotlib as PNG
#   - "png":  try to save Plotly as PNG (requires kaleido); on failure fallback to HTML
#              Matplotlib remains PNG
SAVE_IMAGE_FORMAT = "png"  # set to "png" to prefer PNG (Plotly falls back to HTML if unavailable)

