from NumericalForward import *
# This is not functional yet!!! I will have to test it and debug it first. Do NOT implement this into the GUI!!
# I will do make incremental commits rather then complete ones since a get bad
#  conflicts in my local repository (I had to completely rebase) when we both make changes to Tests.py
# This commit should not break anything, at least it did not on my side.

class InverseProblem():  # later abbreviated as Prob
    def __init__(self, Sim, dt=1.0, q_init=10.0, data_T=None, data_true_q=None):
        self.Sim = Sim  # placeholder for Sim state that the new fluxes are tested on
        if data_T is not None:
            self.data_T = data_T  # true data from the experiment made into callable object (look into NumericalForward.py)

        # fluxes to be resolved
        self.current_q_idx = 0  # index of heat flux than is being currently solved
        self.data_q = np.arange(data_T.x[0], data_T.x[-1], dt)
        self.data_q.fill(q_init)  # initial guess of fluxes
        self.data_true_q = data_true_q  # optional - true fluxes for validation if testing

def EvaluateWindowErrorNorm(Prob, window_span):
    return sum(Prob.Sim.T_x0[-window_span:-1] - Prob.data_T(Prob.Sim.t[-window_span,-1]))

def SolveInverseStep(Prob, dt=1, theta=0.5, window_span=3, init_q_adjustment=10, tolerance=0.5):
    t_stop = Prob.data_T.x[-1]
    Prob.Sim.make_checkpoint()  # checkpoint previous state so we can revert to it
    prev_Error = EvaluateWindowErrorNorm(Prob, window_span)  # calculate error norm between experiment and simulation

    while True:
        q_adj = init_q_adjustment  # initial adjustments to heat flux being currently solved
        data_q[Prob.current_q_idx] += q_adj  # adjust heatflux a little

        # simulate few steps to see what q_adj did to simulation
        Prob.Sim.HeatFlux = MakeDataCallable(data_t, data_q)  # update Fluxes callable in Simulation with new guess
        iter = 0
        while Prob.Sim.t[-1] < t_stop and iter <= window_span:
            EvaluateNewStep(Prob.Sim, min(dt, t_stop-Prob.Sim.t[-1]), theta)
            iter += 1

        new_Error = EvaluateWindowErrorNorm(Prob, window_span)  # calculate new error norm between experiment and simulation
        if new_Error <= tolerance:
            break  # this Flux seems to be ok so stop adjusting it
        elif new_Error < prev_Error:
            Prob.Sim.revert_to_checkpoint()  # revert simulation to last checkpoint
            # and keep adjusting the heat flux the by the same value because the error is getting smaller
        elif new_Error > prev_Error:
            Prob.Sim.revert_to_checkpoint()  # revert simulation to last checkpoint
            q_adj /= -2  # and make adjustments to the heat flux smaller going in the opposite direction because the error got higher last time
        prev_Error = new_Error
    Prob.current_q_idx += 1  # since the current flux is adjusted enough tell the Prob to adjust next one in next SolveInverseStep call
