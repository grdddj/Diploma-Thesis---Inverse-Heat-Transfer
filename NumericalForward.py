#!/usr/bin/env python3
# QUESTION: What is the reason of this line - to run the file without writing "python3" in front of it?
# ANSWER: Yes, although I am not sure if it works with all operating systems, (Linux terminal: ./script.py starts the script without python3 infront of it)
# NOTE: It has to be the fist line in the file otherwise it will not work!

import numpy as np  # this has some nice mathematics related functions
from scipy.sparse import csr_matrix, diags  # using so called sparse linear algebra make stuff run way faster (ignoring zeros)
from scipy.sparse.linalg import spsolve    # this guy can solve equation faster by taking advantage of the sparsity (it ignores zeros in the matrices)
import scipy.interpolate as interpolate  # well this guy is quite obvious
import matplotlib.pyplot as plt  # some ploting backend - but you can change to whatever you need

def Default_HeatFlux(t):
    return 1e5*np.sin(2*np.pi*t*(1/10))
    # QUESTION: This is just an arbitrary value?
    # ASWER: Yes, I was using this to experiment before I have added the DATA.csv

def Default_AmbientTemperature(t):
    return 21
    # QUESTION: Why are we supplying the 't' parameter?
    # ANSWER: The kwarg AmbientTemperature in Simulation.__init__ should be function of time,
    #   even if it returns value that is constant in time.
    # I wanted to have temperatures in Kelvins, but as long as we do not calculate
    #   radiation, Celsius should be fine. Maybe storing lower numbers can make
    #   it marginally faster, but it is just a wild guess
    # You can totally have Kelvins, the algorithm should be compatible with it,
    #   but the DATA.csv were in degrees of Celsia so I put 21 in.
    #   You can include some switch-buton which converts the teperature to kelvins right after it reads them from the DATA.csv.
    #   In general the experimantal data can come with Celsia, Kelvins or even Fahrenheit.
    # The lower numbers should not make speed difference,
    #   it is all floats anyway so I think it has to do the same
    #   amount of work (bitwise speaking) when performing the calculations.

# We will want to evaluate experimental data between points - makes stuff quite easier to handle
def MakeDataCallable(x,y):
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.interp1d.html#scipy.interpolate.interp1d
    # This interpolation is linear by default
    return interpolate.interp1d(x, y)

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
class Material:
    def __init__(self, rho, cp, lmbd):
        self.rho = rho  # Mass density
        self.cp = cp  # Specific heat capacity
        self.lmbd = lmbd  # Heat conductivity

# Default Material
Steel = Material(7850, 520, 50)

# here we do the finite element method magic and define some placeholders to handle stuff
class Simulation:  # In later objects abreviated as Sim
    def __init__(self, Length=1, Material=Steel, N=10, HeatFlux=Default_HeatFlux, AmbientTemperature=Default_AmbientTemperature, RobinAlpha=10):
        self.L = Length  # length (thisckness of one-dimensional wall)
        self.Mat = Material  # material data
        self.N = int(N)  # number of elements in the model
        #  https://docs.scipy.org/doc/numpy/reference/generated/numpy.empty.html
        self.T = np.empty(N+1)  # placeholder for actual temperatures in last evaluated step
        self.T_record = []  # Placeholder for the temperature history (list of numpy arrays)
        self.HeatFlux = HeatFlux  # Placeholder for heat flux at boundary (callable function)
        self.RobinAlpha = RobinAlpha  # constant coeficient of heat transfer for the right boundary (Robin's boundary condition)
        self.T_amb = AmbientTemperature  # ambient temperature callable function
        self.t = []  # placeholder for the simulation point in time
        self.dx = Length/N  # size of one element
        # https://docs.scipy.org/doc/numpy/reference/generated/numpy.linspace.html
        self.x = np.linspace(0, Length, N+1)  # x-positions of the nodes (temperatures)

        # Finite element method: matrix assembly using 1st order continuous Galerkin elements
        # (you dont have to understand the few following lines right now - I will explain to you in person what is happening bellow)
        # ----------------------------------------------------------------------------------------------------
        # Tridiagonal sparse mass matrix (contains information about heat capacity of the elements and how their temperatures react to incoming heat)
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csr_matrix.html
        self.M = csr_matrix(self.dx*self.Mat.rho*self.Mat.cp*diags([1/6, 4/6, 1/6], [-1, 0, 1], shape=(N+1, N+1)))

        # Tridiagonal sparse stiffness matrix (contains information about heat conductivity and how the elements affect each other)
        self.K = csr_matrix((1/self.dx)*self.Mat.lmbd*diags([-1, 2, -1], [-1, 0, 1], shape=(N+1, N+1)))

        # We have to make some changes to the matrix K because we affect the body from outside
        self.K[0,0] /= 2  # Here we will push Heat to the body - Neumann Boundary Condition
        self.K[N,N] /= 2  # Here we know the body is in contact with air so it will cool accordingly - Robin Boundary Condition

# Function that calculates new timestep (Again do not worry about math right now, that will come later)
# theta is value between 0.0 and 1.0 (float) which gradualy mutates the method from fully explicit (0.0) to fully implicit (1.0)
# so we have a lot of methods packed in one function
def EvaluateNewStep(Sim, dt, theta):
    A = Sim.M + dt*theta*Sim.K  # assemble sparse matrix A from the K and M (see in above class what they are)
    b = (Sim.M - dt*(1-theta)*Sim.K).dot(Sim.T)  # Assemble vector b (matmul is matrix multiplication)

    # apply the Neumann Boundary Condition - telling it how much heat is going in from the side
    b[0] += dt*(1-theta)*Sim.HeatFlux(Sim.t[-1])  # from step k-1 - explicit portion of HeatFlux
    b[0] += dt*theta*Sim.HeatFlux(Sim.t[-1] + dt)  # from step k - implicit portion of HeatFlux

    # apply Robin Boundary Condition - telling it how much it cools down because of the air on the other side
    # you surely know the equation alpha*(T_body - T_amb) for convective heat trasfer - that what is it doing here
    b[-1] -= dt*(1-theta)*Sim.RobinAlpha*Sim.T[-1]  # from step k-1 - explicit portion of T_body contribution
    A[-1,-1] += dt*theta*Sim.RobinAlpha  # from step k - implicit portion of T_body contribution
    b[-1] += dt*(1-theta)*Sim.RobinAlpha*Sim.T_amb(Sim.t[-1])  # from step k-1 - explicit portion of T_amb contribution
    b[-1] += dt*theta*Sim.RobinAlpha*Sim.T_amb(Sim.t[-1] + dt)  # from step k-1 - implicit portion of T_amb contribution

    # solve the equation A*Sim.T=b
    return spsolve(A, b)  # solve Sim.T for the new step k

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
            print(f"Temperature at x0: {self.TempHistoryAtPoint_x0[-1]} at time {Sim.t[-1]} flux: {Sim.HeatFlux(Sim.t[-1])}")
            self.last_call += self.Call_at

# This is the function which actually simulates all the timesteps by calling the EvaluateNewStep over and over till t_stop is reached
# theta = 0.5 makes so called Crank-Nicolson method which is 2nd order accurate in time and stable as hell so we can take large steps and be fast
def ForwardSimulation(Sim, theta=0.5, T0=0, dt=0.01, t_start=0, t_stop=100, CallBack=DefaultCallBack()):
    Sim.t.append(t_start)  # push start time into time placeholder inside Simulation class
    Sim.T.fill(T0)  # fill initial temperature with value of T0
    Sim.T_record.append(Sim.T)  # save initial step
    # main simulation loop (no time step adatpation yet - but it can be done later, it would make it even faster and more awesome)
    while Sim.t[-1] < t_stop:
        Sim.T = EvaluateNewStep(Sim, dt, theta)  # evaluate Temperaures at step k
        Sim.T_record.append(Sim.T)  # push it to designated list
        Sim.t.append(Sim.t[-1] + dt)  # push time step to its list
        if CallBack is not None:
            # Do whatever the callback needs to do and stopping the simulation
            #   if the callback returns False
            if not CallBack.Call(Sim):
                break
