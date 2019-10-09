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
    - address the "error_value: nan" bug when simulation is "stopped" when not running
    - create a small window where to put important notices in the GUI
    - create some area where to show error messages to the user
        - or create a popup window with the same intent
    - create the saving of images and CSV files as a result
    - find out how to make the left arguments-menu not occupy the whole height
    - add documentation to classes and functions
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

import sys
import time

import threading
import queue

import heat_transfer_simulation

from heat_transfer_workers import Worker, WorkerSignals

from heat_transfer_plot import PlotCanvas

from heat_transfer_materials import MaterialService
material_service = MaterialService()

from heat_transfer_user_inputs import UserInputService
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
        self.setWindowTitle("Heat transfer")

        self.add_material_choice()
        self.add_user_inputs()

        plot = PlotCanvas(self)
        self.plot_area_layout_2.addWidget(plot)

        # Having access to the current state of the simulation
        # Can be either "running", "paused", "stopped" or "finished"
        self.simulation_state = None

        # Saving the material we are simulating right now
        self.chosen_material = None

        # Variables to keep user informed about the elapsed simulation time
        # TODO: probably create an individual object for this
        #       - also the logic could be maybe simplified
        self.simulation_started_timestamp = 0
        self.time_is_running = False
        self.simulation_paused_timestamp = 0
        self.time_spent_paused = 0
        self.time_in_progress = 0

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

    def get_numbers_from_the_user_input(self):
        """
        Getting a list of number parameters from the user, according to the
            passed list of input elements.
        Depends on all the inputted elements to have a certain structure,
            to be processed the right way.
        """
        list_of_values_to_return = []
        for element in user_input_service.number_parameters_to_get_from_user:
            try:
                # Replacing comma with a dot (for those used to writing decimals places with a comma)
                value_from_user = getattr(self, element["input_name"]).text().replace(",", ".")
                parsed_value_from_user_in_SI = element["parse_function"](value_from_user) * element["multiplicate_to_SI"]
            # If the value is still not parseable to specified type, make it a default value
            #   and notify the user of it
            except ValueError:
                parsed_value_from_user_in_SI = element["default_value"] * element["multiplicate_to_SI"]
                getattr(self, element["input_name"]).setText(str(element["default_value"]))
                # self.show_message_to_the_user("ERROR: Your {} was not a valid number! We gave it a default of {} {}.".format(
                #     element["name"], element["default_value"], element["unit"]))

            list_of_values_to_return.append(parsed_value_from_user_in_SI)

        return list_of_values_to_return


    def add_material_choice(self):
        """

        """
        self.material_combo_box = QtWidgets.QComboBox()
        self.material_combo_box.setFont(QtGui.QFont("Times", 20, QtGui.QFont.Bold))
        self.material_combo_box.addItems(material_service.materials_name_list)
        self.material_combo_box.setCurrentIndex(material_service.materials_name_list.index('Iron'))

        new_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Material: ")
        label.setFont(QtGui.QFont("Times", 20, QtGui.QFont.Bold))
        new_layout.addWidget(label)

        new_layout.addWidget(self.material_combo_box)
        self.verticalLayout.addLayout(new_layout)
        # TODO: add a tooltip with information whenever the material is highlighted:
        #   https://www.tutorialspoint.com/pyqt/pyqt_qcombobox_widget.htm

    def simulation_finished(self):
        """

        """
        print("SIMULATION FINISHED!!")
        # Allowing all the fields for editing again
        self.lock_inputs_for_editing(False)

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

        # Getting current material from GUI and it's peoperties from the service
        current_material = self.material_combo_box.currentText()
        current_material_properties = (material_service.materials_properties_dict[current_material])

        # Getting all other user input for the simulation
        user_input = self.get_numbers_from_the_user_input()
        dt, object_length, place_of_interest, number_of_elements = user_input

        parameters = {
            "rho": current_material_properties["rho"],
            "cp": current_material_properties["cp"],
            "lmbd": current_material_properties["lmbd"],
            "dt": dt,
            "object_length": object_length,
            "place_of_interest": place_of_interest,
            "number_of_elements": number_of_elements
        }

        self.lock_inputs_for_editing(True)

        # Preparing all the time variables for the new simulation
        # TODO: make it more precise with starting counting only as soon as
        #       the simulation really starts
        self.simulation_started_timestamp = time.time()
        self.time_is_running = True
        self.simulation_paused_timestamp = 0
        self.time_spent_paused = 0
        self.time_in_progress = 0

        # Pass the function to execute
        worker = Worker(heat_transfer_simulation.run_test, plot=plot, queue=queue,
                        parameters=parameters, SCENARIO_DESCRIPTION="PyQt5_GUI")

        # TODO: decide what to do with this (use it or delete it)
        worker.signals.result.connect(self.process_output)
        worker.signals.finished.connect(self.simulation_finished)
        worker.signals.progress.connect(self.update_simulation_time)

        # Execute
        self.threadpool.start(worker)

    def update_simulation_time(self, simulation_state):
        """
        Keeping the user notified about the time the simulation is taking.
        Is being called everytime the simulation will emit it's state.
        Parameters:
            simulation_state (int) Whether the simulation is running (1) or not (0)
        """
        now = time.time()

        if simulation_state == 1:
            # Handle transition from paused to running
            if self.time_is_running == False:
                self.time_is_running = True
                self.time_spent_paused += now - self.simulation_paused_timestamp

            # Update the label to show latest time
            elapsed_time = now - self.simulation_started_timestamp - self.time_spent_paused
            self.time_label.setText("TIME: {} s".format(round(elapsed_time, 2)))
        elif simulation_state == 0:
            # Handle transition from running to paused, otherwise do nothing
            if self.time_is_running == True:
                self.time_is_running = False
                self.simulation_paused_timestamp = now

                elapsed_time = now - self.simulation_started_timestamp - self.time_spent_paused
                self.time_label.setText("TIME: {} s".format(round(elapsed_time, 2)))

    def process_output(self, returned_object):
        """

        """
        print(returned_object)
        # TODO: create a function to change this error, and to colour it accordingly
        self.error_label.setText("ERROR: {}".format(returned_object["error_value"]))

    def lock_inputs_for_editing(self, lock=True):
        """
        Locks or unlocks all the user inputs.
        Parameters:
            lock  (bool) ... If the inputs should be locked (True)
                             or unlocked (False)
        """
        # (UN)locking the number inputs
        for element in user_input_service.number_parameters_to_get_from_user:
            getattr(self, element["input_name"]).setReadOnly(lock)

        # (Un)locking the material menu
        self.material_combo_box.setEnabled(not lock)

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

    # heat_transfer_window.showMaximized()
    # heat_transfer_window.resize(1000, 500)
    heat_transfer_window.show()


    sys.exit(app.exec_())
