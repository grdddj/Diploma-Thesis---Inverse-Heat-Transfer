import numpy as np  # this has some nice mathematics related functions
from scipy.sparse import csr_matrix, diags  # using so called sparse linear algebra make stuff run way faster (ignoring zeros)
from scipy.sparse.linalg import spsolve    # this guy can solve equation faster by taking advantage of the sparsity (it ignores zeros in the matrices)
from experiment_data_handler import Experimental_data, Material
from interpolations import Predefined_interp_for_float, Predefined_interp_for_list

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
    @profile
    def evaluate_one_step(self):
        """
        Simulating one step of the simulation
        Is using already initialised instance variables
        """

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
        """
        Running the evaluate_one_step() function multiple times
        """

        step = 0
        while self.current_step_idx < self.max_step_idx and step < N:
            self.evaluate_one_step()
            step += 1

    def make_checkpoint(self):
        """
        Saving the current temperature distribution, to be able to
            run experiments with heat fluxes and not losing the
            initial state
        """

        self.checkpoint_step_idx = self.current_step_idx
        self.T_checkpoint[:] = self.T[:]

    def revert_to_checkpoint(self):
        """
        Restoring the temperature distribution that was previously saved
        """

        self.current_step_idx = self.checkpoint_step_idx
        self.T[:] = self.T_checkpoint[:]
