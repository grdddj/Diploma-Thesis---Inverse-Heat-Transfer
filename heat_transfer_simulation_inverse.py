"""
This module is serving for running the Inverse simulation.
It can be run separately or from the GUI, in which case it will be updating the plot.
"""

from NumericalInverse import InverseProblem
from NumericalForward import Simulation
from experiment_data_handler import Material
import numpy as np
import csv
import time
import os

class InverseCallback:
    """

    """

    def __init__(self, Call_at=500.0, ExperimentData=None, heat_flux_plot=None,
                 temperature_plot=None,queue=None, progress_callback=None):
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

        # Setting the starting simulation state as "running" - this can be changed
        #   only through the queue by input from GUI
        self.simulation_state = "running"

    def Call(self, Sim, force_update=False):
        """

        """

        # Update the time calculation is in progress
        if Sim.current_t_inverse > self.last_call + self.Call_at or force_update == True:  # if it is time to comunicate with GUI then show something
            if self.temperature_plot is not None:
                self.temperature_plot.plot(x_values=Sim.t[:Sim.current_step_idx],
                                         y_values=Sim.T_x0[:Sim.current_step_idx],
                                         x_experiment_values=Sim.Exp_data.t_data,
                                         y_experiment_values=Sim.Exp_data.T_data)

            if self.heat_flux_plot is not None:
                # Showing only the already calculated part of the heat flux
                # calculated_length = len(Sim.T_x0)
                self.heat_flux_plot.plot(x_values=Sim.t[:Sim.current_step_idx],
                                         y_values=Sim.HeatFlux[:Sim.current_step_idx],
                                         x_experiment_values=Sim.Exp_data.t_data,
                                         y_experiment_values=Sim.Exp_data.q_data)

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

        # Returning the current ismulation state to be handled by make_sim_step()
        return self.simulation_state

class InverseSimulationController:
    """

    """

    def prepare_inverse_simulation(self, progress_callback, temperature_plot,
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

        self.Problem = InverseProblem(self.Sim,
                                      q_init=20,
                                      window_span=parameters["window_span"],
                                      tolerance=parameters["tolerance"])

        self.MyCallBack = InverseCallback(progress_callback=progress_callback,
                                          Call_at=parameters["callback_period"],
                                          temperature_plot=temperature_plot,
                                          heat_flux_plot=heat_flux_plot,
                                          queue=queue)

    def complete_inverse_simulation(self):
        """

        """

        while self.Problem.Sim.current_step_idx < self.Problem.Sim.max_step_idx:
            # Processing the callback and getting the simulation state at the same time
            # Then acting accordingly to the current state
            simulation_state = self.MyCallBack.Call(self.Sim)
            if simulation_state == "running":
                self.Problem.evaluate_one_inverse_step()
            elif simulation_state == "paused":
                import random
                if random.random() < 0.1:
                    print("sleep")
                time.sleep(0.1)
            elif simulation_state == "stopped":
                print("stopping")
                break

        # Calling callback at the very end, to update the plot with complete results
        self.MyCallBack.Call(self.Problem.Sim, force_update=True)

        # TODO: review this, as it might not be correct
        calculated_heatflux = self.Problem.Sim.HeatFlux
        experiment_heatflux = np.interp(self.Sim.t, self.Sim.Exp_data.t_data, self.Sim.Exp_data.q_data)

        # Determining the shorter length, to unify the sizes
        min_length = min(len(calculated_heatflux), len(experiment_heatflux))

        try:
            self.ErrorNorm = np.sum(abs(calculated_heatflux[:min_length] - experiment_heatflux[:min_length]))/min_length
            self.ErrorNorm = round(self.ErrorNorm, 3)
        except ValueError:
            # This is raised when the lengths of compared lists are not the same (for some reason)
            self.ErrorNorm = "unknown"

        print("Error norm: {}".format(self.ErrorNorm))

    def save_results_to_csv_file(self, material="iron"):
        """
        Outputs the (semi)results of a simulation into a CSV file and names it
            accordingly.
        """

        # TODO: discuss the possible filename structure
        file_name = "Inverse-{}-{}C-{}s.csv".format(material, int(self.Sim.T_x0[0]),
                                                    int(self.Sim.t[-1]))

        # If for some reason there was already the same file, rather not
        #   overwrite it, but create a new file a timestamp as an identifier
        if os.path.isfile(file_name):
            file_name = file_name.split(".")[0] + "-" + str(int(time.time())) + ".csv"

        with open(file_name, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            headers = ["Time [s]", "Temperature [C]"]
            csv_writer.writerow(headers)

            for time_value, temperature in zip(self.Sim.t, self.Sim.HeatFlux):
                csv_writer.writerow([time_value, temperature])


def run_inverse_simulation(temperature_plot=None, heat_flux_plot=None, progress_callback=None,
             amount_of_trials=1, queue=None, parameters=None, save_results=False):
    """

    """

    app = InverseSimulationController()

    app.prepare_inverse_simulation(progress_callback=progress_callback,
                          temperature_plot=temperature_plot,
                          heat_flux_plot=heat_flux_plot,
                          queue=queue,
                          parameters=parameters)

    app.complete_inverse_simulation()
    if save_results:
        app.save_results_to_csv_file()

    return {"error_value": app.ErrorNorm}

if __name__ == '__main__':
    parameters = {
        "rho": 7850,
        "cp": 520,
        "lmbd": 50,
        "dt": 50,
        "object_length": 0.01,
        "place_of_interest": 0.0045,
        "number_of_elements": 100,
        "callback_period": 500,
        "robin_alpha": 13.5,
        "theta": 0.5,
        "window_span": 2,
        "tolerance": 1e-05
    }

    run_inverse_simulation(parameters=parameters)
