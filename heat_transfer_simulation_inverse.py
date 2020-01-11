"""
This module is serving for running the Inverse simulation.
It can be run separately or from the GUI, in which case
    it will be updating the plot.
"""

import time
import numpy as np
from NumericalInverse import InverseProblem
from NumericalForward import Simulation
from experiment_data_handler import Material
from heat_transfer_simulation_utilities import Callback, run_simulation


class InverseSimulationController:
    """
    Holding variables and defining methods for the inverse simulation
    """

    def __init__(self):
        self.Sim = None
        self.MyCallBack = None
        self.error_norm = None

    def prepare_simulation(self, progress_callback, temperature_plot,
                           heat_flux_plot, queue, parameters):
        """
        Prepare the Simulation, InverseProblem and Callback objects
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

        self.MyCallBack = Callback(progress_callback=progress_callback,
                                   call_at=parameters["callback_period"],
                                   temperature_plot=temperature_plot,
                                   heat_flux_plot=heat_flux_plot,
                                   queue=queue)

    def complete_simulation(self):
        """
        Running all the simulation steps, if not stopped
        """

        while self.Sim.current_step_idx < self.Sim.max_step_idx:
            # Processing the callback and getting the simulation state
            # Then acting accordingly to the current state
            simulation_state = self.MyCallBack(self.Sim)
            if simulation_state == "running":
                self.Problem.evaluate_one_inverse_step()
            elif simulation_state == "paused":
                time.sleep(0.1)
            elif simulation_state == "stopped":
                print("stopping")
                break

        # Calling callback at the very end, to update the plot with complete results
        self.MyCallBack(self.Sim, force_update=True)

        # Getting the error margin
        self.error_norm = self.calculate_error()
        print("Error norm: {}".format(self.error_norm))

    def calculate_error(self):
        """
        Determining the error margin of the simulation
        TODO: review this, as it might not be correct
        """

        calculated_heatflux = self.Sim.HeatFlux
        experiment_heatflux = np.interp(self.Sim.t, self.Sim.Exp_data.t_data,
                                        self.Sim.Exp_data.q_data)

        # Determining the shorter length, to unify the sizes
        min_length = min(len(calculated_heatflux), len(experiment_heatflux))

        try:
            error = np.sum(abs(calculated_heatflux[:min_length] - experiment_heatflux[:min_length]))/min_length
            return round(error, 3)
        except ValueError:
            # This is raised when the lengths of compared lists are not
            #   the same (for some reason)
            return "unknown"


def simulate_from_gui(parameters_from_gui, progress_callback):
    """
    Starts the whole simulation with the inputs from GUI
    """

    simulation = InverseSimulationController()
    result = run_simulation(**parameters_from_gui, simulation=simulation,
                            progress_callback=progress_callback,
                            time_data_location="t", quantity_data_location="HeatFlux",
                            algorithm="Inverse", quantity_and_unit="Heat flux [W]")
    return result


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

    simulation = InverseSimulationController()
    run_simulation(simulation=simulation, parameters=parameters,
                   time_data_location="t", quantity_data_location="HeatFlux",
                   algorithm="Inverse", quantity_and_unit="Heat flux [W]",
                   save_results=False)
