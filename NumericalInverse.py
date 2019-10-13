from NumericalForward import *
# This is not functional yet!!! I will have to test it and debug it first. Do NOT implement this into the GUI!!
# I will do make incremental commits rather then complete ones since a get bad
#  conflicts in my local repository (I had to completely rebase) when we both make changes to Tests.py
# This commit should not break anything, at least it did not on my side.

class InverseProblem():  # later abbreviated as Prob
    def __init__(self, Sim, dt=1.0, q_init=0.0, data_T=None, data_true_q=None):
        self.Sim = Sim  # placeholder for Sim state that the new fluxes are tested on
        # TODO: when there are high dt, value error can be encountered:
        #   ValueError: A value in x_new is above the interpolation range.
        self.dt = dt  # placeholder for time step dt

        if data_T is not None:
            self.data_T = data_T  # true data from the experiment made into callable

        data_t = np.arange(data_T.x[0], data_T.x[-1], dt)
        Sim.t.append(data_t[0])  # push start time into time placeholder inside Simulation class
        Sim.T.fill(data_T.y[0])  # fill initial temperature with value of T0
        Sim.T_x0.append(np.interp(Sim.x0, Sim.x, Sim.T))  # save data from the temperature probes

        # fluxes to be resolved
        self.current_q_idx = 0  # initial index
        self.Sim.HeatFlux = MakeDataCallable(data_t, data_t)  # rewrite whatever HeatFlux is in Sim
        self.Sim.HeatFlux.y.fill(q_init)  # change initial values
        self.ElapsedTime = 0
        # validation stuff
        self.data_true_q = data_true_q  # optional - true fluxes for validation if testing

def EvaluateWindowErrorNorm(Prob, window_span):
    return sum((Prob.Sim.T_x0[-window_span:] - Prob.data_T(Prob.Sim.t[-window_span:]))**2)

def SolveInverseStep(Prob, theta=0.5, window_span=3, init_q_adjustment=10, tolerance=1e-8, CallBack=None):
    t_stop = Prob.data_T.x[-1]
    Prob.Sim.make_checkpoint()  # checkpoint previous state so we can revert to it
    q_adj = init_q_adjustment  # initial adjustments to heat flux being currently solved
    Prob.Sim.HeatFlux.y[Prob.current_q_idx] = Prob.Sim.HeatFlux.y[Prob.current_q_idx-1]  # explicit portion
    Prob.Sim.HeatFlux.y[Prob.current_q_idx+1] = Prob.Sim.HeatFlux.y[Prob.current_q_idx-1]  # implicit portion
    prev_Error = EvaluateWindowErrorNorm(Prob, window_span)
    iter = 0
    while True:
        # simulate few steps
        iter += 1
        step = 0
        while Prob.Sim.t[-1] < t_stop and step < window_span:
            EvaluateNewStep(Prob.Sim, min(Prob.dt, t_stop-Prob.Sim.t[-1]), theta)
            step += 1
        # calculate error between simulation and experimental data
        new_Error = EvaluateWindowErrorNorm(Prob, window_span)

        if abs(prev_Error - new_Error) < tolerance:
            Prob.Sim.revert_to_checkpoint()  # revert simulation to last checkpoint
            # print(f"Accepting Flux: %.2f at time %.2f s with Error: %.10f after %i iterations" % (Prob.Sim.HeatFlux.y[Prob.current_q_idx], Prob.Sim.t[-1], new_Error, iter))
            EvaluateNewStep(Prob.Sim, min(Prob.dt, t_stop-Prob.Sim.t[-1]), theta)  # make one step only
            # TODO:# CallBack should be here probably
            break  # this Flux seems to be ok so stop adjusting it
        elif new_Error < prev_Error:

            prev_Error = new_Error
            Prob.Sim.revert_to_checkpoint()  # revert simulation to last checkpoint
            # and keep adjusting the heat flux the by the same value because the error is getting smaller
        elif new_Error > prev_Error:

            prev_Error = new_Error
            Prob.Sim.revert_to_checkpoint()  # revert simulation to last checkpoint
            q_adj *= -0.7  # and make adjustments to the heat flux smaller going in the opposite direction because the error got higher last time
        Prob.Sim.HeatFlux.y[Prob.current_q_idx] += q_adj  # adjust heatflux a little in the explicit portion
        Prob.Sim.HeatFlux.y[Prob.current_q_idx+1] += q_adj  # adjust heatflux a little in the implicit portion
    Prob.current_q_idx += 1  # since the current flux is adjusted enough tell the Prob to adjust next one in next SolveInverseStep call
