"""
This module is including all the main functionality of this application
    and is the one being called.
It spawns the GUI and enables users to choose their custom parameters
    and run the simulation.
"""

import os
import sys
import time
import threading
import queue

from PyQt5.QtGui import QFont, QDoubleValidator # type: ignore
from PyQt5.QtCore import QThreadPool, Qt # type: ignore
from PyQt5.QtWidgets import (QFileDialog, QHBoxLayout, QVBoxLayout, QCheckBox, # type: ignore
    QLabel, QLineEdit, QPushButton, QGroupBox, QRadioButton, QComboBox,
    QFormLayout, QDialogButtonBox, QApplication, QDialog)
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
Ui_MainWindow, QMainWindow = loadUiType("heat_transfer_gui.ui")


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
        self.add_data_file_choices(self.verticalLayout_6)
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

        # Storing current data file
        self.current_data_file = "DATA.csv"

        # Variables to keep user informed about the elapsed simulation time
        # TODO: probably create an individual object for this
        #       - also the logic could be maybe simplified
        self.simulation_started_timestamp = 0
        self.time_is_running = False
        self.simulation_paused_timestamp = 0
        self.time_spent_paused = 0
        self.time_in_progress = 0

        self.threadpool = QThreadPool()
        print("Multithreading with maximum {} threads".format(self.threadpool.maxThreadCount()))
        print("Current thread: " + threading.currentThread().getName())

        self.queue = queue.Queue()

        self.button_run_3.pressed.connect(lambda: self.run_simulation())
        self.button_pause_3.pressed.connect(lambda: self.pause_simulation())
        self.button_stop_3.pressed.connect(lambda: self.stop_simulation())

        self.update_state_for_the_user()

    def open_file_name_dialog(self):
        """
        Opens a dialog for the choice of a data file
        """

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(self,
            "Choose a data file", "", "CSV Files (*.csv)", options=options)
        if file_path:
            # Storing the new data file path
            self.current_data_file = file_path
            # Extracting only the name of the file, without the whole path
            file_name = os.path.basename(file_path)
            print(file_name)

            # Displaying this into the input to provide visible feedback
            self.data_file_input.setText(file_name)

    def set_simulation_state(self,
                             new_state: str,
                             update_buttons: bool = True) -> None:
        """
        Function to put together the state-change and the specific button
            highlighting that is connected with the new state.

        Args:
            new_state ... simulation state that we should switch to
            update_buttons ... whether to reflect the change on buttons
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
        font = "font: 20pt 'MS Shell Dlg 2';"
        border = "border: 1px solid black;"
        border_active = "border: 15px solid black;"
        color_run = "background-color: rgb(0, 255, 0);"
        color_pause = "background-color: rgb(255, 140, 0);"
        color_stop = "background-color: rgb(255, 0, 0);"

        run_stylesheet = "{} {} {}".format(font, color_run, border_active if self.simulation_state == "running" else border)
        pause_stylesheet = "{} {} {}".format(font, color_pause, border_active if self.simulation_state == "paused" else border)
        stop_stylesheet = "{} {} {}".format(font, color_stop, border_active if self.simulation_state == "stopped" else border)
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

        Args:
            layout ... name of the layout which should be cleared
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

        Args:
            message ... what should be shown to the user
        """

        print(message)
        self.info_label.setText(message)

    def show_error_dialog_to_user(self, error_message: str) -> None:
        """
        Displays a separate dialog (alert) informing user of something bad, like
            invalid user input.

        Args:
            error_message ... what should be shown to the user
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
        self.add_data_file_choices(self.verticalLayout_6)
        self.add_material_choice(self.verticalLayout_6)
        self.add_user_inputs(self.verticalLayout_6)

    def add_saving_choices(self, parent_layout) -> None:
        """
        Including the checkboxes for user to choose if to save data or not

        Args:
            parent_layout ... into which layout we should include everything
        """

        self.saving_choice_layout = QHBoxLayout()

        self.save_plots_checkbox = QCheckBox("Save plots")
        self.save_data_checkbox = QCheckBox("Save data")

        self.saving_choice_layout.addWidget(self.save_plots_checkbox)
        self.saving_choice_layout.addWidget(self.save_data_checkbox)

        parent_layout.addLayout(self.saving_choice_layout)

    def add_data_file_choices(self, parent_layout) -> None:
        """
        Including the checkboxes for user to choose if to save data or not

        Args:
            parent_layout ... into which layout we should include everything
        """

        self.file_choice_layout = QHBoxLayout()

        label = QLabel("Data file: ")
        label.setFont(QFont("Times", 15, QFont.Bold))

        self.data_file_input = QLineEdit()
        self.data_file_input.setText("DATA.csv")
        self.data_file_input.setFont(QFont("Times", 15, QFont.Bold))
        self.data_file_input.setReadOnly(True)

        choice_button = QPushButton("Choose", self)
        choice_button.clicked.connect(self.open_file_name_dialog)

        self.file_choice_layout.addWidget(label)
        self.file_choice_layout.addWidget(self.data_file_input)
        self.file_choice_layout.addWidget(choice_button)

        parent_layout.addLayout(self.file_choice_layout)

    def add_smoothing_options(self, parent_layout) -> None:
        """
        Including the options for smoothing the final result

        Args:
            parent_layout ... into which layout we should include everything
        """

        # Creating all layouts (rows) we want to generate
        self.smooth_layout_labels = QHBoxLayout()
        self.smooth_layout_buttons = QHBoxLayout()
        self.smooth_alforithm_choice = QGroupBox("Smoothing algorithm")
        self.smooth_radio_choice_layout = QVBoxLayout()
        self.smooth_layout_radios = QHBoxLayout()

        # Creating the label and input for window length
        window_length_label = QLabel("Window length: ")
        window_length_label.setFont(QFont("Times", 15, QFont.Bold))

        self.window_length_input = QLineEdit()
        self.window_length_input.setText("2")
        self.window_length_input.setFont(QFont("Times", 15, QFont.Bold))

        # Creating the controlling buttons
        smooth_btn = QPushButton("Smooth", self)
        smooth_btn.clicked.connect(lambda: self.send_smoothing_option("smooth"))

        back_btn = QPushButton("Back", self)
        back_btn.clicked.connect(lambda: self.send_smoothing_option("back"))

        finish_btn = QPushButton("Finish", self)
        finish_btn.clicked.connect(lambda: self.send_smoothing_option("finish"))

        self.smooth_choice_moving_avg = QRadioButton("Moving average")
        self.smooth_choice_savgol = QRadioButton("Savgol")
        self.smooth_choice_moving_avg.setChecked(True)

        # Including all the widgets into their appropriate layouts (rows)
        self.smooth_layout_labels.addWidget(window_length_label)
        self.smooth_layout_labels.addWidget(self.window_length_input)
        self.smooth_layout_buttons.addWidget(smooth_btn)
        self.smooth_layout_buttons.addWidget(back_btn)
        self.smooth_layout_buttons.addWidget(finish_btn)
        self.smooth_radio_choice_layout.addWidget(self.smooth_choice_moving_avg)
        self.smooth_radio_choice_layout.addWidget(self.smooth_choice_savgol)
        self.smooth_alforithm_choice.setLayout(self.smooth_radio_choice_layout)

        self.smooth_layout_radios.addWidget(self.smooth_alforithm_choice)

        # Including all the layouts in chosen order into the parent layout
        parent_layout.addLayout(self.smooth_layout_radios)
        parent_layout.addLayout(self.smooth_layout_labels)
        parent_layout.addLayout(self.smooth_layout_buttons)

    def send_smoothing_option(self, option: str):
        """
        Moderating the connection between this GUI thread and calculation thread
            according the smoothing options after simulation finishes

        Args:
            option ... which supported command to send to a smoothing function
        """

        if option == "finish":
            # Sends the signal the smoothing has finished
            print("smoothing finished")
            self.queue.put("stop")
            # Hide the smoothing options
            self.clear_layout(self.smooth_layout_labels)
            self.clear_layout(self.smooth_layout_buttons)
            self.clear_layout(self.smooth_layout_radios)
        elif option == "back":
            self.queue.put("back")
        elif option == "smooth":
            # Including the window length and specific smoothing algorithm
            command = "smooth__{}__{}".format(self.window_length_input.text(),
                self.get_current_smoothing_algorithm())
            print("command", command)
            self.queue.put(command)

    def add_algorithm_choice(self,
                             parent_layout,
                             specified_algorithm: str = None) -> None:
        """
        Including the radio buttons for user to choose the algorithm

        Args:
            parent_layout ... into which layout we should include everything
            specified_algorithm ... if some algorithm is already chosen
        """

        self.algorithmlayout = QHBoxLayout()

        label = QLabel("Algorithm choice:")
        label.setFont(QFont("Times", 15, QFont.Bold))

        self.radio_choice_classic = QRadioButton("Classic")
        self.radio_choice_inverse = QRadioButton("Inverse")

        # Seeing which algorithm should be checked (useful when rerendering the inputs)
        if specified_algorithm is None or specified_algorithm == "classic":
            self.radio_choice_classic.setChecked(True)
        else:
            self.radio_choice_inverse.setChecked(True)

        # Listening for changes in the choice of algorithm
        # TODO: with more than 2 algorithms all would need to listen
        self.radio_choice_classic.toggled.connect(lambda: self.change_user_input())

        self.algorithmlayout.addWidget(label)
        self.algorithmlayout.addWidget(self.radio_choice_classic)
        self.algorithmlayout.addWidget(self.radio_choice_inverse)

        parent_layout.addLayout(self.algorithmlayout)

    def add_user_inputs(self, parent_layout) -> None:
        """
        Including the labels and input fields for all the input data that
            are required for a current situation (algorithm)

        Args:
            parent_layout ... into which layout we should include everything
        """

        for entry in self.get_current_input_service().number_parameters_to_get_from_user:
            new_layout = QHBoxLayout()

            label_text = "{} [{}]:".format(entry["name"], entry["unit_abbrev"])
            label = QLabel(label_text)
            label.setFont(QFont("Times", 15, QFont.Bold))
            label.setToolTip(entry["description"])

            # Generating the input and setting its font
            setattr(self, entry["input_name"], QLineEdit())
            getattr(self, entry["input_name"]).setFont(QFont("Times", 20, QFont.Bold))

            # Including the validation to be able to input only float values
            getattr(self, entry["input_name"]).setValidator(QDoubleValidator())
            # For some reason the validation treats floats with commas
            #   instead of dots, so we must display it in this manner
            # (Apparently, it is looking into the computer settings for the separator)
            value = str(entry["default_value"]).replace(".", ",")
            getattr(self, entry["input_name"]).setText(value)

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

    def get_current_smoothing_algorithm(self) -> str:
        """
        Simplifies the access to current smoothing algorithm
        """

        if self.smooth_choice_moving_avg.isChecked():
            return "moving_avg"
        elif self.smooth_choice_savgol.isChecked():
            return "savgol"

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

        Args:
            parent_layout  ... into which layout we should include everything
        """

        new_layout = QHBoxLayout()

        # Creating the choice of all materials and filling it with them
        self.material_combo_box = QComboBox()
        self.material_combo_box.setFont(QFont("Times", 15, QFont.Bold))
        self.material_combo_box.addItems(material_service.materials_name_list)
        self.material_combo_box.setCurrentIndex(material_service.materials_name_list.index("Iron"))

        # Defining tooltips for each material containing their properties
        for index, material in enumerate(material_service.materials_name_list):
            properties = material_service.materials_properties_dict[material]
            info = "{} - {}".format(material, str(properties))
            self.material_combo_box.setItemData(index, info, Qt.ToolTipRole)

        label = QLabel("Material: ")
        label.setFont(QFont("Times", 15, QFont.Bold))

        custom_material_button = QPushButton("Custom", self)
        custom_material_button.clicked.connect(self.get_custom_material)

        new_layout.addWidget(label)
        new_layout.addWidget(self.material_combo_box)
        new_layout.addWidget(custom_material_button)

        parent_layout.addLayout(new_layout)

    def get_custom_material(self):
        """
        Getting and parsing custom material data from the user
        """

        # Instantiating the dialog and getting its results
        dialog = CustomMaterialInputDialog()
        if dialog.exec():
            results = dialog.get_inputs()
            print(results)

            # Catching the possible error
            if results == "error":
                error_msg = "Error happened when parsing custom material data."
                print(error_msg)
                self.show_message_to_user(error_msg)
            # Otherwise save all the custom data
            # TODO: we could even save this material to our material file,
            #   to be available for the user even in the future
            else:
                # Including the name of new material into the material choice
                self.material_combo_box.addItem(results["name"])

                # Choosing the new material in the material choice
                index = self.material_combo_box.findText(results["name"], Qt.MatchFixedString)
                if index >= 0:
                    self.material_combo_box.setCurrentIndex(index)

                # Setting the material properties to be visible in a tooltip
                info = "{} - {}".format(results["name"], str(results["properties"]))
                self.material_combo_box.setItemData(index, info, Qt.ToolTipRole)

                # Saving the custom material properties
                material_service.materials_properties_dict[results["name"]] = results["properties"]

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
        parameters["experiment_data_path"] = self.current_data_file

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
            simulation_state (int) W

        Args:
            simulation_state  ... whether the simulation is running (1),
                                  is stopped(0) or has finished (2)
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
        elif simulation_state == 2:
            # Handle the smoothing options after simulation has finished
            self.add_smoothing_options(self.verticalLayout_6)

    def update_time_label(self, time_value: float) -> None:
        """
        Updates the time value in the time label
        Showing the value in seconds with the precision of 2 decimal places

        Args:
            time_value  ... time to show on the label
        """

        self.time_label_2.setText("TIME: {} s".format(round(time_value, 2)))

    def update_error_label(self, error_value: float) -> None:
        """
        Updates the error value in the error label

        Args:
            error_value  ... how big is the simulation eror
        """

        self.error_label_2.setText("ERROR: {}".format(error_value))

    def process_output(self, returned_object: dict) -> None:
        """
        Displaying the information returned after the simulation has finished

        Args:
            returned_object  ... object returned from simulation
        """

        print(returned_object)
        # TODO: create a function to change this error, and to colour it accordingly
        self.update_error_label(returned_object["error_value"])

    def lock_inputs_for_editing(self, lock: bool = True) -> None:
        """
        Locks or unlocks all the user inputs.

        Args:
            lock  ... If the inputs should be locked (True) or unlocked (False)
        """

        # TODO: find out how to disable the algorithm radio button
        #   maybe https://stackoverflow.com/questions/11472284/how-to-set-a-read-only-checkbox-in-pyside-pyqt

        # (Un)locking the number inputs
        for element in self.get_current_input_service().number_parameters_to_get_from_user:
            getattr(self, element["input_name"]).setReadOnly(lock)

        # (Un)locking the material menu
        self.material_combo_box.setEnabled(not lock)


class CustomMaterialInputDialog(QDialog):
    """
    Class defining input dialog to get custom material data from the user
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Defining all the input fields and setting their font-size
        self.name = QLineEdit(self)
        self.rho = QLineEdit(self)
        self.cp = QLineEdit(self)
        self.lmbd = QLineEdit(self)
        for input_field in [self.name, self.rho, self.cp, self.lmbd]:
            input_field.setFont(QFont("Times", 15, QFont.Bold))

        # Including validation for number values to contain only digits
        for number_input_field in [self.rho, self.cp, self.lmbd]:
            number_input_field.setValidator(QDoubleValidator())

        # Defining all the labels and setting their font-size
        name_label = QLabel("Material name")
        rho_label = QLabel("Rho [kg/m3]")
        cp_label = QLabel("Cp [J/(kg*K)]")
        lambda_label = QLabel("Lambda [W/(m*K)]")
        for label in [name_label, rho_label, cp_label, lambda_label]:
            label.setFont(QFont("Times", 15, QFont.Bold))

        # Defining which buttons will be present
        buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)

        # Including everything into a single layout
        layout = QFormLayout(self)
        layout.addRow(name_label, self.name)
        layout.addRow(rho_label, self.rho)
        layout.addRow(cp_label, self.cp)
        layout.addRow(lambda_label, self.lmbd)
        layout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        self.setWindowTitle("Custom material choice")

    def get_inputs(self):
        """
        Defines the way inputs will be returned
        """

        # Trying to parse all numerical values to floats
        # Also replacing possible commas with a dot, to be parseable
        # If unsuccessful, returning error string, which will be caught later
        try:
            returned_info = {
                "name": self.name.text(),
                "properties": {
                    "rho": float(self.rho.text().replace(",", ".")),
                    "cp": float(self.cp.text().replace(",", ".")),
                    "lmbd": float(self.lmbd.text().replace(",", "."))
                }
            }
        except ValueError:
            returned_info = "error"

        return returned_info


if __name__ == "__main__":
    # Necessary stuff for errors and exceptions to be thrown
    # Without this, the app just dies and says nothing
    sys._excepthook = sys.excepthook  # type: ignore

    def exception_hook(exctype, value, traceback):
        print(exctype, value, traceback)
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)
    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    heat_transfer_window = HeatTransferWindow()

    # heat_transfer_window.showMaximized()
    # heat_transfer_window.resize(1000, 500)
    heat_transfer_window.show()

    sys.exit(app.exec_())
