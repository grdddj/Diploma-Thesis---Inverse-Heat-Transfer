import numpy as np    # type: ignore # this has some nice mathematics related functions
# using so called sparse linear algebra make stuff run way faster (ignoring zeros)
from scipy.sparse import csr_matrix, diags  # type: ignore
# this guy can solve equation faster by taking advantage of the sparsity
#   (it ignores zeros in the matrices)
from scipy.sparse.linalg import spsolve  # type: ignore
from experiment_data_handler import ExperimentalData
from interpolations import predefined_interp_class_factory


class Simulation:  # In later objects abreviated as Sim
    """
    theta = 0.0 - fully explicit 1st order, numerically unstable.
    theta = 0.5 - midpoint (Crank-Nicolson) 2nd order, numerically stable (probably the best choice).
    theta = 1.0 - fully implicit 1st order, numerically stable.
    """

    def __init__(self,
                 N: int,
                 dt: float,
                 theta: float,
                 robin_alpha: float,
                 x0: float,
                 length: float,
                 material,
                 experiment_data_path: str = "DATA.csv") -> None:
        self.N = int(N)  # number of elements in the model
        self.dt = dt  # fixed time step
        self.theta = theta  # fixed integration method
        self.Exp_data = ExperimentalData(experiment_data_path)

        self.rho = material.rho
        self.cp = material.cp
        self.lmbd = material.lmbd
        self.length = length
        self.robin_alpha = robin_alpha
        self.x0 = x0

        # Placeholder for the fixed simulation time points
        self.t = np.arange(self.Exp_data.t_data[0], self.Exp_data.t_data[-1] + self.dt, self.dt)
        # Current time for quick lookup in the callback
        self.current_t = 0.0
        # maximum allowed index when simulating
        self.max_step_idx = len(self.t) - 1
        # current time step index
        self.current_step_idx = 0
        # checkpoint time step index
        self.checkpoint_step_idx = 0
        # Placeholder for interpolated body temperature
        self.T_data = np.interp(self.t, self.Exp_data.t_data, self.Exp_data.T_data)
        # Placeholder for interpolated heat_flux
        self.HeatFlux = np.interp(self.t, self.Exp_data.t_data, self.Exp_data.q_data)
        # Placeholder for interpolated ambient temperature
        self.T_amb = np.interp(self.t, self.Exp_data.t_data, self.Exp_data.T_amb_data)
        # size of one element
        self.dx = self.length/N
        # x-positions of the nodes (temperatures)
        # https://docs.scipy.org/doc/numpy/reference/generated/numpy.linspace.html
        self.x = np.linspace(0, self.length, N+1)

        # temperature fields
        # https://docs.scipy.org/doc/numpy/reference/generated/numpy.empty.html
        # placeholder for actual temperatures in last evaluated step
        self.T = np.empty(N+1)
        # initialize temperature field
        self.T.fill(self.Exp_data.T_data[0])
        # placeholder for temperatures saved in checkpoint
        self.T_checkpoint = np.empty(N+1)
        # Placeholder for temperature probes data
        self.T_x0 = len(self.t)*[0.0]
        # Placeholder for temperature probes data
        self.T_x0_checkpoint = len(self.t)*[0.0]

        # Setup the right interpolation object and save initial T_x0
        self.T_x0_interpolator = predefined_interp_class_factory(self.x0, self.x)
        self.T_x0[0] = self.T_x0_interpolator(self.T)  # type: ignore
        # TODO: make it allow multiple probes at the same time

        # Finite element method: matrix assembly using 1st order continuous Galerkin elements
        # Tridiagonal sparse mass matrix (contains information about heat capacity
        #   of the elements and how their temperatures react to incoming heat)
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csr_matrix.html
        self.M = csr_matrix(self.dx*self.rho*self.cp*diags([1/6, 4/6, 1/6], [-1, 0, 1], shape=(N+1, N+1)))

        # Tridiagonal sparse stiffness matrix (contains information about heat
        #   conductivity and how the elements affect each other)
        self.K = csr_matrix((1/self.dx)*self.lmbd*diags([-1, 2, -1], [-1, 0, 1], shape=(N+1, N+1)))

        # We have to make some changes to the matrix K because we affect
        #   the body from outside
        # Here we will push Heat to the body - Neumann Boundary Condition
        self.K[0, 0] /= 2
        # Here we know the body is in contact with air so it will cool
        #   accordingly - Robin Boundary Condition
        self.K[N, N] /= 2

        # Preparing variables to store the values of some properties, that are
        #   constant during the simulation
        # placeholder for matrix A
        self.A = self.M + self.dt*self.theta*self.K
        # implicit portion of T_body contribution (Robin BC Nth node)
        self.A[-1, -1] += self.dt*self.theta*self.robin_alpha
        # Matrix b to calculate boundary vector b
        self.b_base = self.M - self.dt*(1-self.theta)*self.K
        # allocate memory for vector b
        self.b = np.empty(N+1)

    def __repr__(self) -> str:
        """
        Defining what should be displayed when we print the
            object of this class.
        Very useful for debugging purposes.
        """

        return f"""
            self.N: {self.N},
            self.dt: {self.dt},
            self.theta: {self.theta},
            self.length: {self.length},
            self.rho: {self.rho},
            self.cp: {self.cp},
            self.lmbd: {self.lmbd},
            self.length: {self.length},
            self.robin_alpha: {self.robin_alpha},
            self.x0: {self.x0},
            """

    # Function that calculates new timestep (integration step)
    def evaluate_one_step(self) -> None:
        """
        Simulating one step of the simulation
        Is using already initialised instance variables
        """

        # Evaluate new boundary vector (BC means boundary condition)

        # Assemble vector b (dot() is matrix multiplication)
        self.b = self.b_base.dot(self.T)
        # Apply explicit portion of HeatFlux (Neumann BC 1st node)
        self.b[0] += self.dt*(1-self.theta)*self.HeatFlux[self.current_step_idx]
        # Apply implicit portion of HeatFlux (Neumann BC 1st node)
        self.b[0] += self.dt*self.theta*self.HeatFlux[self.current_step_idx+1]
        # Apply explicit contribution of the body temperature (Robin BC Nth node)
        self.b[-1] -= self.dt*(1-self.theta)*self.robin_alpha*self.T[-1]
        # Apply explicit contribution of the ambient temperature (Robin BC Nth node)
        self.b[-1] += self.dt*(1-self.theta)*self.robin_alpha*self.T_amb[self.current_step_idx]
        # Apply implicit contribution of the ambient temperature (Robin BC Nth node)
        self.b[-1] += self.dt*self.theta*self.robin_alpha*self.T_amb[self.current_step_idx+1]

        # solve the equation self.A*self.T=b
        self.T = spsolve(self.A, self.b)  # solve new self.T for the new step
        self.current_step_idx += 1  # move to new timestep
        self.T_x0[self.current_step_idx] = self.T_x0_interpolator(self.T)  # type: ignore

        # Incrementing time information for the callback
        # We are assuming the self.dt stays the same all the time
        # If self.dt would be changeable, this would need to be reverted
        #   to the previous state of "self.current_t += self.dt",
        #   which however had other disadvantages (as we do not want
        #   the time being incremented when we do inverse problem probes)
        #   - it was firstly solved by passing the boolean value whether
        #     to increment time, but then there were issues with incompatible
        #     signatures of evaluate_one_step() methods in Simulation and
        #     InverseSimulation()
        self.current_t = self.dt * self.current_step_idx

    def calculate_final_error(self) -> float:
        """
        Determining error value for this simulation at its end
        """

        error = np.sum(abs(self.T_x0 - self.T_data))/len(self.t[1:])
        return round(error, 3)

    @property
    def simulation_has_finished(self) -> bool:
        """
        Deciding if the simulation has already finished or not according to
            the current step index and the maximum step index
        Is being used to determine when to stop calling the main
            evaluate_one_step method() by some higher function

        Is implemented as a property and not as a function, as it does not
            take any parameters, does not do any calculations and is
            just returning simple comparison
            - https://www.python-course.eu/python3_properties.php
        """

        # Returning True when the current index is equal or higher than
        #   the maximal one
        return self.current_step_idx >= self.max_step_idx
