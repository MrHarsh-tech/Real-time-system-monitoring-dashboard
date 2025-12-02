# SECTION 1 — File Header + Imports + Config
#!/usr/bin/env python3
"""
enhanced_monitor_singlefile.py

Single-file real-time system monitor (matplotlib UI).
Features:
- CPU, Memory, Disk usage (live charts)
- Network Sent/Recv RATE in MB/s (delta-based)
- Live alerts with threshold settings
- Pause/Resume functionality
- Update interval slider
- Network show/hide toggles
- Simple, dependency-light implementation for CA2 project

Requirements:
    pip install psutil matplotlib numpy
"""

import psutil
import time
import logging
from datetime import datetime
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, Slider, CheckButtons, TextBox
import numpy as np

# ---------- Configuration / Defaults ----------
MAX_POINTS = 60                # number of data points to show on the charts
DEFAULT_INTERVAL_MS = 1000     # update interval (in milliseconds)

# UI color palette
COLORS = {
    'bg': '#0f1724',
    'panel': '#0b1220',
    'text': '#dbeafe',
    'cpu': '#f97316',
    'mem': '#10b981',
    'disk': '#60a5fa',
    'network': '#f472b6',
    'accent': '#60a5fa',
    'threshold': '#fb923c',
    'alert_bg': '#1f2937'
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
