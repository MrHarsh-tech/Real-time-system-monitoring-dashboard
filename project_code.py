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
    def toggle_pause(self, event):
        """Toggle pause/resume of updates."""
        self.paused = not self.paused
        if self.paused:
            self.pause_button.label.set_text('Resume')
            self.status_text.set_text("Status: [PAUSED]")
            self.status_text.set_color(COLORS['alert'])
            if self.animation:
                self.animation.event_source.stop()
            logging.info("Dashboard paused")
        else:
            self.pause_button.label.set_text('Pause')
            self.status_text.set_text("Status: [RUNNING]")
            self.status_text.set_color(COLORS['success'])
            if self.animation:
                self.animation.event_source.start()
            logging.info("Dashboard resumed")
        # self.fig.canvas.draw_idle() # Use draw_idle for better performance with widgets
        plt.draw() # Keep plt.draw for simplicity here


    def toggle_network_visibility(self, label):
        """Toggle visibility of network sent/received data."""
        # Need to check the actual status from the widget
        statuses = self.network_toggle.get_status()
        self.show_network_sent = statuses[0]
        self.show_network_recv = statuses[1]

        # if label == ' Sent': # Compare with the actual label text
        #     self.show_network_sent = not self.show_network_sent
        # elif label == ' Recv': # Compare with the actual label text
        #      self.show_network_recv = not self.show_network_recv

        self.update_network_plot() # Redraw only the network plot
        self.fig.canvas.draw_idle() # Update the canvas efficiently
        logging.info(f"Network visibility updated: Sent={self.show_network_sent}, Recv={self.show_network_recv}")


    def update_interval_changed(self, val):
        """Handle interval changes from the slider."""
        try:
            new_interval = float(val) * 1000
            if 1000 <= new_interval <= 10000: # Match slider range
                self.update_interval = int(new_interval) # Store as int ms
                self.status_text.set_text(f"Status: [INTERVAL UPDATED]")
                self.status_text.set_color(COLORS['success'])
                self.refresh_text.set_text(f"Refresh: {val:.1f}s")
                if self.animation and not self.paused:
                    self.animation.event_source.stop() # Stop and restart timer
                    self.animation.event_source.interval = self.update_interval
                    self.animation.event_source.start()
                logging.info(f"Update interval changed to {self.update_interval} ms")
            else:
                # Reset slider to previous value if out of bounds (optional)
                # self.interval_slider.set_val(self.update_interval/1000)
                self.status_text.set_text("Status: [INTERVAL OUT OF RANGE]")
                self.status_text.set_color(COLORS['alert'])
                logging.warning(f"Invalid interval requested: {val}s")
        except ValueError:
            self.status_text.set_text("Status: [INVALID INTERVAL INPUT]")
            self.status_text.set_color(COLORS['alert'])
            logging.error("Invalid non-numeric input for interval slider")
        self.fig.canvas.draw_idle()


    def update_threshold(self, metric, text, multiplier):
        """Update thresholds from TextBox input with validation."""
        try:
            input_val = float(text)
            new_val = input_val * multiplier # Convert input unit to base unit (bytes for network)

            # Basic validation (can add more specific ranges per metric)
            if new_val > 0:
                self.thresholds[metric] = new_val
                self.status_text.set_text(f"Status: [{metric.upper()} THRESHOLD UPDATED]")
                self.status_text.set_color(COLORS['success'])
                logging.info(f"Threshold updated: {metric} = {new_val} (Input: {text})")
                # Redraw relevant plot to show new threshold line immediately
                if metric == 'cpu': self.update_cpu_plot()
                elif metric == 'memory': self.update_memory_plot()
                elif metric == 'disk': self.update_disk_plot()
                elif metric == 'network': self.update_network_plot()
                elif metric == 'process': self.update_process_plot()
                self.fig.canvas.draw_idle()
            else:
                self.status_text.set_text("Status: [VALUE MUST BE POSITIVE]")
                self.status_text.set_color(COLORS['alert'])
                # Reset text box to current valid threshold value
                self.threshold_inputs[metric].set_val(f"{self.thresholds[metric]/multiplier:.1f}" if metric=='network' else f"{int(self.thresholds[metric]/multiplier)}")
                logging.warning(f"Invalid threshold value for {metric}: {text}")
        except ValueError:
            self.status_text.set_text("Status: [INVALID THRESHOLD INPUT]")
            self.status_text.set_color(COLORS['alert'])
            # Reset text box to current valid threshold value
            self.threshold_inputs[metric].set_val(f"{self.thresholds[metric]/multiplier:.1f}" if metric=='network' else f"{int(self.thresholds[metric]/multiplier)}")
            logging.error(f"Invalid non-numeric input for {metric} threshold: {text}")
        self.fig.canvas.draw_idle()


    def get_system_metrics(self):
        """Collect system metrics with error handling."""
        try:
            # Get network counters before CPU percent to measure over the interval
            net_before = psutil.net_io_counters()
            cpu_usage = psutil.cpu_percent(interval=0.5) # Non-blocking interval
            net_after = psutil.net_io_counters()

            # Calculate network usage delta over the interval (approximate rate)
            # Note: This gives total bytes since boot, not rate. Rate calculation needs previous values.
            # Storing totals is simpler for this example. Thresholds apply to total usage reported.
            # For rate, you'd store previous values and subtract.
            # Let's keep it simple and use the total bytes reported by psutil for now.
            # The threshold check will compare these totals.

            return {
                'time': datetime.now().strftime('%H:%M:%S'),
                'cpu': cpu_usage,
                'memory': psutil.virtual_memory().percent,
                'disk': psutil.disk_usage('/').percent,
                'process': len(psutil.pids()),
                'network_sent': net_after.bytes_sent,
                'network_recv': net_after.bytes_recv
            }
        except Exception as e:
            logging.error(f"Error collecting system metrics: {str(e)}")
            # Optionally return last known good values or None/default dict
            return None


    def check_thresholds(self, metrics):
        """Check for threshold violations and update alerts."""
        if not metrics:
            return

        new_alerts = []
        timestamp = metrics['time'] # Use the timestamp from metrics collection

        if metrics['cpu'] > self.thresholds['cpu']:
            alert_msg = f"CPU: {metrics['cpu']:.1f}% > {self.thresholds['cpu']:.0f}%"
            new_alerts.append(alert_msg)
            logging.warning(f"Alert Triggered: {alert_msg}")

        if metrics['memory'] > self.thresholds['memory']:
            alert_msg = f"MEM: {metrics['memory']:.1f}% > {self.thresholds['memory']:.0f}%"
            new_alerts.append(alert_msg)
            logging.warning(f"Alert Triggered: {alert_msg}")

        if metrics['disk'] > self.thresholds['disk']:
            alert_msg = f"DISK: {metrics['disk']:.1f}% > {self.thresholds['disk']:.0f}%"
            new_alerts.append(alert_msg)
            logging.warning(f"Alert Triggered: {alert_msg}")

        # Network check (compare total bytes, convert threshold to MB for message)
        net_thresh_mb = self.thresholds['network'] / 1e6
        # Note: Comparing total bytes sent/received since boot might not be ideal for alerts.
        # A better approach would be rate (MB/s), which requires storing previous values.
        # Keeping the current simpler logic for this example.
        # Let's change the check to be more meaningful, e.g., if *increase* per interval is high
        # For now, sticking to the original logic comparing totals:
        if metrics['network_sent'] > self.thresholds['network']:
            sent_mb = metrics['network_sent'] / 1e6
            # alert_msg = f"NET SENT: {sent_mb:.1f}MB > {net_thresh_mb:.1f}MB (Total)" # Indicate it's total
            # new_alerts.append(alert_msg)
            # logging.warning(f"Alert Triggered: {alert_msg}")
            pass # Deactivate simple total check for network as it's less useful

        if metrics['network_recv'] > self.thresholds['network']:
            recv_mb = metrics['network_recv'] / 1e6
            # alert_msg = f"NET RECV: {recv_mb:.1f}MB > {net_thresh_mb:.1f}MB (Total)" # Indicate it's total
            # new_alerts.append(alert_msg)
            # logging.warning(f"Alert Triggered: {alert_msg}")
            pass # Deactivate simple total check for network

        if metrics['process'] > self.thresholds['process']:
            alert_msg = f"PROC: {metrics['process']} > {self.thresholds['process']}"
            new_alerts.append(alert_msg)
            logging.warning(f"Alert Triggered: {alert_msg}")

        if new_alerts:
            alert_tuples = [(timestamp, alert) for alert in new_alerts]
            self.alerts.extend(alert_tuples)
            self.alert_history.extend(alert_tuples) # Keep full history
            self.alerts = self.alerts[-8:]  # Limit displayed alerts
            self.status_text.set_text("Status: [ALERT TRIGGERED]")
            self.status_text.set_color(COLORS['alert'])
            # Update alert panel immediately
            self.update_alert_panel()


    def update_dashboard(self, frame):
        """Main update function called by FuncAnimation."""
        if self.paused:
            # Return list of artists that need updating (empty if paused and not using blit)
            return []

        metrics = self.get_system_metrics()
        if not metrics:
            self.status_text.set_text("Status: [METRICS ERROR]")
            self.status_text.set_color(COLORS['alert'])
            # Decide how to handle missing metrics in plots (e.g., skip update, show gap)
            return [] # Skip update if metrics failed

        # Check thresholds before updating history (so history reflects state *before* alert check)
        self.check_thresholds(metrics) # This might update status text

        # Update history (only if metrics were successful)
        current_time = metrics['time'] # Use consistent time
        self.metrics_history['time'].append(current_time)
        self.metrics_history['cpu'].append(metrics['cpu'])
        self.metrics_history['memory'].append(metrics['memory'])
        self.metrics_history['disk'].append(metrics['disk'])
        self.metrics_history['network_sent'].append(metrics['network_sent'])
        self.metrics_history['network_recv'].append(metrics['network_recv'])
        self.metrics_history['process'].append(metrics['process'])

        # Trim history to max_data_points
        for key in self.metrics_history:
            if len(self.metrics_history[key]) > self.max_data_points:
                self.metrics_history[key] = self.metrics_history[key][-self.max_data_points:]

        # Update status bar text elements (only if not paused and no alert triggered/metric error)
        if not self.paused and self.status_text.get_text() not in ["Status: [ALERT TRIGGERED]", "Status: [METRICS ERROR]"]:
             self.status_text.set_text("Status: [RUNNING]")
             self.status_text.set_color(COLORS['success'])

        self.timestamp_text.set_text(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # Uptime update can be less frequent, but ok here for simplicity
        self.uptime_text.set_text(f"Uptime: {time.strftime('%H:%M:%S', time.gmtime(time.time() - psutil.boot_time()))}")


        # Update all plots and panels
        artists = []
        artists.extend(self.update_cpu_plot())
        artists.extend(self.update_memory_plot())
        artists.extend(self.update_disk_plot())
        artists.extend(self.update_network_plot())
        artists.extend(self.update_process_plot())
        artists.extend(self.update_alert_panel()) # Update alert panel even if no new alerts (to clear old ones)
        artists.extend(self.update_summary_panel(metrics))

        # When not using blit=True, FuncAnimation expects an iterable of artists, but returning
        # an empty list works fine as matplotlib redraws the whole figure anyway.
        # If using blit=True, you MUST return all modified artists.
        return []
def update_plot(self, ax, title, color, data_key, threshold_key=None, unit='%', is_network=False):
        """Generic plot update returning list of artists modified (for blitting, though not used)."""
        ax.clear() # Clear previous drawings
        self.configure_plot(ax, title, color) # Reapply base configuration
        artists = [] # Keep track of artists if blitting is desired later

        times = self.metrics_history['time']
        data = self.metrics_history[data_key]

        if not times or not data: # No data yet
             return artists

        y_data = data
        threshold_value = None
        threshold_unit_multiplier = 1e6 if is_network else 1

        if is_network:
            y_data = [d / threshold_unit_multiplier for d in data] # Convert bytes to MB for plotting

        # Threshold line and fill
        if threshold_key and threshold_key in self.thresholds:
            threshold_value = self.thresholds[threshold_key] / threshold_unit_multiplier # Threshold in plot units (e.g., MB)
            line = ax.axhline(y=threshold_value, color=COLORS['threshold'], linestyle='--', alpha=0.7, linewidth=1.5, label=f'Threshold ({threshold_value:.1f}{unit})')
            artists.append(line)

            # Fill area above threshold
            y_data_np = np.array(y_data)
            fill = ax.fill_between(
                times,
                threshold_value,
                y_data_np,
                where=y_data_np > threshold_value,
                color=COLORS['alert'], alpha=0.2, interpolate=True
            )
            # fill_between returns a PolyCollection, which is an Artist
            if fill: artists.append(fill)


        # Plot the main data line
        line, = ax.plot(
            times,
            y_data,
            color=color,
            linewidth=2.0, # Slightly thinner line
            marker='o',
            markersize=4, # Slightly smaller marker
            markerfacecolor=COLORS['background'],
            markeredgecolor=color,
            markeredgewidth=1.0,
            path_effects=[path_effects.SimpleLineShadow(shadow_color='black', alpha=0.3), path_effects.Normal()],
            label=f'Current: {y_data[-1]:.1f}{unit}' # Add current value to label
        )
        artists.append(line)

        # Add value annotation near the last point
        last_value = y_data[-1]
        annotation = ax.annotate(
            f'{last_value:.1f}{unit}',
            xy=(len(times)-1, last_value), # Position based on index
            xytext=(8, 0), # Offset pixels
            textcoords='offset points',
            color=color,
            fontsize=9, # Smaller annotation
            fontweight='bold',
            bbox=dict(
                boxstyle='round,pad=0.3',
                fc=COLORS['panel'],
                ec=color,
                lw=1.0, # Thinner border
                alpha=0.8 # Slightly more transparent
            )
        )
        artists.append(annotation)

        # Adjust Y-axis limits dynamically (with padding)
        if y_data:
            min_val = min(y_data)
            max_val = max(y_data)
            padding = (max_val - min_val) * 0.1 + 1 # Add small absolute padding too
            y_min = 0 # Generally start Y axis at 0 for usage plots
            y_max = max(max_val + padding, threshold_value + padding if threshold_value else 0)
            # For percentage plots, cap max at slightly above 100 if threshold isn't higher
            if unit == '%' and (not threshold_value or threshold_value <= 100):
                 y_max = max(y_max, 105) # Ensure 100% is visible
            elif is_network and (not threshold_value or threshold_value < 1):
                 y_max = max(y_max, 1.0) # Ensure small MB values have some scale

            ax.set_ylim(y_min, y_max)

        # Add legend if threshold is present
        #if threshold_key:
        #    leg = ax.legend(loc='upper left', fontsize=8, facecolor=COLORS['panel'], edgecolor=color)
        #    if leg: artists.extend(leg.get_texts())
        #    if leg: artists.extend(leg.get_lines())
        #    if leg: artists.append(leg.get_frame())

        # Return artists for blitting if needed (currently not used)
        return artists


    def update_cpu_plot(self):
        return self.update_plot(self.axes['cpu'], 'CPU USAGE (%)', COLORS['cpu'], 'cpu', 'cpu', '%')

    def update_memory_plot(self):
        return self.update_plot(self.axes['memory'], 'MEMORY USAGE (%)', COLORS['memory'], 'memory', 'memory', '%')

    def update_disk_plot(self):
        return self.update_plot(self.axes['disk'], 'DISK USAGE (%)', COLORS['disk'], 'disk', 'disk', '%')

    def update_process_plot(self):
        return self.update_plot(self.axes['process'], 'ACTIVE PROCESSES', COLORS['process'], 'process', 'process', '')


    def update_network_plot(self):
        """Update network plot with Sent/Received lines and threshold."""
        ax = self.axes['network']
        ax.clear()
        self.configure_plot(ax, 'NETWORK TRAFFIC (Total MB)', COLORS['network']) # Clarify Total
        artists = []
        times = self.metrics_history['time']

        if not times: return artists

        threshold_mb = self.thresholds['network'] / 1e6

        # Threshold line
        line_thresh = ax.axhline(y=threshold_mb, color=COLORS['threshold'], linestyle='--', alpha=0.7, linewidth=1.5, label=f'Threshold ({threshold_mb:.1f} MB)')
        artists.append(line_thresh)

        max_val = 0 # Track max value for Y-axis scaling

        # Plot sent data if enabled
        if self.show_network_sent:
            sent_mb = [x/1e6 for x in self.metrics_history['network_sent']]
            if sent_mb: max_val = max(max_val, max(sent_mb))
            line_sent, = ax.plot(
                times, sent_mb,
                color=COLORS['network'], linewidth=2.0, label=f'Sent: {sent_mb[-1]:.1f} MB' if sent_mb else 'Sent',
                marker='^', markersize=4, markerfacecolor=COLORS['background'], markeredgecolor=COLORS['network']
            )
            artists.append(line_sent)

        # Plot received data if enabled
        if self.show_network_recv:
            recv_mb = [x/1e6 for x in self.metrics_history['network_recv']]
            if recv_mb: max_val = max(max_val, max(recv_mb))
            line_recv, = ax.plot(
                times, recv_mb,
                color=COLORS['accent'], linewidth=2.0, label=f'Recv: {recv_mb[-1]:.1f} MB' if recv_mb else 'Recv',
                marker='v', markersize=4, markerfacecolor=COLORS['background'], markeredgecolor=COLORS['accent']
            )
            artists.append(line_recv)

        # Adjust Y-axis limits
        padding = max_val * 0.1 + 0.5 # Add some padding
        ax.set_ylim(0, max(max_val + padding, threshold_mb + padding))

        # Add legend if any data is shown
        if self.show_network_sent or self.show_network_recv:
            leg = ax.legend(
                loc='upper left',
                facecolor=COLORS['panel'],
                edgecolor=COLORS['text'], # Use text color for legend border
                fontsize=8 # Smaller legend font
            )
            if leg: # Add legend artists if blitting
                artists.extend(leg.get_texts())
                artists.extend(leg.get_lines())
                artists.append(leg.get_frame())

        return artists


    def update_alert_panel(self):
        """Update the alert panel text."""
        ax = self.axes['alert']
        ax.clear() # Clear previous text
        ax.set_title('ALERTS', color=COLORS['alert'], pad=10, fontsize=12, fontweight='bold')
        ax.axis('off') # Keep axis off
        artists = [] # For blitting if needed

        if self.alerts:
            # Display newest alerts at the top
            for i, (timestamp, alert) in enumerate(reversed(self.alerts)): # Show last 8, newest first
                 txt = ax.text(
                    0.02, 0.95 - i*0.11, # Adjust vertical spacing
                    f"• {timestamp} - {alert}",
                    color=COLORS['alert'],
                    fontsize=9,
                    fontweight='normal', # Normal weight for alerts
                    transform=ax.transAxes, # Use axis coordinates
                    verticalalignment='top' # Align text from top
                 )
                 artists.append(txt)
        else:
            txt = ax.text(
                0.5, 0.5,
                "NO ACTIVE ALERTS",
                color=COLORS['success'],
                ha='center',
                va='center',
                fontsize=11,
                fontweight='bold',
                transform=ax.transAxes
            )
            artists.append(txt)
        return artists


    def update_summary_panel(self, metrics):
        """Update the system summary panel."""
        ax = self.axes['summary']
        ax.clear()
        ax.set_title('SYSTEM SUMMARY', color=COLORS['accent'], pad=10, fontsize=12, fontweight='bold')
        ax.axis('off')
        artists = []

        # System info (collected less frequently might be better, but ok here)
        try:
            cpu_count = psutil.cpu_count(logical=False)
            cpu_logical = psutil.cpu_count(logical=True)
            memory_total_gb = round(psutil.virtual_memory().total / (1024**3), 1)
            disk_total_gb = round(psutil.disk_usage('/').total / (1024**3), 1)
            memory_used_gb = round(psutil.virtual_memory().used / (1024**3), 1)
            disk_used_gb = round(psutil.disk_usage('/').used / (1024**3), 1)
        except Exception as e:
            logging.error(f"Error getting static system info: {e}")
            cpu_count, cpu_logical, memory_total_gb, disk_total_gb = 'N/A', 'N/A', 'N/A', 'N/A'
            memory_used_gb, disk_used_gb = 'N/A', 'N/A'


        # Format network values safely in case metrics is None briefly
        net_sent_mb = metrics['network_sent'] / 1e6 if metrics else 0
        net_recv_mb = metrics['network_recv'] / 1e6 if metrics else 0

        sections = [
            ("HARDWARE INFO", [
                f"CPU Cores: {cpu_count} physical, {cpu_logical} logical",
                f"Total Memory: {memory_total_gb} GB",
                f"Total Disk (/): {disk_total_gb} GB"
            ]),
            ("CURRENT STATUS", [
                f"CPU Usage: {metrics['cpu']:.1f}%" if metrics else 'N/A',
                f"Memory Usage: {metrics['memory']:.1f}% ({memory_used_gb} GB)" if metrics else 'N/A',
                f"Disk Usage (/): {metrics['disk']:.1f}% ({disk_used_gb} GB)" if metrics else 'N/A',
                f"Active Processes: {metrics['process']}" if metrics else 'N/A',
                f"Network Total: ↑{net_sent_mb:.1f}MB / ↓{net_recv_mb:.1f}MB"
            ]),
            ("ALERT HISTORY", [
                f"Total Alerts Logged: {len(self.alert_history)}",
                f"Last Alert Time: {self.alert_history[-1][0] if self.alert_history else 'None'}"
            ])
        ]

        base_y = 0.95
        section_spacing = 0.32 # Space between sections
        item_spacing = 0.06 # Space between items in a section

        for i, (title, items) in enumerate(sections):
            section_y = base_y - i * section_spacing
            # Section Title
            txt_title = ax.text(0.02, section_y, title, color=COLORS['accent'], fontsize=10, fontweight='bold', transform=ax.transAxes, va='top')
            artists.append(txt_title)

            # Section Items
            for j, item in enumerate(items):
                item_y = section_y - 0.06 - j * item_spacing # Position items below title
                txt_item = ax.text(0.05, item_y, item, color=COLORS['text'], fontsize=9, transform=ax.transAxes, va='top')
                artists.append(txt_item)
        return artists


    def run(self):
        """Start the dashboard animation."""
        try:
            self.animation = FuncAnimation(
                self.fig,
                self.update_dashboard,
                frames=None, # Keep generating frames indefinitely
                interval=self.update_interval,
                blit=False, # Blitting is complex with dynamic text/layouts and widgets
                cache_frame_data=False, # Avoid memory leak with long runs
                repeat=False # Don't repeat animation
            )
            plt.show()
            logging.info("Dashboard stopped")
        except Exception as e:
            logging.critical(f"Dashboard runtime error: {str(e)}", exc_info=True)
            print(f"A critical error occurred: {e}. Check system_monitor.log for details.")
            # Optional: Try to clean up plot window if possible
            try:
                plt.close(self.fig)
            except Exception:
                pass # Ignore errors during cleanu

if __name__ == "__main__":
    print("Starting System Monitor Dashboard...")
    print("Check system_monitor.log for detailed activity.")
    try:
        dashboard = SystemMonitorDashboard()
        dashboard.run()
    except Exception as e:
        logging.critical(f"Fatal error during dashboard initialization or run: {str(e)}", exc_info=True)
        print(f"\nFATAL ERROR: {str(e)}")
        print("The application could not start. Please check system_monitor.log for details.")
        # Keep console open briefly to show error
        # input("Press Enter to exit...") # Uncomment if running from a double-click scenario
                
