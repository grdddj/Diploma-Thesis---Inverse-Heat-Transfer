"""
This module is responsible for setting the plot and defining it's behaviors.
"""

from PyQt5 import QtWidgets
import random

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

class PlotCanvas(FigureCanvas):
    """

    """
    def __init__(self, parent=None, dpi=100):
        fig = Figure(dpi=dpi)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.temperature_subplot = self.figure.add_subplot(111)

        self.plot()

    def plot(self, x_values=None, y_values=None,
                   x_experiment_values=None, y_experiment_values=None):
        """

        """
        # TODO: make the plot at the beginning to say something, like "Press RUN"
        if x_values is None:
            x_values = [random.random() for i in range(25)]
        if y_values is None:
            y_values = [random.random() for i in range(25)]
        self.temperature_subplot.cla()
        self.temperature_subplot.set_title('Heat Transfer plot')
        self.temperature_subplot.set_xlabel("Time [s]")
        self.temperature_subplot.set_ylabel("Temperature [°C]")

        self.temperature_subplot.plot(x_values, y_values, label='Calculated Data')
        if x_experiment_values is not None and y_experiment_values is not None:
            self.temperature_subplot.plot(x_experiment_values, y_experiment_values, label='Experiment Data')


        self.temperature_subplot.legend()
        self.draw()
