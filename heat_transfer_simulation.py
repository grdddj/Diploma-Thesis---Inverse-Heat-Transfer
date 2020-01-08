"""
This module is preparing simulation for the PyQT5 GUI.
Theoretically it can be used anywhere, because it just takes an arbitrary plot,
    and calls it's plot() method with the calculated data.

It is now written to support connection with PySide2 GUI in the sense of:
    a) the plot which to update
    b) the queue which to communicate over
However, it can still be used as a standalone module, because we are using
    these connections only when they are set up (are not None)
Therefore it can still be used as a performance tracker, or as a simulation
    module to whatever other GUI will connect to it

TODOS:
    - create documentation for the functions and classes
"""

from NumericalForward import Simulation
from experiment_data_handler import Material
import numpy as np
import csv
import time
import os
import threading

class Callback:
    """
    Class defining the actions that should happen when the simulation
    """

    def __init__(self, Call_at=500.0, ExperimentData=None, heat_flux_plot=None,
                 temperature_plot=None, queue=None, progress_callback=None):
        self.Call_at = Call_at  # specify how often to be called (default is every 50 seccond)
        self.last_call = 0  # placeholder fot time in which the callback was last called

        # TODO: decide whether to use experiment data from Sim all the time, or to initialize them here
        # default_ExperimentData = {"time": None, "temperature": None, "heat_flux": None}
        # self.ExperimentData = ExperimentData if ExperimentData is not None else default_ExperimentData

        # Takes reference of some plot, which it should update, and some queue,
        #   through which the GUI will send information.
        # Also save the progress communication channel to update time in GUI
        self.temperature_plot = temperature_plot
        self.heat_flux_plot = heat_flux_plot
        self.queue = queue
        self.progress_callback = progress_callback

        # We do not want to waste time by plotting the same heat_flux values
        #   over and over, so we do that only once, and flag it to be done
        self.heat_flux_already_plotted = False

        # Setting the starting simulation state as "running" - this can be changed
        #   only through the queue by input from GUI
        self.simulation_state = "running"

    def Call(self, Sim, force_update=False):
        """

        """

        # Update the time calculation is in progress
        if Sim.current_t_forward > self.last_call + self.Call_at or force_update == True:  # if it is time to comunicate with GUI then show something
            if self.temperature_plot is not None:
                # Sending only the data that is already calculated
                self.temperature_plot.plot(x_values=Sim.t[:Sim.current_step_idx],
                                         y_values=Sim.T_x0[:Sim.current_step_idx],
                                         x_experiment_values=Sim.Exp_data.t_data,
                                         y_experiment_values=Sim.Exp_data.T_data)

            # Plotting the heat flux graph at the very beginning and marking it done
            if not self.heat_flux_already_plotted and self.heat_flux_plot is not None:
                self.heat_flux_plot.plot(x_values=None,
                                         y_values=None,
                                         x_experiment_values=Sim.Exp_data.t_data,
                                         y_experiment_values=Sim.Exp_data.q_data)
                self.heat_flux_already_plotted = True

            # If callback is defined, emit positive value to increment time in GUI
            if self.progress_callback is not None:
                self.progress_callback.emit(1)

            self.last_call += self.Call_at

        # TODO: decide how often to read the queue (look if it does not affect performance a lot)
        # TODO: make sure there is not more than 1 message in queue (no leftovers)
        if self.queue is not None:
            # Try to get last item from the queue sent from GUI
            try:
                msg = self.queue.get_nowait()
                print(msg)

                # This may seem redundant, but we are guarding against some
                #   unkown msg
                if msg == "stop":
                    self.simulation_state = "stopped"
                elif msg == "pause":
                    self.simulation_state = "paused"
                elif msg == "continue":
                    self.simulation_state = "running"
            # TODO: handle this properly
            except:
                pass

        # Emit the information that simulation is not running (not to increment time)
        if self.simulation_state != "running" and self.progress_callback is not None:
            self.progress_callback.emit(0)

        # Returning the current simulation state to be handled by complete_simulation()
        return self.simulation_state

class SimulationController:
    """

    """

    def prepare_simulation(self, progress_callback, temperature_plot,
                          heat_flux_plot, queue, parameters):
        """

        """

        my_material = Material(parameters["rho"], parameters["cp"], parameters["lmbd"])
        self.Sim = Simulation(length=parameters["object_length"],
                              material=my_material,
                              N=parameters["number_of_elements"],
                              theta=parameters["theta"],
                              robin_alpha=parameters["robin_alpha"],
                              dt=parameters["dt"],
                              x0=parameters["place_of_interest"])

        self.MyCallBack = Callback(progress_callback=progress_callback,
                                      Call_at=parameters["callback_period"],
                                      temperature_plot=temperature_plot,
                                      heat_flux_plot=heat_flux_plot,
                                      queue=queue)
        return True

    def complete_simulation(self):
        """

        """

        while self.Sim.current_step_idx < self.Sim.max_step_idx:
            # Processing the callback and getting the simulation state at the same time
            # Then acting accordingly to the current state
            simulation_state = self.MyCallBack.Call(self.Sim)
            if simulation_state == "running":
                self.Sim.evaluate_one_step()
            elif simulation_state == "paused":
                time.sleep(0.1)
            elif simulation_state == "stopped":
                print("stopping")
                break

        # Calling callback at the very end, to update the plot with complete results
        self.MyCallBack.Call(self.Sim, force_update=True)

        self.ErrorNorm = np.sum(abs(self.Sim.T_x0 - self.Sim.T_data))/len(self.Sim.t[1:])
        self.ErrorNorm = round(self.ErrorNorm, 3)
        print("Error norm: {}".format(self.ErrorNorm))

    def save_results_to_csv_file(self, material="iron"):
        """
        Outputs the (semi)results of a simulation into a CSV file and names it
            accordingly.
        """

        # TODO: discuss the possible filename structure
        file_name = "Classic-{}-{}C-{}s.csv".format(material, int(self.Sim.T_x0[0]),
                                            int(self.Sim.t[-1]))

        # If for some reason there was already the same file, rather not
        #   overwrite it, but create a new file a timestamp as an identifier
        if os.path.isfile(file_name):
            file_name = file_name.split(".")[0] + "-" + str(int(time.time())) + ".csv"

        with open(file_name, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            headers = ["Time [s]", "Temperature [C]"]
            csv_writer.writerow(headers)

            for time_value, temperature in zip(self.Sim.t, self.Sim.T_x0):
                csv_writer.writerow([time_value, temperature])

def run_simulation(temperature_plot=None, heat_flux_plot=None, progress_callback=None,
             amount_of_trials=1, queue=None, parameters=None, save_results=False):
    """

    """

    simulation = SimulationController()

    simulation.prepare_simulation(progress_callback=progress_callback,
                          temperature_plot=temperature_plot,
                          heat_flux_plot=heat_flux_plot,
                          queue=queue,
                          parameters=parameters)

    simulation.complete_simulation()
    if save_results:
        simulation.save_results_to_csv_file()

    # Returning the dictionary with arbitrary information for the GUI to be notified
    return {"error_value": simulation.ErrorNorm}

if __name__ == '__main__':
    parameters = {
        "rho": 7850,
        "cp": 520,
        "lmbd": 50,
        "dt": 1,
        "object_length": 0.01,
        "place_of_interest": 0.0045,
        "number_of_elements": 100,
        "callback_period": 500,
        "robin_alpha": 13.5,
        "theta": 0.5
    }

    run_simulation(amount_of_trials=2, parameters=parameters)
