from NumericalForward import *
# This is not functional yet!!! I will have to test it and debug it first. Do NOT implement this into the GUI!!
# I will do make incremental commits rather then complete ones since a get bad
#  conflicts in my local repository (I had to completely rebase) when we both make changes to Tests.py
# This commit should not break anything, at least it did not on my side.

class InverseProblem():  # later abbreviated as Prob
    def __init__(self, Sim, q_init=20.0, window_span=3, tolerance=1e-8):
        self.Sim = Sim  # placeholder for Sim state that the new fluxes are tested on
        self.window_span = window_span
        self.tolerance = tolerance
        # TODO: when there are high dt, value error can be encountered:
        #   ValueError: A value in x_new is above the interpolation range.

        # fluxes to be resolved
        self.current_q_idx = 0  # initial index
        self.Sim.HeatFlux.fill(q_init)  # change initial values
        self.ElapsedTime = 0

    def evaluate_window_error_norm(self):
        end_idx = self.current_q_idx+self.window_span+1
        return sum((self.Sim.T_x0[self.current_q_idx:end_idx] - self.Sim.T_data[self.current_q_idx:end_idx])**2)

    def evaluate_one_inverse_step(self, init_q_adjustment=10):
        self.Sim.make_checkpoint()  # checkpoint previous state so we can revert to it
        q_adj = init_q_adjustment  # initial adjustments to heat flux being currently solved
        self.Sim.HeatFlux[self.current_q_idx] = self.Sim.HeatFlux[self.current_q_idx-1]  # explicit portion
        self.Sim.HeatFlux[self.current_q_idx+1] = self.Sim.HeatFlux[self.current_q_idx-1]  # implicit portion
        prev_Error = self.evaluate_window_error_norm()
        iter = 0
        while True:
            # simulate few steps
            iter += 1
            self.Sim.evaluate_N_steps(N=self.window_span)
            new_Error = self.evaluate_window_error_norm()

            if abs(prev_Error - new_Error) < self.tolerance:
                self.Sim.revert_to_checkpoint()  # revert simulation to last checkpoint
                self.Sim.evaluate_one_step()  # make one step only
                #print(f"Accepting Flux: %.2f at time %.2f s with Error: %.10f after %i iterations" % (self.Sim.HeatFlux[self.current_q_idx], self.Sim.t[self.current_q_idx], new_Error, iter))
                break  # this Flux seems to be ok so stop adjusting it
            elif new_Error < prev_Error:

                prev_Error = new_Error
                self.Sim.revert_to_checkpoint()  # revert simulation to last checkpoint
                # and keep adjusting the heat flux the by the same value because the error is getting smaller
            elif new_Error > prev_Error:

                prev_Error = new_Error
                self.Sim.revert_to_checkpoint()  # revert simulation to last checkpoint
                q_adj *= -0.7  # and make adjustments to the heat flux smaller going in the opposite direction because the error got higher last time
            self.Sim.HeatFlux[self.current_q_idx] += q_adj  # adjust heatflux a little in the explicit portion
            self.Sim.HeatFlux[self.current_q_idx+1] += q_adj  # adjust heatflux a little in the implicit portion
        self.current_q_idx += 1  # since the current flux is adjusted enough tell the Prob to adjust next one in next SolveInverseStep call
