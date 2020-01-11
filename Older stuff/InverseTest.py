from NumericalInverse import *
import time

# TODO: implement this into the performance test (or make it a separate performance test)
Sim = Simulation(dt=10.0)
Problem = InverseProblem(Sim, window_span=2)
x = time.time()


while Problem.Sim.current_step_idx < Problem.Sim.max_step_idx:
    Problem.evaluate_one_inverse_step()

print("Elapsed Time: %.2f seconds." % (time.time()-x))
#fig1 = plt.figure()
#plt.plot(Problem.Sim.Exp_data.t_data, Problem.Sim.Exp_data.q_data)
#plt.plot(Problem.Sim.t, Problem.Sim.HeatFlux)
#
#fig2 = plt.figure()
#plt.plot(Problem.Sim.Exp_data.t_data, Problem.Sim.Exp_data.T_data)
#plt.plot(Problem.Sim.t, Problem.Sim.T_x0)
#
#plt.show()
