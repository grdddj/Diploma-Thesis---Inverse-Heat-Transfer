"""
This module is the current HEAD of the development - almost a
    complete transition from TKinter GUI to PyQt5/PySide2 GUI.
    Only some smaller additions are needed here.

Beware that this file relies on heat_transfer_gui.ui, which is generated
    automatically from Qt Designer - so rather not to be manipulated.

Benefits of moving from TKinter to PyQt involve:
    1) The Performance:
        - The new GUI frameworks allow for the easy possibility of multithreading,
            which is making out application quicker and more responsive than
            before, without needing to awkwardly switch attention between
            calculating and listening.
    2) The functionality:
        - The new GUI frameworks have richer library of possible widgets and behaviors,
            which offers more possibilities increases our toolset.
    3) The UI development:
        - PyQt5 offers a fantastic app called Qt Designer, which is itself a GUI
            for creating GUIs. This UI is then completely separated from the
            business logic, and therefore almost anybody without any programming
            skills can create it. As long as the names of the widgets remain
            the same, it is possible to change layout of the UI freely, without
            having to worry about breaking the code.
        - It has maybe one disadvantage though, and that it is not possible to
            place widgets and stuff in relative sizes like in TKinter
            (At least I haven't found it yet)
    4) The future:
        - Qt as a platform for creating GUIs is not used only in Python, but
            almost in all major languages. Both the knowledge of it, and the
            possibility of transforming the app into a different language,
            if necessary, is certainly useful.

TODOS:
    - actually take the arguments from the user (not being done now)
    - create a time counter from within the GUI loop, so that it is not
         slowing down the simulation
    - create a small window where to put important notices in the GUI
    - create some area where to show error messages to the user
        - or create a popup window with the same intent
    - create the saving of images and CSV files as a result
    - find out how to make the left arguments-menu not occupy the whole height
    - add documentation to classes and functions
    - pick some naming convention for all files (like heat_transfer_***.py)
    - have an eye on speed - maybe it could even handle some multiprocessing
        - (or that FeniCS library)
    - think about more separation (Workers or PlotCanvas could deserve their own module)
    - think about the imports
        - (whether import *, import the module, or import individual functions)
    - bear in mind that we want to transition to PySide2 at the very end
    - generalize the fonts

TODOS FROM Tests.py:
    - offer the option of regular savings (useful in time-consuming simulations)
    - discuss in which situations to save the file
    - discuss the naming of the saved files
        - what information to incorporate there (dt etc.)
    - offer the creation of custom material/custom properties
        - consider showing the properties in the menu/next to it
        - consider moving materials to the DB (SQLite3)
    - improve the design of the menus and buttons
    - include second graph showing heat flux
    - look up the cx_Freeze to-exe module, as pyinstaller produces 300 MB .exe
        - cx_Freeze offers deletion of unused libraries (scipy etc.)
    - create second thread (process) that is responsible for the calculation
        - IDEA: running the calculation as a separate script, output the
                results to the text_file and draw it continually from there
    - offer "run calculation on background" possibility (without any visual output)
    - parameters that could be inputted from the user:
        - the type of algorithm
        - the time after which to plot the results (can quicken the simulation)
"""

from PyQt5.uic import loadUiType
from PyQt5 import QtWidgets, QtGui, QtCore

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

import sys
import random

import threading
import queue

import pyqt5_simulation

from material_service import MaterialService
material_service = MaterialService()

from user_input_service import UserInputService
user_input_service = UserInputService()

# Creating the UI from the .ui template
# We could also generate a .py file from it and import it
#   - worth a try later, now for development purposes this is more comfortable
Ui_MainWindow, QMainWindow = loadUiType('heat_transfer_gui.ui')

class HeatTransferWindow(QMainWindow, Ui_MainWindow):
    """

    """
    def __init__(self, ):
        super(HeatTransferWindow, self).__init__()
        self.setupUi(self)

        self.add_material_choice()
        self.add_user_inputs()

        plot = PlotCanvas(self)
        self.plot_area_layout_2.addWidget(plot)

        self.simulation_state = None

        self.threadpool = QtCore.QThreadPool()
        print("Multithreading with maximum {} threads".format(self.threadpool.maxThreadCount()))
        print("Current thread: " + threading.currentThread().getName())

        self.queue = queue.Queue()

        self.button_run_2.pressed.connect(lambda: self.run_simulation(plot, self.queue))
        self.button_pause_2.pressed.connect(lambda: self.pause_simulation())
        self.button_stop_2.pressed.connect(lambda: self.stop_simulation())

    def add_user_inputs(self):
        """

        """
        for entry in user_input_service.number_parameters_to_get_from_user:
            new_layout = QtWidgets.QHBoxLayout()
            label_text = "{} [{}]:".format(entry["name"], entry["unit_abbrev"])
            label = QtWidgets.QLabel(label_text)
            label.setFont(QtGui.QFont("Times", 15, QtGui.QFont.Bold))
            new_layout.addWidget(label)

            setattr(self, entry["input_name"], QtWidgets.QLineEdit())
            getattr(self, entry["input_name"]).setText(str(entry["default_value"]))
            getattr(self, entry["input_name"]).setFont(QtGui.QFont("Times", 20, QtGui.QFont.Bold))
            # TODO: add validation to only allow for numbers here

            new_layout.addWidget(getattr(self, entry["input_name"]))
            self.verticalLayout.addLayout(new_layout)


    def add_material_choice(self):
        """

        """
        self.combo_box = QtWidgets.QComboBox()
        self.combo_box.setFont(QtGui.QFont("Times", 20, QtGui.QFont.Bold))
        self.combo_box.addItems(material_service.materials_name_list)

        new_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Material: ")
        label.setFont(QtGui.QFont("Times", 20, QtGui.QFont.Bold))
        new_layout.addWidget(label)

        new_layout.addWidget(self.combo_box)
        self.verticalLayout.addLayout(new_layout)
        # TODO: add a tooltip with information whenever the material is highlighted:
        #   https://www.tutorialspoint.com/pyqt/pyqt_qcombobox_widget.htm

    def simulation_finished(self):
        """

        """
        print("SIMULATION FINISHED!!")
        self.simulation_state = "finished"

    def pause_simulation(self):
        """

        """
        self.simulation_state = "paused"
        print("PAUSING THE SIMULATION!!!!")
        self.queue.put("pause")

    def stop_simulation(self):
        """

        """
        self.simulation_state = "stopped"
        print("STOPPING THE SIMULATION!!!!")
        self.queue.put("stop")

    def run_simulation(self, plot, queue):
        """

        """
        if self.simulation_state == "running":
            print("SIMULATION IS ALREADY RUNNING!!!")
            return

        if self.simulation_state == "paused":
            queue.put("continue")
            print("CONTINUING THE SIMULATION!!")
            return

        self.simulation_state = "running"
        self.error_label.setText("ERROR:")
        print("RUNNING THE SIMULATION")
        queue.put("WE HAVE JUST BEGAN!")
        # Pass the function to execute
        worker = Worker(pyqt5_simulation.run_test, plot=plot, queue=queue, SCENARIO_DESCRIPTION="PyQt5_GUI")

        # TODO: decide what to do with this (use it or delete it)
        worker.signals.result.connect(self.process_output)
        worker.signals.finished.connect(self.simulation_finished)
        # worker.signals.progress.connect(self.new_progress)

        # Execute
        self.threadpool.start(worker)

    def process_output(self, returned_object):
        """

        """
        print(returned_object)
        # TODO: create a function to change this error, and to colour it accordingly
        self.error_label.setText("ERROR: {}".format(returned_object["error_value"]))

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

class WorkerSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    '''
    # TODO: decide what to do with this (use it or delete it)
    finished = QtCore.Signal()
    error = QtCore.Signal(tuple)
    result = QtCore.Signal(object)
    progress = QtCore.Signal(int)


class Worker(QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

        # TODO: decide what to do with this (use it or delete it)
        self.signals = WorkerSignals()
        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @QtCore.Slot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


if __name__ == '__main__':
    # Necessary stuff for errors and exceptions to be thrown
    # Without this, the app just dies and says nothing
    sys._excepthook = sys.excepthook
    def exception_hook(exctype, value, traceback):
        print(exctype, value, traceback)
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)
    sys.excepthook = exception_hook

    app = QtWidgets.QApplication(sys.argv)
    heat_transfer_window = HeatTransferWindow()

    heat_transfer_window.showMaximized()
    # main.resize(1000, 500)
    # main.show()

    sys.exit(app.exec_())
