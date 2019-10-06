"""
This messy module is the working example of PyQT GUI running our NumericalForward
    algorithms.
It consists of some Worker class, that I stole somewhere, after verifying it is
    actually doing it's job - enabling to use multithreading in the GUI.
The Worker class is responsible for running the simulation and updating the plot,
    while the PyQT loop can happily listen in it's event loop (the HELLO WORLD button).
Experiments have shown that running simulation in this way is around 10-20 %
    faster that in the TKinter app. This improvement is most probably the cause
    of involving more threads.
(I am not completely sure now how these Workers really work, but after printing
    thread IDs, it really seems new threads are responsible for the calculation.)
Disadvantage is that so far I can just run the simulation and wait for it to
    finish, I cannot pause it or stop it. Saying that, I haven't even tried
    that yet, as this is just a proof of concept.
(I verified that it is possible to get information from the Workers, so it
    should be also possible somehow to pass information to them, through some
    MPI - Message Passing Interface)
"""

from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QPushButton
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import traceback, sys
import time
import random
import threading

import pyqt5_simulation


def hello_world():
    print("HELLO WORLD")

class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self.left = 10
        self.top = 10
        self.title = 'PyQt5 trial of HeatTransfer'
        self.width = 640
        self.height = 400
        self.initUI()

        self.threadpool = QThreadPool()
        print("Multithreading with maximum {} threads".format(self.threadpool.maxThreadCount()))
        print("Current thread: " + threading.currentThread().getName())

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        plot = PlotCanvas(self, width=5, height=4)
        plot.move(0,0)

        button2 = QPushButton('HELLO WORLD', self)
        button2.move(500,0)
        button2.resize(140,100)

        button2.pressed.connect(lambda: hello_world())

        button4 = QPushButton('Run multithread', self)
        button4.move(500,240)
        button4.resize(140,100)

        button4.pressed.connect(lambda: self.run_simulation(plot))

        self.show()

    def execute_this_fn(self, progress_callback):
        for n in range(0, 5):
            time.sleep(1)
            progress_callback.emit(n*100/4)

        return "Done."

    def print_output(self, s):
        print(s)

    def thread_complete(self):
        print("THREAD COMPLETE!")

    def run_simulation(self, plot):
        print("Simulation is running")

        # Pass the function to execute
        worker = Worker(pyqt5_simulation.run_test, plot=plot) # Any other args, kwargs are passed to the run function
        # worker.signals.result.connect(self.print_output)
        # worker.signals.finished.connect(self.thread_complete)
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
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


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
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
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
