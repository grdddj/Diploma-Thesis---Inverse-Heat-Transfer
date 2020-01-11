"""
This module is hosting class responsible for the inverse simulation
"""

from NumericalForward import Simulation


class InverseSimulation(Simulation):  # later abbreviated as Prob
    """
    Class holding variables and methods to allow for the simulation of the
        inverse problem
    """

    def __init__(self, N=100, dt=1.0, theta=0.5, experiment_data_path="DATA.csv",
                 material=None, robin_alpha=None, x0=None, length=None,
                 q_init=20.0, window_span=3, tolerance=1e-8):
        super().__init__(length=length,
                         material=material,
                         N=N,
                         theta=theta,
                         robin_alpha=robin_alpha,
                         dt=dt,
                         x0=x0)
        self.window_span = window_span
        self.tolerance = tolerance

        # fluxes to be resolved
        self.current_q_idx = 0  # initial index
        self.HeatFlux.fill(q_init)  # change initial values

    def __repr__(self):
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

    def evaluate_window_error_norm(self):
        """
        Determining the current error norm we achieved with our estimation of
            heat flux
        Comparing the measured temperatures with the temperatures resulting
            from simulation with the estimated heat flux
        """

        end_idx = self.current_q_idx+self.window_span+1
        return sum((self.T_x0[self.current_q_idx:end_idx] - self.T_data[self.current_q_idx:end_idx])**2)

    def evaluate_one_inverse_step(self, init_q_adjustment=10):
        """
        Running one whole step of the inverse simulation, until the point
            we are satisfied with the results
        We are done with the step when the difference of two successive
            error values is less than the tolerance that was set in __init__
        """

        self.make_checkpoint()  # checkpoint previous state so we can revert to it
        q_adj = init_q_adjustment  # initial adjustments to heat flux being currently solved
        self.HeatFlux[self.current_q_idx] = self.HeatFlux[self.current_q_idx-1]  # explicit portion
        self.HeatFlux[self.current_q_idx+1] = self.HeatFlux[self.current_q_idx-1]  # implicit portion
        prev_error = self.evaluate_window_error_norm()
        iter_no = 0
        while True:
            # simulate few steps
            iter_no += 1
            self.evaluate_n_steps(n_steps=self.window_span, increment_simulation_time=False)
            new_error = self.evaluate_window_error_norm()

            if abs(prev_error - new_error) < self.tolerance:
                self.revert_to_checkpoint()  # revert simulation to last checkpoint
                self.evaluate_one_step()  # make one step only
                # print(f"Accepting Flux: %.2f at time %.2f s with Error: %.10f after %i iterations" % (self.HeatFlux[self.current_q_idx], self.t[self.current_q_idx], new_error, iter_no))
                break  # this Flux seems to be ok so stop adjusting it
            elif new_error < prev_error:
                prev_error = new_error
                self.revert_to_checkpoint()  # revert simulation to last checkpoint
                # and keep adjusting the heat flux the by the same value because the error is getting smaller
            elif new_error > prev_error:
                prev_error = new_error
                self.revert_to_checkpoint()  # revert simulation to last checkpoint
                q_adj *= -0.7  # and make adjustments to the heat flux smaller going in the opposite direction because the error got higher last time
            self.HeatFlux[self.current_q_idx] += q_adj  # adjust heatflux a little in the explicit portion
            self.HeatFlux[self.current_q_idx+1] += q_adj  # adjust heatflux a little in the implicit portion
        self.current_q_idx += 1  # since the current flux is adjusted enough tell the Prob to adjust next one in next SolveInverseStep call
