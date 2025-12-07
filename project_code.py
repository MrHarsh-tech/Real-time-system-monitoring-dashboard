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
class SystemMonitorDashboard:
    def _init_(self):
        """Initialize dashboard with default settings."""
        self.thresholds = {
            'cpu': 80,
            'memory': 80,
            'disk': 80,
            'network': 1000000,  # Threshold in bytes (1MB)
            'process': 200
        }
        self.update_interval = 2000  # Start with 2s updates
        self.max_data_points = 15
        self.alerts = []
        self.alert_history = []
        self.metrics_history = {
            'time': [],
            'cpu': [],
            'memory': [],
            'disk': [],
            'network_sent': [],
            'network_recv': [],
            'process': []
        }
        self.animation = None
        self.paused = False
        self.show_network_sent = True
        self.show_network_recv = True

        self.create_dashboard()
        logging.info("Dashboard initialized")

    def create_dashboard(self):
        """Create the dashboard layout with enhanced UI elements."""
        self.fig = plt.figure(figsize=(18, 12), facecolor=COLORS['background'])
        self.fig.suptitle(
            'ADVANCED SYSTEM MONITORING DASHBOARD',
            fontsize=22,
            color=COLORS['accent'],
            y=0.98,
            fontweight='bold',
            path_effects=[path_effects.withStroke(linewidth=2, foreground='black')]
        )

        # Main grid layout with better spacing
        self.gs = GridSpec(4, 3, figure=self.fig,
                           left=0.07, right=0.93,
                           bottom=0.15, top=0.92,  # Adjusted bottom slightly for controls
                           hspace=0.7, wspace=0.4)

        # Create subplots with improved layout
        self.axes = {
            'cpu': self.fig.add_subplot(self.gs[0, 0], facecolor=COLORS['panel']),
            'memory': self.fig.add_subplot(self.gs[0, 1], facecolor=COLORS['panel']),
            'disk': self.fig.add_subplot(self.gs[1, 0], facecolor=COLORS['panel']),
            'network': self.fig.add_subplot(self.gs[1, 1], facecolor=COLORS['panel']),
            'process': self.fig.add_subplot(self.gs[2, 0], facecolor=COLORS['panel']),
            'alert': self.fig.add_subplot(self.gs[2, 1], facecolor=COLORS['panel']),
            'summary': self.fig.add_subplot(self.gs[0:2, 2], facecolor=COLORS['panel']),
            'controls': self.fig.add_subplot(self.gs[3, :], facecolor=COLORS['background'])
        }

        # Configure plots with better styling
        self.configure_plot(self.axes['cpu'], 'CPU USAGE (%)', COLORS['cpu'])
        self.configure_plot(self.axes['memory'], 'MEMORY USAGE (%)', COLORS['memory'])
        self.configure_plot(self.axes['disk'], 'DISK USAGE (%)', COLORS['disk'])
        self.configure_plot(self.axes['network'], 'NETWORK TRAFFIC (MB)', COLORS['network'])
        self.configure_plot(self.axes['process'], 'ACTIVE PROCESSES', COLORS['process'])

        # Alert panel setup
        self.axes['alert'].set_title('ALERTS', color=COLORS['alert'], pad=10, fontsize=12, fontweight='bold')
        self.axes['alert'].axis('off')
        self.alert_texts = []

        # Summary panel setup
        self.axes['summary'].set_title('SYSTEM SUMMARY', color=COLORS['accent'], pad=10, fontsize=12, fontweight='bold')
        self.axes['summary'].axis('off')

        # Add enhanced controls and status bar
        self.add_control_panel()
        self.add_status_bar()

        # Initial data collection to populate plots before animation starts
        self.update_dashboard(0)
        logging.info("Dashboard UI created")

    def configure_plot(self, ax, title, color):
        """Enhanced plot styling with better visuals."""
        ax.clear()
        ax.set_title(title, color=color, pad=12, fontsize=12, fontweight='bold')
        ax.set_xlabel('Time', color=COLORS['text'], fontsize=10)
        ax.set_ylabel(title.split(' (')[0], color=COLORS['text'], fontsize=10)
        ax.tick_params(colors=COLORS['text'], labelsize=9)
        ax.grid(True, alpha=0.2, linestyle='--')
        ax.set_facecolor(COLORS['panel'])

        # Rotate x-labels and limit ticks for better readability
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
        ax.xaxis.set_major_locator(plt.MaxNLocator(6))
        ax.yaxis.set_major_locator(plt.MaxNLocator(5))

        # Border styling
        for spine in ax.spines.values():
            spine.set_color(color)
            spine.set_linewidth(1.5) # Slightly thinner border
