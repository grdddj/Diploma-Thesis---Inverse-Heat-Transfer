
# QUESTION: What is the reason of this line - to run the file without writing "python3" in front of it?
# ANSWER: Yes, although I am not sure if it works with all operating systems, (Linux terminal: ./script.py starts the script without python3 infront of it)
# NOTE: It has to be the fist line in the file otherwise it will not work!

import numpy as np  # this has some nice mathematics related functions
from scipy.sparse import csr_matrix, diags  # using so called sparse linear algebra make stuff run way faster (ignoring zeros)
from scipy.sparse.linalg import spsolve    # this guy can solve equation faster by taking advantage of the sparsity (it ignores zeros in the matrices)
from experiment_data_handler import Experimental_data, Material
from interpolations import Predefined_interp_for_float, Predefined_interp_for_list
import matplotlib.pyplot as plt  # some ploting backend - but you can change to whatever you need

# material properties - we can make some basic database of those, but I  would leave an option to define custom ones
# Yeah, the DB will be provided, with the ability of defining custom materials.
# I had an idea of implementing the material characteristics as a funtion,
#   but I am afraid it would make the calculations slower, if we had to
#   calculate it after each temperature change. What do you think - is it
#   even possible to find temperature-depending functions for rho, cp and lmbd
#   at least for some common materials?
# We could find some temperature depending material properties, but the way we would
#   have to handle the calculatinos would be super-slow when using python directly as we do here.
#   It would basically require to recalculate the Sim.M and Sim.K every step and the induced non-linearity of it
#   would require insertion of Newton type solver rigth in between the time-stepping and the linear spsolve.
#   Then imagine the inverse solver around all of that stuff... ouch!
#   We might try that with the FeniCS library though, which would handle bunch of these stuff automatically,
#   but the slowness might be still quite painful (usually these kind of complexity requires more CPU cores, and heavy paralelisation).
#   I would start with the constant propperty and then see how fast it can be implemented.

# here we do the finite element method magic and define some placeholders to handle stuff
class Simulation:  # In later objects abreviated as Sim
    """
    theta = 0.0 - fully explicit 1st order, numerically unstable.
    theta = 0.5 - midpoint (Crank-Nicolson) 2nd order, numerically stable (probably the best choice).
    theta = 1.0 - fully implicit 1st order, numerically stable.
    """

    def __init__(self, N=100, dt=1.0, theta=0.5, experiment_data_path="DATA.csv",
                 material=None, robin_alpha=None, x0=None, length=None):
        self.N = int(N)  # number of elements in the model
        self.dt = dt  # fixed time step
        self.theta = theta  # fixed integration method
        self.Exp_data = Experimental_data(experiment_data_path)

        # A lot of properties can be either chosen (in GUI), or defined in a CSV
        # TODO: let user choose one or another, at least in material
        self.rho = material.rho if material is not None else self.Exp_data.Mat.rho
        self.cp = material.cp if material is not None else self.Exp_data.Mat.cp
        self.lmbd = material.lmbd if material is not None else self.Exp_data.Mat.lmbd
        self.length = length if length is not None else self.Exp_data.Length
        self.robin_alpha = robin_alpha if robin_alpha is not None else self.Exp_data.RobinAlpha
        self.x0 = x0 if x0 is not None else self.Exp_data.x0

        self.t = np.arange(self.Exp_data.t_data[0], self.Exp_data.t_data[-1] + self.dt, self.dt)  # Placeholder for the fixed simulation time points
        self.current_t_forward = 0 # Storing current time for quick lookup in the forward callback
        self.current_t_inverse = 0 # Storing current time for quick lookup in the inverse callback
        self.max_step_idx = len(self.t) - 1  # maximum allowed index when simulating
        self.current_step_idx = 0  # current time step index
        self.checkpoint_step_idx = 0  # checkpoint time step index
        self.T_data = np.interp(self.t, self.Exp_data.t_data, self.Exp_data.T_data)
        self.HeatFlux = np.interp(self.t, self.Exp_data.t_data, self.Exp_data.q_data)  # Placeholder for interpolated heat_flux
        self.T_amb = np.interp(self.t, self.Exp_data.t_data, self.Exp_data.T_amb_data)  # Placeholder for interpolated ambient temperature
        self.dx = self.length/N  # size of one element
        # https://docs.scipy.org/doc/numpy/reference/generated/numpy.linspace.html
        self.x = np.linspace(0, self.length, N+1)  # x-positions of the nodes (temperatures)

        # temperature fields
        # https://docs.scipy.org/doc/numpy/reference/generated/numpy.empty.html
        self.T = np.empty(N+1)  # placeholder for actual temperatures in last evaluated step
        self.T.fill(self.Exp_data.T_data[0])  # initialize temperature field
        self.T_checkpoint = np.empty(N+1)  # placeholder for temperatures saved in checkpoint
        self.T_x0 = len(self.t)*[0.0]  # Placeholder for temperature probes data
        self.T_x0_checkpoint = len(self.t)*[0.0]  # Placeholder for temperature probes data

        # This way it does not spend any time on if statements during simulation
        try:
            len(self.x0)
            self.T_x0_interpolator = Predefined_interp_for_list(self.x0, self.x)
        except:
            self.T_x0_interpolator = Predefined_interp_for_float(self.x0, self.x)
        self.T_x0[0] = self.T_x0_interpolator(self.T)  # save initial T_x0
        # TODO: make it allow multiple probes at the same time

        # Finite element method: matrix assembly using 1st order continuous Galerkin elements
        # Tridiagonal sparse mass matrix (contains information about heat capacity of the elements and how their temperatures react to incoming heat)
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csr_matrix.html
        self.M = csr_matrix(self.dx*self.rho*self.cp*diags([1/6, 4/6, 1/6], [-1, 0, 1], shape=(N+1, N+1)))

        # Tridiagonal sparse stiffness matrix (contains information about heat conductivity and how the elements affect each other)
        self.K = csr_matrix((1/self.dx)*self.lmbd*diags([-1, 2, -1], [-1, 0, 1], shape=(N+1, N+1)))

        # We have to make some changes to the matrix K because we affect the body from outside
        self.K[0,0] /= 2  # Here we will push Heat to the body - Neumann Boundary Condition
        self.K[N,N] /= 2  # Here we know the body is in contact with air so it will cool accordingly - Robin Boundary Condition

        # Preparing variables to store the values of some properties, that are constant during the simulation
        self.A = self.M + self.dt*self.theta*self.K  # placeholder for matrix A
        self.A[-1,-1] += self.dt*self.theta*self.robin_alpha  # implicit portion of T_body contribution (Robin BC Nth node)
        self.b_base = self.M - self.dt*(1-self.theta)*self.K  # Matrix b to calculate boundary vector b
        self.b = np.empty(N+1)  # allocate memory for vector b

    # Function that calculates new timestep (integration step)

    def evaluate_one_step(self):
        # evaluate new boundary vector (BC means boundary condition)
        self.b = self.b_base.dot(self.T)  # Assemble vector b (dot() is matrix multiplication)
        self.b[0] += self.dt*(1-self.theta)*self.HeatFlux[self.current_step_idx]  # apply explicit portion of HeatFlux (Neumann BC 1st node)
        self.b[0] += self.dt*self.theta*self.HeatFlux[self.current_step_idx+1]  # apply implicit portion of HeatFlux (Neumann BC 1st node)
        self.b[-1] -= self.dt*(1-self.theta)*self.robin_alpha*self.T[-1]  # apply explicit contribution of the body temperature (Robin BC Nth node)
        self.b[-1] += self.dt*(1-self.theta)*self.robin_alpha*self.T_amb[self.current_step_idx]  # apply explicit contribution of the ambient temperature (Robin BC Nth node)
        self.b[-1] += self.dt*self.theta*self.robin_alpha*self.T_amb[self.current_step_idx+1]  # apply implicit contribution of the ambient temperature (Robin BC Nth node)

        # solve the equation self.A*self.T=b
        self.T = spsolve(self.A, self.b)  # solve new self.T for the new step
        #self.T_x0.append(np.interp(self.Exp_data.x0, self.x, self.T))  # save data from the temperature probes  # switich off for now
        self.current_step_idx += 1  # move to new timestep
        self.T_x0[self.current_step_idx] = self.T_x0_interpolator(self.T)
        self.current_t_forward += self.dt # Updating time info for the callback

    def evaluate_N_steps(self, N=1):
        step = 0
        while self.current_step_idx < self.max_step_idx and step < N:
            self.evaluate_one_step()
            step += 1

    def make_checkpoint(self):
        self.checkpoint_step_idx = self.current_step_idx
        self.T_checkpoint[:] = self.T[:]

    def revert_to_checkpoint(self):
        self.current_step_idx = self.checkpoint_step_idx
        self.T[:] = self.T_checkpoint[:]

# This is quite dumm callback, but I guess you are going to change this part a lot
# In forward simulation there perhaps does not have to be callback at all
# If you want to kill simulaton, click into terminal and quickly hit CTRL+C, the 0.01 pause should leave enough time to register the Interupt
class DefaultCallBack:
    def __init__(self, Call_at=100.0, plot_limits=[0, 5000, 20, 40], x0=0, ExperimentData=None):
        self.Call_at = Call_at  # specify how often to be called (default is every 50 seccond)
        self.last_call = 0  # placeholder fot time in which the callback was last called
        self.plot_limits = plot_limits  # axis limits to make plot looking "better"
        self.x0 = x0  # x positinon of the temperature we are interested in
        self.TempHistoryAtPoint_x0 = []  # We can be saving data of temperature from specific point in space (x0)
        self.ExperimentData = ExperimentData

    def Call(self, Sim):
        # https://docs.scipy.org/doc/numpy/reference/generated/numpy.interp.html
        self.TempHistoryAtPoint_x0.append(np.interp(self.x0, Sim.x, Sim.T))  # interpolate temperature value at position x0 from point around and save it
        if Sim.t[-1] > self.last_call + self.Call_at:  # if it is time to comunicate with GUI then show something
            plt.clf()
            plt.axis(self.plot_limits)
            plt.plot(Sim.t[1:], self.TempHistoryAtPoint_x0)
            if self.ExperimentData is not None:
                plt.plot(self.ExperimentData[0], self.ExperimentData[1])
            plt.pause(0.01)
            print(f"Temperature at x0: {self.TempHistoryAtPoint_x0[-1]} at time {Sim.t[-1]} flux: {Sim.HeatFlux(Sim.current_step_idx)}")
            self.last_call += self.Call_at

# This is the function which actually simulates all the timesteps by calling the EvaluateNewStep over and over till t_stop is reached
# theta = 0.5 makes so called Crank-Nicolson method which is 2nd order accurate in time and stable as hell so we can take large steps and be fast
def ForwardSimulation(Sim, T0=0, t_start=0, t_stop=100, CallBack=DefaultCallBack()):
    Sim.t.append(t_start)  # push start time into time placeholder inside Simulation class
    Sim.T.fill(T0)  # fill initial temperature with value of T0
    # main simulation loop (no time step adatpation yet - but it can be done later, it would make it even faster and more awesome)
    while Sim.t[-1] < t_stop:
        Sim.EvaluateNewStep()  # evaluate Temperaures at step k
        if CallBack is not None:
            # Do whatever the callback needs to do
            CallBack.Call(Sim)
