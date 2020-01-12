"""
This module is responsible for setting the plot and defining it's behaviors.
"""

import os
import time
from PyQt5 import QtWidgets  # type: ignore

from matplotlib.figure import Figure  # type: ignore
from matplotlib.backends.backend_qt5agg import (  # type: ignore
    FigureCanvasQTAgg as FigureCanvas)


class TemperaturePlotCanvas(FigureCanvas):
    """
    Class holding the temperature plot
    """

    def __init__(self, parent=None, dpi=100):
        self.fig = Figure(dpi=dpi)

        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.temperature_subplot = self.figure.add_subplot(111)

        self.plot()

    def plot(self, x_values=None, y_values=None,
             x_experiment_values=None, y_experiment_values=None) -> None:
        """
        Plotting the inputted values of temperature progress
        """

        # TODO: make the plot at the beginning to say something, like "Press RUN"
        self.temperature_subplot.cla()
        self.temperature_subplot.set_title('Temperature plot')
        self.temperature_subplot.set_xlabel("Time [s]")
        self.temperature_subplot.set_ylabel("Temperature [°C]")

        # In both cases of plotting we have to make sure we plot the
        #   data with the same dimensions, therefore we first determine
        #   she shortest array and plot just that data

        if x_values is not None and y_values is not None:
            min_length = min(len(x_values), len(y_values))
            self.temperature_subplot.plot(x_values[:min_length],
                                          y_values[:min_length],
                                          label='Calculated Data',
                                          color="blue")

        if x_experiment_values is not None and y_experiment_values is not None:
            min_length = min(len(x_experiment_values), len(y_experiment_values))
            self.temperature_subplot.plot(x_experiment_values[:min_length],
                                          y_experiment_values[:min_length],
                                          label='Experiment Data',
                                          color="orange")

        self.temperature_subplot.legend()
        self.draw()

    def save_results_to_png_file(self,
                                 material: str,
                                 method: str) -> None:
        """
        Outputs the (semi)results of a simulation into a PNG file and names it
            accordingly.
        """

        # TODO: discuss the possible filename structure

        # Getting the data from plot - to inuquely identify the plot condition
        # (for the complete plot being different from non-complete one)
        try:
            lines = self.figure.gca().get_lines()
            time_data = lines[0].get_data()[0]

            file_name = "Temperature-{}-{}-{}s.png".format(method,
                                                           material,
                                                           int(time_data[-1]))

            # If for some reason there was already the same file, rather not
            #   overwrite it, but create a new file a timestamp as an identifier
            if os.path.isfile(file_name):
                file_name = "{}-{}.png".format(file_name.split(".")[0],
                                               int(time.time()))

            self.fig.savefig(file_name)
        except IndexError:
            # IndexError happens when there is no calculated data yet
            # (When user clicks STOP button right after RUN button)
            pass
