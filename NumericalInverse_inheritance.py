"""
This module is hosting class responsible for the inverse simulation
"""

import numpy as np    # type: ignore
from NumericalForward import Simulation


class InverseSimulation(Simulation):  # later abbreviated as Prob
    """
    Class holding variables and methods to allow for the simulation of the
        inverse problem
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

        # fluxes to be resolved
        self.current_q_idx = 0  # initial index
        self.HeatFlux.fill(q_init)  # change initial values

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
        self.HeatFlux[self.current_q_idx] = self.HeatFlux[self.current_q_idx-1]
        # implicit portion
        self.HeatFlux[self.current_q_idx+1] = self.HeatFlux[self.current_q_idx-1]
        prev_error = self._evaluate_window_error_norm()
        iter_no = 0
        while True:
            # simulate few steps
            iter_no += 1
            self._evaluate_n_steps(n_steps=self.window_span)
            new_error = self._evaluate_window_error_norm()

            if abs(prev_error - new_error) < self.tolerance:
                # revert simulation to last checkpoint
                self._revert_to_checkpoint()
                # make one step only
                super().evaluate_one_step()
                # print(f"Accepting Flux: %.2f at time %.2f s with Error: %.10f after %i iterations" % (self.HeatFlux[self.current_q_idx], self.t[self.current_q_idx], new_error, iter_no))
                # this Flux seems to be ok so stop adjusting it
                break
            elif new_error < prev_error:
                prev_error = new_error
                # revert simulation to last checkpoint
                self._revert_to_checkpoint()
                # and keep adjusting the heat flux the by the same value because
                #   the error is getting smaller
            elif new_error > prev_error:
                prev_error = new_error
                # revert simulation to last checkpoint
                self._revert_to_checkpoint()
                # and make adjustments to the heat flux smaller going in the
                #   opposite direction because the error got higher last time
                q_adj *= -0.7
            # adjust heatflux a little in the explicit portion
            self.HeatFlux[self.current_q_idx] += q_adj
            # adjust heatflux a little in the implicit portion
            self.HeatFlux[self.current_q_idx+1] += q_adj
        # since the current flux is adjusted enough tell the Prob to adjust
        #   next one in next SolveInverseStep call
        self.current_q_idx += 1

    def calculate_final_error(self) -> float:
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

        step = 0
        while self.current_step_idx < self.max_step_idx and step < n_steps:
            super().evaluate_one_step()
            step += 1

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
