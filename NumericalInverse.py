"""
This module is hosting class responsible for the inverse simulation
"""

import csv
import time
import numpy as np  # type: ignore
from scipy.signal import savgol_filter  # type: ignore
from NumericalForward import Simulation


class InverseSimulation(Simulation):  # later abbreviated as Prob
    """
    Class holding variables and methods to allow for the simulation of the
        inverse problem
    Inherits all the internal properties from the Simulation class
    """

    def __init__(self,
                 N: int,
                 dt: float,
                 theta: float,
                 material,
                 robin_alpha: float,
                 x0: float,
                 length: float,
                 window_span: int,
                 tolerance: float,
                 q_init: float,
                 init_q_adjustment: float,
                 adjusting_value: float,
                 experiment_data_path: str = "DATA.csv"):
        super().__init__(length=length,
                         material=material,
                         N=N,
                         theta=theta,
                         robin_alpha=robin_alpha,
                         dt=dt,
                         x0=x0)
        self.window_span = window_span
        self.tolerance = tolerance
        self.init_q_adjustment = init_q_adjustment
        self.adjusting_value = adjusting_value

        # Storing the amount of iterations we make for the simulation
        self.number_of_iterations = 0

        # fluxes to be resolved
        self.current_q_idx = 0  # initial index
        self.HeatFlux.fill(q_init)  # change initial values

        # Varibles for smoothing purposes - long list for storing whole
        #   history and stored index
        self.smooth_history = [[] for _ in range(1000)]  # type: ignore
        self.smooth_index = 0

    def __repr__(self) -> str:
        """
        Defining what should be displayed when we print the
            object of this class.
        Very useful for debugging purposes.
        """

        return f"""
            self.Sim: {self},
            self.window_span: {self.window_span},
            self.tolerance: {self.tolerance},
            """

    def evaluate_one_step(self) -> None:
        """
        Running one whole step of the inverse simulation, until the point
            we are satisfied with the results
        We are done with the step when the difference of two successive
            error values is less than the tolerance that was set in __init__

        NOTE: We are overriding parent evaluate_one_step() method to expose
            same public method.
        Superb article about overriding and its best practices can be found here:
            https://www.thedigitalcatonline.com/blog/2014/05/19/method-overriding-in-python/
        """

        # checkpoint previous state so we can revert to it
        self._make_checkpoint()
        # initial adjustments to heat flux being currently solved
        q_adj = self.init_q_adjustment
        # explicit portion
        self.HeatFlux[self.current_q_idx:self.current_q_idx+self.window_span] = self.HeatFlux[self.current_q_idx-1]
        # implicit portion
        # self.HeatFlux[self.current_q_idx+1] = self.HeatFlux[self.current_q_idx-1]
        prev_error = self._evaluate_window_error_norm()
        iter_no = 0
        while True:
            # simulate few steps
            iter_no += 1
            self._evaluate_n_steps(n_steps=self.window_span)
            new_error = self._evaluate_window_error_norm()

            # When we are satisfied with the heat flux, finish the loop,
            #   otherwise continue with adjusting it
            if abs(prev_error - new_error) < self.tolerance or new_error < self.tolerance:
                # revert simulation to last checkpoint and make only one step
                self._revert_to_checkpoint()
                super().evaluate_one_step()
                # print("Accepting Flux: {} at time {} with Error {} after {} iterations".format(
                #     self.HeatFlux[self.current_q_idx], self.t[self.current_q_idx], new_error, iter_no))

                self.number_of_iterations += iter_no
                break
            else:
                # When the new error is higher than the previous one, we want
                #   to start making smaller adjustments in the opposite direction
                # Otherwise continue with current adjustments
                if new_error > prev_error:
                    q_adj *= self.adjusting_value
                # Saving the error and reverting to the last checkpoint
                prev_error = new_error
                self._revert_to_checkpoint()

            # adjust heatflux a little in the explicit and implicit portion
            self.HeatFlux[self.current_q_idx:self.current_q_idx+self.window_span] += q_adj
            # self.HeatFlux[self.current_q_idx+1] += q_adj
        # since the current flux is adjusted enough tell the Prob to adjust
        #   next one in next SolveInverseStep call
        self.current_q_idx += 1

    def after_simulation_action(self, SimController=None):
        """
        Defines what should happen after the simulation is over

        Has access to all the variables from SimController, so can
            freely communicate with the GUI
        """

        # Determining the error margin before smoothing
        self.error_norm = self._calculate_final_error()
        print("Error norm before smoothing: {}".format(self.error_norm))

        self._perform_smoothing(SimController)

        # Determining the error margin after smoothing
        self.error_norm = self._calculate_final_error()
        print("Error norm after smoothing: {}".format(self.error_norm))

        # Show the iteration statistics
        print("amount of steps: ", self.current_step_idx)
        print("number_of_iterations", self.number_of_iterations)
        print("average of iterations", self.number_of_iterations / self.current_step_idx)

    def save_results(self) -> None:
        """
        Outputs the (semi)results of a simulation into a CSV file and names it
            accordingly.
        """

        # TODO: discuss the possible filename structure
        file_name = "Inverse-{}.csv".format(int(time.time()))

        time_data = self.t
        temp_data = self.HeatFlux

        with open(file_name, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            headers = ["Time [s]", "Heat flux [W]"]
            csv_writer.writerow(headers)

            for time_value, temp_value in zip(time_data, temp_data):
                csv_writer.writerow([time_value, temp_value])

    def plot(self, temperature_plot, heat_flux_plot):
        """
        Defining the way simulation data should be plotted
        """

        # Displaying only the data that is calculated ([:self.current_step_idx])
        temperature_plot.plot(x_values=self.t[:self.current_step_idx],
                              y_values=self.T_x0[:self.current_step_idx],
                              x_experiment_values=self.Exp_data.t_data,
                              y_experiment_values=self.Exp_data.T_data)

        heat_flux_plot.plot(x_values=self.t[:self.current_step_idx],
                            y_values=self.HeatFlux[:self.current_step_idx],
                            x_experiment_values=self.Exp_data.t_data,
                            y_experiment_values=self.Exp_data.q_data)

    def _calculate_final_error(self) -> float:
        """
        Determining error value for this simulation at its end
        """

        # TODO: review this, as it might not be correct
        calculated_heatflux = self.HeatFlux
        experiment_heatflux = np.interp(self.t, self.Exp_data.t_data, self.Exp_data.q_data)

        # Determining the shorter length, to unify the sizes
        min_length = min(len(calculated_heatflux), len(experiment_heatflux))

        error = np.sum(abs(calculated_heatflux[:min_length] - experiment_heatflux[:min_length]))/min_length
        return round(error, 3)

    def _perform_smoothing(self, SimController=None):
        """
        Is responsible for smoothing the result according to user input
            from the GUI through the shared queue
        """

        if SimController.progress_callback is not None:
            # Sending signal that we are ready for smoothing
            SimController.progress_callback.emit(2)
            # Listening for the smoothing input
            while True:
                if not SimController.queue.empty():
                    # Try to get last item from the queue sent from GUI,
                    #   which should contain commands for the smoothing
                    msg = SimController.queue.get_nowait()
                    if msg == "stop":
                        # Finishing the smoothing
                        break
                    if msg == "back":
                        # Reverting the smoothing
                        self._revert_the_smoothing()
                    elif msg.startswith("smooth_"):
                        # Performing the defined smoothing
                        # Parsing the window length from the message
                        try:
                            length = int(msg[len("smooth_"):])
                        except ValueError:
                            # Length of 1 will not do anything
                            print("unparseable window length:", length)
                            length = 1
                        self._smooth_the_result(window_length=length)

                    # Updating the plot after smoothing or reverting
                    self.plot(temperature_plot=SimController.temperature_plot,
                              heat_flux_plot=SimController.heat_flux_plot)
                else:
                    time.sleep(0.1)

    def _revert_the_smoothing(self):
        """
        Reverts the heat flux to previous value before last smoothing
        """

        if self.smooth_index > 0:
            # Renewing the heat flux value from the previous index
            #   and decreasing the index we are at
            self.HeatFlux = self.smooth_history[self.smooth_index-1][:]
            self.smooth_index -= 1
        else:
            print("cannot revert anymore")

    def _smooth_the_result(self, window_length: int = None) -> None:
        """
        Making the final result smoothed - modifying the resulting HeatFlux

        Using Savgol filter, that is getting rid of extremes
        http://scipy.github.io/devdocs/generated/scipy.signal.savgol_filter.html
        OR
        Moving average method
        https://stackoverflow.com/questions/20618804/how-to-smooth-a-curve-in-the-right-way#answer-26337730
        """

        # Choosing which method to use (manually so far)
        # The moving average seems to yield better results
        method = "moving_avg"

        # Saving the current flux to be able to revert to it later
        current_flux = self.HeatFlux[:]
        self.smooth_history[self.smooth_index] = current_flux

        # Performing the chosen smoothing
        if method == "savgol":
            if window_length is None:
                window_length = self.HeatFlux.size // 20
                # Window window_length must be odd
                if window_length % 2 == 0:
                    window_length += 1
            self.HeatFlux = savgol_filter(self.HeatFlux, window_length, 2)
        elif method == "moving_avg":
            if window_length is None:
                window_length = self.HeatFlux.size // 50
            box = np.ones(window_length)/window_length
            self.HeatFlux = np.convolve(self.HeatFlux, box, mode='same')

        # Increasing the smoothing index for the future
        self.smooth_index += 1

    def _evaluate_window_error_norm(self) -> float:
        """
        Determining the current error norm we achieved with our estimation of
            heat flux
        Comparing the measured temperatures with the temperatures resulting
            from simulation with the estimated heat flux
        """

        end_idx = self.current_q_idx+self.window_span+1
        return sum((self.T_x0[self.current_q_idx:end_idx] - self.T_data[self.current_q_idx:end_idx])**2)

    def _evaluate_n_steps(self,
                          n_steps: int = 1) -> None:
        """
        Running the parent evaluate_one_step() function multiple times
            to evaluate more steps at once
        """

        for _ in range(n_steps):
            # We must only check if we did not exceed the simulation time
            if not self.simulation_has_finished:
                super().evaluate_one_step()

    def _make_checkpoint(self) -> None:
        """
        Saving the current temperature distribution, to be able to
            run experiments with heat fluxes and not losing the
            initial state
        """

        self.checkpoint_step_idx = self.current_step_idx
        self.T_checkpoint[:] = self.T[:]

    def _revert_to_checkpoint(self) -> None:
        """
        Restoring the temperature distribution that was previously saved
        """

        self.current_step_idx = self.checkpoint_step_idx
        self.T[:] = self.T_checkpoint[:]
