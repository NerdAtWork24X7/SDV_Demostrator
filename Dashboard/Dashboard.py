import sys
import threading
from UDP_Client import Client
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton
from PySide6.QtGui import QPainter, QPen, QFont, QColor
from PySide6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, Property, QVariantAnimation
import random
import math


class DigitalClusterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._speed = 0
        self._rpm = 0
        self._temp = 90
        self._fuel = 50
        self._gear = 'N'

        self.speed_anim = QVariantAnimation(duration=800)
        self.speed_anim.valueChanged.connect(self.update_speed_value)

        self.rpm_anim = QVariantAnimation(duration=800)
        self.rpm_anim.valueChanged.connect(self.update_rpm_value)

        self.temp_anim = QVariantAnimation(duration=800)
        self.temp_anim.valueChanged.connect(self.update_temp_value)

        self.fuel_anim = QVariantAnimation(duration=800)
        self.fuel_anim.valueChanged.connect(self.update_fuel_value)

        self._night_mode = True
        self.bg_color = QColor(10, 10, 10)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dashboard_data)
        self.timer.start(1000)  # Update every second

        self.bg_anim = QVariantAnimation(
            startValue=QColor(10, 10, 10),
            endValue=QColor(245, 245, 245),
            duration=500,
        )
        self.bg_anim.valueChanged.connect(self.on_bg_anim_value_changed)

        # Initialize the Client instance
        self.client = Client()
        self.client.client_thread(self.client.data_callback)


    def update_speed_value(self, value):
        self._speed = int(value)
        self.update()

    def update_rpm_value(self, value):
        self._rpm = int(value)
        self.update()

    def update_temp_value(self, value):
        self._temp = int(value)
        self.update()

    def update_fuel_value(self, value):
        self._fuel = int(value)
        self.update()

    def get_night_mode(self):
        return self._night_mode

    def set_night_mode(self, value):
        self._night_mode = value
        start = self.bg_color
        end = QColor(10, 10, 10) if value else QColor(245, 245, 245)
        self.bg_anim.setStartValue(start)
        self.bg_anim.setEndValue(end)
        self.bg_anim.start()

    night_mode = Property(bool, get_night_mode, set_night_mode)

    def on_bg_anim_value_changed(self, color):
        self.bg_color = color
        self.update()

    def toggle_mode(self):
        self.night_mode = not self.night_mode

    def update_dashboard_data(self):
        self.speed_anim.setStartValue(self._speed)
        self.speed_anim.setEndValue(int(self.client.data_dict['SPEED']))
        print(f"Speed: {self.client.data_dict['SPEED']}")
        self.speed_anim.start()

        self.rpm_anim.setStartValue(self._rpm)
        self.rpm_anim.setEndValue(int(self.client.data_dict.get('RPM', self._rpm)))
        self.rpm_anim.start()

        self.temp_anim.setStartValue(self._temp)
        self.temp_anim.setEndValue(int(self.client.data_dict.get('TEMP', self._temp)))
        self.temp_anim.start()

        self.fuel_anim.setStartValue(self._fuel)
        self.fuel_anim.setEndValue(int(self.client.data_dict.get('FUEL', self._fuel)))
        self.fuel_anim.start()

        
        gear = self.client.data_dict.get('GEAR', self._gear)
        if gear != "0":
            self._gear = gear
        else:
            self._gear = "N"
        self.update()
    
    def draw_analog_gauge(self, painter, rect, value, max_value, color, label):
        center = rect.center()
        radius = rect.width() / 2 - 10

        # Draw gauge background
        painter.setPen(QPen(QColor(60, 60, 60), 5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, radius, radius)

        # Draw tick marks
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        for i in range(0, 11):  # 10 major ticks
            angle = 225 - (270 * i / 10)
            x1 = center.x() + radius * math.cos(math.radians(angle))
            y1 = center.y() - radius * math.sin(math.radians(angle))
            x2 = center.x() + (radius - 10) * math.cos(math.radians(angle))
            y2 = center.y() - (radius - 10) * math.sin(math.radians(angle))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            # Add labels
            label_val = int((max_value / 10) * i)
            label_x = center.x() + (radius - 20) * math.cos(math.radians(angle))
            label_y = center.y() - (radius - 20) * math.sin(math.radians(angle))
            painter.drawText(int(label_x) - 10, int(label_y) + 5, f"{label_val}")

        # Draw needle
        needle_length = radius - (rect.width() // 15)
        angle = 225 - (270 * value / max_value)
        x_needle = center.x() + needle_length * math.cos(math.radians(angle))
        y_needle = center.y() - needle_length * math.sin(math.radians(angle))
        painter.setPen(QPen(color, 5))
        painter.drawLine(int(center.x()), int(center.y()), int(x_needle), int(y_needle))

        # Draw center circle
        painter.setBrush(color)
        painter.drawEllipse(center, 10, 10)

        # Draw digital value
        painter.setPen(QColor(255, 255, 255) if self.night_mode else QColor(0, 0, 0))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(rect, Qt.AlignBottom | Qt.AlignCenter, f"{int(value)} {label}")

    def draw_center_display(self, painter, rect):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(30, 30, 30) if self.night_mode else QColor(220, 220, 220))
        painter.drawRoundedRect(rect, 15, 15)

        painter.setPen(QColor(255, 255, 255) if self.night_mode else QColor(0, 0, 0))
        painter.setFont(QFont("Arial", 18, QFont.Bold))
        text = f"Gear: {self._gear}    Temp: {self._temp}°C    Fuel: {self._fuel}%"
        painter.drawText(rect, Qt.AlignCenter, text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Animated background
        painter.fillRect(self.rect(), self.bg_color)

        margin = 10
        arc_size = min(self.width() * 1.5, self.height() * 1.5) / 2 - margin

        # RPM analog gauge on left
        rpm_rect = QRectF(margin + 30, margin + 30, arc_size, arc_size)
        self.draw_analog_gauge(painter, rpm_rect, self._rpm, 8000, QColor(0, 170, 255), "RPM")

        # Speed analog gauge on right
        speed_rect = QRectF(self.width() - arc_size - margin - 30, margin + 30, arc_size, arc_size)
        self.draw_analog_gauge(painter, speed_rect, self._speed, 260, QColor(255, 100, 0), "km/h")

        # Center display
        center_rect = QRectF(self.width() / 2 - 400, self.height() - 60, 800, 60)

        self.draw_center_display(painter, center_rect)

class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("BMW Digital Cluster")
        self.setGeometry(100, 100, 800, 400)

        # Main widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout
        layout = QVBoxLayout()

        # Digital Cluster widget
        self.digital_cluster = DigitalClusterWidget()
        layout.addWidget(self.digital_cluster)

        # Toggle button
        self.toggle_button = QPushButton("Toggle Night/Day Mode")
        self.toggle_button.clicked.connect(self.digital_cluster.toggle_mode)
        layout.addWidget(self.toggle_button)

        # Set layout to central widget
        self.central_widget.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())
