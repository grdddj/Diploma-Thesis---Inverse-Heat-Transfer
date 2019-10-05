"""
SOURCE: https://www.learnpyqt.com/courses/concurrent-execution/multithreading-pyqt-applications-qthreadpool/

This module is almost identical as pyqt5_gui.py - the only difference is it uses PySide2
    as a GUI framework. PySide2 is almost the same as PyQt5, but has better
    licensing terms - it is not necessary to pay anything even if the app
    would be monetized.
Therefore I decided to continue developing this app in PySide, because you
    never know when somebody would like to buy it :)
The difference from PyQt5 lies mostly in the different naming in some cases
    (pyqtSignal vs Signal, pyqtSlot vs Slot...)

We are using gueue to communicate with the simulation thread, we are sending
    simulation state changes, so that the simulation can reflect this change.
"""

# TODO: Use the "import PySide2" statement below, which is needed for the plugins
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import *

import queue

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import traceback, sys
import time
import random
import threading

import pyqt5_simulation

# Below code is necessary to run the GUI, because it is missing some plugins otherwise
# https://stackoverflow.com/questions/51367446/pyside2-application-failed-to-start
import os
import PySide2
dirname = os.path.dirname(PySide2.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

def hello_world():
    print("HELLO WORLD")

class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self.left = 10
        self.top = 10
        self.title = 'PySide2 trial of HeatTransfer'
        self.width = 840
        self.height = 700

        self.simulation_state = None

        self.threadpool = QThreadPool()
        print("Multithreading with maximum {} threads".format(self.threadpool.maxThreadCount()))
        print("Current thread: " + threading.currentThread().getName())

        self.queue = queue.Queue()

        self.initUI()


    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        plot = PlotCanvas(self, width=7, height=7)
        plot.move(0,0)

        button_hello_world = QPushButton('HELLO WORLD', self)
        button_hello_world.move(700,0)
        button_hello_world.resize(140,100)

        button_hello_world.pressed.connect(lambda: hello_world())

        button_run = QPushButton('RUN', self)
        button_run.move(700,120)
        button_run.resize(140,100)

        button_run.pressed.connect(lambda: self.run_simulation(plot, self.queue))

        button_stop = QPushButton('STOP', self)
        button_stop.move(700,240)
        button_stop.resize(140,100)

        button_stop.pressed.connect(lambda: self.stop_simulation())

        button_stop = QPushButton('PAUSE', self)
        button_stop.move(700,360)
        button_stop.resize(140,100)

        button_stop.pressed.connect(lambda: self.pause_simulation())

        button_continue = QPushButton('CONTINUE', self)
        button_continue.move(700,500)
        button_continue.resize(140,100)

        button_continue.pressed.connect(lambda: self.continue_simulation())

        self.show()

    def simulation_finished(self):
        print("SIMULATION FINISHED!!")
        self.simulation_state = "finished"

    def pause_simulation(self):
        self.simulation_state = "paused"
        self.queue.put("pause")

    def continue_simulation(self):
        self.simulation_state = "running"
        self.queue.put("continue")

    def stop_simulation(self):
        self.simulation_state = "stopped"
        self.queue.put("stop")

    def run_simulation(self, plot, queue):
        if self.simulation_state in ["running", "paused"]:
            print("SIMULATION IS ALREADY RUNNING!!!")
            return

        self.simulation_state = "running"
        print("Simulation is running")
        queue.put("WE HAVE JUST BEGAN!")
        # Pass the function to execute
        worker = Worker(pyqt5_simulation.run_test, plot=plot, queue=queue) # Any other args, kwargs are passed to the run function

        # TODO: decide what to do with this (use it or delete it)
        # worker = Worker(pyqt5_simulation.run_test, plot=plot) # Any other args, kwargs are passed to the run function
        # worker.signals.result.connect(self.print_output)
        worker.signals.finished.connect(self.simulation_finished)
        # worker.signals.progress.connect(self.new_progress)

        # Execute
        self.threadpool.start(worker)

class PlotCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.plot()


    def plot(self, x=None, y=None):
        if x is None:
            x = [random.random() for i in range(25)]
        if y is None:
            y = [random.random() for i in range(25)]
        ax = self.figure.add_subplot(111)
        ax.cla()
        ax.plot(x, y)
        ax.set_title('Heat Transfer plot')
        self.draw()

class WorkerSignals(QObject):
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
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)


class Worker(QRunnable):
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

    @Slot()
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

    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
