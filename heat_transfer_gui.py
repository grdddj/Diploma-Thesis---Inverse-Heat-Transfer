"""
This module is including all the main functionality of this application
    and is the one being called.
It spawns the GUI and enables users to choose their custom parameters
    and run the simulation.
"""

import sys
import time
import threading
import queue

from PyQt5 import QtWidgets, QtGui, QtCore  # type: ignore
from PyQt5.uic import loadUiType  # type: ignore

import heat_transfer_simulation
import heat_transfer_simulation_inverse

from heat_transfer_workers import Worker

from heat_transfer_plot_temperature import TemperaturePlotCanvas
from heat_transfer_plot_heatflux import HeatFluxPlotCanvas

from heat_transfer_materials import MaterialService
from heat_transfer_user_inputs_classic import UserInputServiceClassic
from heat_transfer_user_inputs_inverse import UserInputServiceInverse

material_service = MaterialService()
user_input_service_classic = UserInputServiceClassic()
user_input_service_inverse = UserInputServiceInverse()

# Creating the UI from the .ui template
# We could also generate a .py file from it and import it
#   - worth a try later, now for development purposes this is more comfortable
Ui_MainWindow, QMainWindow = loadUiType('heat_transfer_gui.ui')


class HeatTransferWindow(QMainWindow, Ui_MainWindow):  # type: ignore
    """
    Class holding the whole GUI
    It stores all the internal variables and behaviors
    """

    def __init__(self, ):
        super(HeatTransferWindow, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Heat transfer")

        # Filling the left side with user choice and inputs
        self.add_saving_choices(self.verticalLayout_6)
        self.add_algorithm_choice(self.verticalLayout_6)
        self.add_material_choice(self.verticalLayout_6)
        self.add_user_inputs(self.verticalLayout_6)

        # Adding plots for temperature and heat flux
        self.temperature_plot = TemperaturePlotCanvas(self)
        self.heat_flux_plot = HeatFluxPlotCanvas(self)
        self.plot_area_layout_3.addWidget(self.temperature_plot)
        self.plot_area_layout_3.addWidget(self.heat_flux_plot)

        # Having access to the current state of the simulation
        # Can be either "started", "running", "paused", "stopped" or "finished"
        self.simulation_state = "started"

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

        self.button_run_3.pressed.connect(lambda: self.run_simulation())
        self.button_pause_3.pressed.connect(lambda: self.pause_simulation())
        self.button_stop_3.pressed.connect(lambda: self.stop_simulation())

        self.update_state_for_the_user()

    def set_simulation_state(self,
                             new_state: str,
                             update_buttons: bool = True) -> None:
        """
        Function to put together the state-change and the specific button
            highlighting that is connected with the new state.
        """

        self.simulation_state = new_state
        if update_buttons:
            self.update_state_for_the_user()

    def update_state_for_the_user(self) -> None:
        """
        Shows to the user in which state the simulation is - by highlighting
            specific button.
        We are just playing with the width of the border.
        Also mentioning the simulation state in the user info label.
        """

        # TODO: research some better way, as this is quite awkward, to assign
        #       always the whole stylesheet
        font = 'font: 20pt "MS Shell Dlg 2";'
        border = 'border: 1px solid black;'
        border_active = 'border: 15px solid black;'
        color_run = 'background-color: rgb(0, 255, 0);'
        color_pause = 'background-color: rgb(255, 140, 0);'
        color_stop = 'background-color: rgb(255, 0, 0);'

        run_stylesheet = '{} {} {}'.format(font, color_run, border_active if self.simulation_state == "running" else border)
        pause_stylesheet = '{} {} {}'.format(font, color_pause, border_active if self.simulation_state == "paused" else border)
        stop_stylesheet = '{} {} {}'.format(font, color_stop, border_active if self.simulation_state == "stopped" else border)
        self.button_run_3.setStyleSheet(run_stylesheet)
        self.button_pause_3.setStyleSheet(pause_stylesheet)
        self.button_stop_3.setStyleSheet(stop_stylesheet)

        if self.simulation_state == "started":
            self.show_message_to_user("Choose your parameters and click Run button. Hover over parameters to get details.")
        elif self.simulation_state == "running":
            self.show_message_to_user("Simulation started. Click Pause to pause it, or Stop to abort it completely.")
        elif self.simulation_state == "paused":
            self.show_message_to_user("Simulation paused. Click Run to continue simulation.")
        elif self.simulation_state == "stopped":
            self.show_message_to_user("Simulation stopped. Click Run to start with new simulation.")
        elif self.simulation_state == "finished":
            self.show_message_to_user("Simulation finished. Click Run to start with new simulation.")

    def clear_layout(self, layout) -> None:
        """
        Completely empties the inputted layout, and makes it ready for
            new information.
        """

        while layout.count():
            child = layout.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
            elif child.layout() is not None:
                self.clear_layout(child.layout())

    def show_message_to_user(self, message: str) -> None:
        """
        Shows arbitrary message (general info or error) to the user.
        """

        print(message)
        self.info_label.setText(message)

    def show_error_dialog_to_user(self, error_message: str) -> None:
        """
        Displays a separate dialog (alert) informing user of something bad, like
            invalid user input.
        """

        # TODO: implement the new window creation
        self.show_message_to_user(error_message)

        print(error_message)

    def change_user_input(self) -> None:
        """
        Making sure each algorithm has it's own custom user inputs
        """

        # TODO: maybe the algorithm an material choice could stay, and
        #       only inputs themselves could be deleted and recreated
        # Clearing the whole layout and filling it again
        self.clear_layout(self.verticalLayout_6)

        self.add_saving_choices(self.verticalLayout_6)
        self.add_algorithm_choice(self.verticalLayout_6, self.get_current_algorithm())
        self.add_material_choice(self.verticalLayout_6)
        self.add_user_inputs(self.verticalLayout_6)

    def add_saving_choices(self, parent_layout) -> None:
        """
        Including the checkboxes for user to choose if to save data or not
        """

        new_layout = QtWidgets.QHBoxLayout()

        self.save_plots_checkbox = QtWidgets.QCheckBox("Save plots")
        self.save_data_checkbox = QtWidgets.QCheckBox("Save data")

        new_layout.addWidget(self.save_plots_checkbox)
        new_layout.addWidget(self.save_data_checkbox)

        parent_layout.addLayout(new_layout)

    def add_algorithm_choice(self,
                             parent_layout,
                             specified_algorithm: str = None) -> None:
        """
        Including the radio buttons for user to choose the algorithm
        """

        new_layout = QtWidgets.QHBoxLayout()

        label = QtWidgets.QLabel("Algorithm choice:")
        label.setFont(QtGui.QFont("Times", 15, QtGui.QFont.Bold))

        self.radio_choice_classic = QtWidgets.QRadioButton("Classic")
        self.radio_choice_inverse = QtWidgets.QRadioButton("Inverse")

        # Seeing which algorithm should be checked (useful when rerendering the inputs)
        if specified_algorithm is None or specified_algorithm == "classic":
            self.radio_choice_classic.setChecked(True)
        else:
            self.radio_choice_inverse.setChecked(True)

        # Listening for changes in the choice of algorithm
        # TODO: with more than 2 algorithms all would need to listen
        self.radio_choice_classic.toggled.connect(lambda: self.change_user_input())

        new_layout.addWidget(label)
        new_layout.addWidget(self.radio_choice_classic)
        new_layout.addWidget(self.radio_choice_inverse)

        parent_layout.addLayout(new_layout)

    def add_user_inputs(self, parent_layout) -> None:
        """
        Including the labels and input fields for all the input data that
            are required for a current situation (algorithm)
        """

        for entry in self.get_current_input_service().number_parameters_to_get_from_user:
            new_layout = QtWidgets.QHBoxLayout()

            label_text = "{} [{}]:".format(entry["name"], entry["unit_abbrev"])
            label = QtWidgets.QLabel(label_text)
            label.setFont(QtGui.QFont("Times", 15, QtGui.QFont.Bold))
            label.setToolTip(entry["description"])

            setattr(self, entry["input_name"], QtWidgets.QLineEdit())
            getattr(self, entry["input_name"]).setText(str(entry["default_value"]))
            getattr(self, entry["input_name"]).setFont(QtGui.QFont("Times", 20, QtGui.QFont.Bold))
            # TODO: add validation to only allow for numbers here

            new_layout.addWidget(label)
            new_layout.addWidget(getattr(self, entry["input_name"]))

            parent_layout.addLayout(new_layout)

    def get_current_input_service(self):
        """
        Simplifies the choice of user input service
        """

        if self.radio_choice_classic.isChecked():
            return user_input_service_classic
        elif self.radio_choice_inverse.isChecked():
            return user_input_service_inverse

    def get_current_algorithm(self) -> str:
        """
        Simplifies the access to current algorithm
        """

        if self.radio_choice_classic.isChecked():
            return "classic"
        elif self.radio_choice_inverse.isChecked():
            return "inverse"

        return "no algorithm"

    def get_numbers_from_the_user_input(self) -> dict:
        """
        Getting number parameters from the user in the form of a dictionary.
            Dictionary is better than list, because we are defining everything
            including the variable name in a separate file, and GUI does not
            have to care about anything - just passing whatever is found
            to the simulation.
        Depends on all the inputted elements to have a certain structure,
            to be processed the right way.
        """

        values_dictionary = {}
        for element in self.get_current_input_service().number_parameters_to_get_from_user:
            try:
                # Replacing comma with a dot (for those used to writing decimals places with a comma)
                value_from_user = getattr(self, element["input_name"]).text().replace(",", ".")
                parsed_value_from_user_in_SI = element["parse_function"](value_from_user) * element["multiplicate_to_SI"]
            # If the value is still not parseable to specified type, make it a default value
            #   and notify the user of it
            except ValueError:
                parsed_value_from_user_in_SI = element["default_value"] * element["multiplicate_to_SI"]
                getattr(self, element["input_name"]).setText(str(element["default_value"]))
                self.show_error_dialog_to_user("ERROR: Your {} was not a valid number! We gave it a default of {} {}.".format(
                    element["name"], element["default_value"], element["unit"]))

            values_dictionary[element["variable_name"]] = parsed_value_from_user_in_SI

        return values_dictionary

    def add_material_choice(self, parent_layout) -> None:
        """
        Adding the menu with all possible materials users can choose
        """

        new_layout = QtWidgets.QHBoxLayout()

        self.material_combo_box = QtWidgets.QComboBox()
        self.material_combo_box.setFont(QtGui.QFont("Times", 20, QtGui.QFont.Bold))
        self.material_combo_box.addItems(material_service.materials_name_list)
        self.material_combo_box.setCurrentIndex(material_service.materials_name_list.index('Iron'))

        label = QtWidgets.QLabel("Material: ")
        label.setFont(QtGui.QFont("Times", 20, QtGui.QFont.Bold))

        new_layout.addWidget(label)
        new_layout.addWidget(self.material_combo_box)

        parent_layout.addLayout(new_layout)
        # TODO: add a tooltip with information whenever the material is highlighted:
        #   https://www.tutorialspoint.com/pyqt/pyqt_qcombobox_widget.htm

    def simulation_finished(self) -> None:
        """
        What to do when simulation is over
        """

        print("SIMULATION FINISHED!!")
        # Allowing all the fields for editing again
        self.lock_inputs_for_editing(False)

        # Unhighlight all buttons, when it was not stopped by the user
        if self.simulation_state == "stopped":
            self.set_simulation_state("finished", update_buttons=False)
        else:
            self.set_simulation_state("finished")

        # Saving the plots
        if self.save_plots_checkbox.isChecked():
            self.temperature_plot.save_results_to_png_file(material=self.chosen_material, method=self.get_current_algorithm())
            self.heat_flux_plot.save_results_to_png_file(material=self.chosen_material, method=self.get_current_algorithm())

    def pause_simulation(self) -> None:
        """
        What to do when simulation is paused
        Having it enabled only when the simulation is running
        """

        if self.simulation_state == "running":
            self.set_simulation_state("paused")
            print("PAUSING THE SIMULATION!!!!")
            # Sending signal to the calculating thread to have a rest
            self.queue.put("pause")

    def stop_simulation(self) -> None:
        """
        What to do when a simulation is stopped
        Having it enabled only when the simulation is running or paused
        """

        if self.simulation_state in ["running", "paused"]:
            self.set_simulation_state("stopped")
            print("STOPPING THE SIMULATION!!!!")
            # Telling the calculating thread to give up
            self.queue.put("stop")

    def run_simulation(self) -> None:
        """
        What to do when a Run button is clicked.
        """

        if self.simulation_state == "running":
            print("SIMULATION IS ALREADY RUNNING!!!")
            return

        if self.simulation_state == "paused":
            self.queue.put("continue")
            self.set_simulation_state("running")
            print("CONTINUING THE SIMULATION!!")
            return

        self.set_simulation_state("running")
        self.error_label_2.setText("ERROR:")
        print("RUNNING THE SIMULATION")

        # Getting current material from GUI and it's peoperties from the service
        self.chosen_material = self.material_combo_box.currentText()
        current_material_properties = material_service.materials_properties_dict[self.chosen_material]

        # Getting all other user input for the simulation
        parameters = self.get_numbers_from_the_user_input()
        parameters["rho"] = current_material_properties["rho"]
        parameters["cp"] = current_material_properties["cp"]
        parameters["lmbd"] = current_material_properties["lmbd"]

        # Disabling the user from modifying inputs
        self.lock_inputs_for_editing(True)

        # Preparing all the time variables for the new simulation
        # TODO: make it more precise with starting counting only as soon as
        #       the simulation really starts
        self.simulation_started_timestamp = time.time()
        self.time_is_running = True
        self.simulation_paused_timestamp = 0
        self.time_spent_paused = 0
        self.time_in_progress = 0

        # Defining arguments we will send to workers not depending on algorithm
        common_arguments_to_workers = {
            "temperature_plot": self.temperature_plot,
            "heat_flux_plot": self.heat_flux_plot,
            "queue": self.queue,
            "parameters": parameters,
            "save_results": self.save_data_checkbox.isChecked(),
        }

        # Running the specific simulation
        if self.get_current_algorithm() == "classic":
            print("classic")
            worker = Worker(heat_transfer_simulation.simulate_from_gui,
                            common_arguments_to_workers)
        elif self.get_current_algorithm() == "inverse":
            print("inverse")
            worker = Worker(heat_transfer_simulation_inverse.simulate_from_gui,
                            common_arguments_to_workers)

        # Opening some additional communication channels with the workers
        worker.signals.result.connect(self.process_output)
        worker.signals.finished.connect(self.simulation_finished)
        worker.signals.progress.connect(self.update_simulation_time)

        # Tell the workers to start the job
        self.threadpool.start(worker)

    def update_simulation_time(self, simulation_state: str) -> None:
        """
        Keeping the user notified about the time the simulation is taking.
        Is being called everytime the simulation will emit it's state.
        Parameters:
            simulation_state (int) Whether the simulation is running (1) or not (0)
        """

        now = time.time()

        if simulation_state == 1:
            # Handle transition from paused to running
            if self.time_is_running is False:
                self.time_is_running = True
                self.time_spent_paused += now - self.simulation_paused_timestamp

            # Update the label to show latest time
            elapsed_time = now - self.simulation_started_timestamp - self.time_spent_paused
            self.update_time_label(elapsed_time)
        elif simulation_state == 0:
            # Handle transition from running to paused, otherwise do nothing
            if self.time_is_running is True:
                self.time_is_running = False
                self.simulation_paused_timestamp = now

                elapsed_time = now - self.simulation_started_timestamp - self.time_spent_paused
                self.update_time_label(elapsed_time)

    def update_time_label(self, time_value: float) -> None:
        """
        Updates the time value in the time label
        Showing the value in seconds with the precision of 2 decimal places
        """

        self.time_label_2.setText("TIME: {} s".format(round(time_value, 2)))

    def update_error_label(self, error_value: float) -> None:
        """
        Updates the error value in the error label
        """

        self.error_label_2.setText("ERROR: {}".format(error_value))

    def process_output(self, returned_object: dict) -> None:
        """
        Displaying the information returned after the simulation has finished
        """

        print(returned_object)
        # TODO: create a function to change this error, and to colour it accordingly
        self.update_error_label(returned_object["error_value"])

    def lock_inputs_for_editing(self, lock: bool = True) -> None:
        """
        Locks or unlocks all the user inputs.
        Parameters:
            lock  (bool) ... If the inputs should be locked (True)
                             or unlocked (False)
        """

        # TODO: find out how to disable the algorithm radio button
        #   maybe https://stackoverflow.com/questions/11472284/how-to-set-a-read-only-checkbox-in-pyside-pyqt

        # (Un)locking the number inputs
        for element in self.get_current_input_service().number_parameters_to_get_from_user:
            getattr(self, element["input_name"]).setReadOnly(lock)

        # (Un)locking the material menu
        self.material_combo_box.setEnabled(not lock)


if __name__ == '__main__':
    # Necessary stuff for errors and exceptions to be thrown
    # Without this, the app just dies and says nothing
    sys._excepthook = sys.excepthook  # type: ignore

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
