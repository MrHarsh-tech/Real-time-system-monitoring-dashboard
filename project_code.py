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
    def add_control_panel(self):
        """Enhanced control panel with more interactive elements."""
        # Use the dedicated controls axis, turn off its own ticks/spines
        ax_controls_area = self.axes['controls']
        ax_controls_area.axis('off')

        # Define relative positions for controls within the bottom area
        control_y_pos = 0.06 # Base Y position for buttons/inputs in figure coords
        slider_y_pos = 0.08 # Y position for slider in figure coords
        label_pad = 0.01

        # Pause/Resume button
        ax_pause = self.fig.add_axes([0.15, control_y_pos, 0.08, 0.05]) # Use fig.add_axes for precise placement
        self.pause_button = Button(
            ax_pause, 'Pause', color=COLORS['panel'], hovercolor=COLORS['accent'])
        self.pause_button.on_clicked(self.toggle_pause)
        self.pause_button.label.set_color(COLORS['text'])
        self.pause_button.label.set_fontweight('bold')


        # Update interval slider
        ax_slider = self.fig.add_axes([0.25, slider_y_pos, 0.18, 0.025]) # Adjusted position/size
        self.interval_slider = Slider(
            ax=ax_slider,
            label=' Interval (s):', # Shortened label
            valmin=1,
            valmax=10, # Reduced max interval for quicker testing if needed
            valinit=self.update_interval/1000,
            valstep=1,
            color=COLORS['accent'],
            track_color=COLORS['panel'],
            handle_style={'facecolor': COLORS['accent'], 'edgecolor': COLORS['text'], 'size': 10}
        )
        self.interval_slider.label.set_color(COLORS['text'])
        self.interval_slider.valtext.set_color(COLORS['text'])
        self.interval_slider.on_changed(self.update_interval_changed)

        # Network visibility toggle - CORRECTED
        ax_network_toggle = self.fig.add_axes([0.45, control_y_pos, 0.1, 0.05]) # Adjusted position
        self.network_toggle = CheckButtons(
            ax=ax_network_toggle,  # CORRECTED: Use the correct axis variable
            labels=[' Sent', ' Recv'], # Shortened labels
            actives=[self.show_network_sent, self.show_network_recv],
            label_props={'color': [COLORS['text']] * 2, 'fontsize': [9]*2},
            frame_props={'edgecolor': [COLORS['text']] * 2},
            check_props={'color': [COLORS['accent']] * 2}
        )
        self.network_toggle.on_clicked(self.toggle_network_visibility)


        # Threshold controls using TextBox
        self.threshold_inputs = {}
        threshold_base_x = 0.58
        threshold_width = 0.06
        threshold_spacing = 0.07
        positions = [
            # (metric, label, min_val, max_val, multiplier) - Multiplier for display/input units
            ('cpu', 'CPU%:', 5, 100, 1),
            ('memory', 'MEM%:', 5, 100, 1),
            ('disk', 'DISK%:', 5, 100, 1),
            ('network', 'NET(MB):', 0.1, 100, 1e6), # Input in MB
            ('process', 'PROC:', 10, 500, 1)
        ]

        for i, (metric, label, min_val, max_val, multiplier) in enumerate(positions):
            xpos = threshold_base_x + i * threshold_spacing
            ax_box = self.fig.add_axes([xpos, control_y_pos, threshold_width, 0.04])
            initial_val = self.thresholds[metric] / multiplier # Display in appropriate unit
            self.threshold_inputs[metric] = TextBox(
                ax_box, label, initial=f"{initial_val:.1f}" if metric=='network' else f"{int(initial_val)}",
                color=COLORS['panel'],
                hovercolor=COLORS['panel'],
                label_pad=label_pad # Adjusted padding
            )
            self.threshold_inputs[metric].label.set_color(COLORS['text'])
            self.threshold_inputs[metric].label.set_fontsize(9)
            self.threshold_inputs[metric].text_disp.set_color(COLORS['text'])
            # Use a nested function to capture metric and multiplier correctly in lambda
            def create_submit_handler(m, mult):
                return lambda text: self.update_threshold(m, text, mult)
            self.threshold_inputs[metric].on_submit(create_submit_handler(metric, multiplier))


    def add_status_bar(self):
        """Enhanced status bar using the controls axis."""
        ax = self.axes['controls']
        # Use figure coordinates for precise positioning at the very bottom
        status_y_pos = 0.015

        # Timestamp
        self.timestamp_text = self.fig.text(
            0.02, status_y_pos, # Position relative to figure
            datetime.now().strftime('Last Update: %Y-%m-%d %H:%M:%S'),
            color=COLORS['text'],
            fontsize=9,
            ha='left' # Horizontal alignment
        )

        # Status text
        self.status_text = self.fig.text(
            0.35, status_y_pos, # Position relative to figure
            'Status: [ACTIVE]',
            color=COLORS['success'],
            fontsize=9,
            fontweight='bold',
            ha='left'
        )

        # Uptime - CORRECTED
        self.uptime_text = self.fig.text(
            0.65, status_y_pos, # Position relative to figure
            f"Uptime: {time.strftime('%H:%M:%S', time.gmtime(time.time() - psutil.boot_time()))}", # CORRECTED: Added closing parenthesis
            color=COLORS['text'],
            fontsize=9,
            ha='left'
        )

        # Refresh rate indicator
        self.refresh_text = self.fig.text(
            0.85, status_y_pos, # Position relative to figure
            f"Refresh: {self.update_interval/1000:.1f}s",
            color=COLORS['accent'],
            fontsize=9,
            ha='left'
        )

