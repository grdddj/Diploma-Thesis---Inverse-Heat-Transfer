"""
This module is responsible for setting the plot and defining it's behaviors.
"""

from PyQt5 import QtWidgets
import random
import os
import time

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

class HeatFluxPlotCanvas(FigureCanvas):
    """

    """
    def __init__(self, parent=None, dpi=100):
        self.fig = Figure(dpi=dpi)

        FigureCanvas.__init__(self, self.fig)
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

    def save_results_to_png_file(self, material, method):
        """
        Outputs the (semi)results of a simulation into a PNG file and names it
            accordingly.
        """
        # TODO: discuss the possible filename structure

        # Getting the data from plot - to inuquely identify the plot condition
        # (for the complete plot being different from non-complete one)
        lines = self.figure.gca().get_lines()
        time_data = lines[0].get_data()[0]
        flux_data = lines[0].get_data()[1]

        file_name = "HeatFlux-{}-{}-{}s.png".format(method, material, int(time_data[-1]))

        # If for some reason there was already the same file, rather not
        #   overwrite it, but create a new file a timestamp as an identifier
        if os.path.isfile(file_name):
            file_name = file_name.split(".")[0] + "-" + str(int(time.time())) + ".png"

        self.fig.savefig(file_name)
