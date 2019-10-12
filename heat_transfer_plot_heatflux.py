"""
This module is responsible for setting the plot and defining it's behaviors.
"""

from PyQt5 import QtWidgets
import random

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

class HeatFluxPlotCanvas(FigureCanvas):
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

        self.heat_flux_subplot = self.figure.add_subplot(111)

        self.plot()

    def plot(self, x_values=None, y_values=None,
                   x_experiment_values=None, y_experiment_values=None):
        """

        """
        # TODO: make the plot at the beginning to say something, like "Press RUN"
        self.heat_flux_subplot.cla()
        self.heat_flux_subplot.set_title('Heat flux plot')
        self.heat_flux_subplot.set_xlabel("Time [s]")
        self.heat_flux_subplot.set_ylabel("Heat flux [W]")

        if x_values is not None and y_values is not None:
            min_length = min(len(x_values), len(y_values))
            self.heat_flux_subplot.plot(x_values[:min_length], y_values[:min_length], label='Calculated Data', color="blue")
        if x_experiment_values is not None and y_experiment_values is not None:
            min_length = min(len(x_experiment_values), len(y_experiment_values))
            self.heat_flux_subplot.plot(x_experiment_values[:min_length], y_experiment_values[:min_length], label='Experiment Data', color="orange")


        self.heat_flux_subplot.legend()
        self.draw()
