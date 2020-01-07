"""
This module is serving as a helper for a very quick linear interpolation,
    that is always happening at the one point, which is specified
    at the initialisation, and is not changed.

The previous version of this module, containing two implementations, was
    transferred to "Older stuff" folder, and the not used class
    was removed from here.

I really liked the solution of having two subclasses from the creative
    point of view, but it was adding unnecessary complexity to the code
    (also when creating the self.T_x0_interpolator in NumericalForward).
Therefore I decided to unify it in only one class - with the point that
    one more if-statement cannot ruin the performance.
"""

class Predefined_interp:
    """
    Class responsible for handling the quick interpolation in predefined
        point(s).
    """

    def __init__(self, x0, x):
        """
        Initialising all the internal variables
        """

        self.indexes = self.find_interp_indexes(x0,x)
        self.n = len(self.indexes)

        # Determining where exactly is the x0 point in relation to the
        #   two indexes around it (one being smaller than x0 and the second one bigger)
        if self.n == 1:
            self.x_diff_ratios = (x0-x[self.indexes[0]])/(x[self.indexes[0]+1] - x[self.indexes[0]])
        else:
            self.x_diff_ratios = [(x0[i]-x[self.indexes[i]])/(x[self.indexes[i]+1] - x[self.indexes[i]]) for i in range(self.n)]

    def __call__(self, y):
        """
        Returning the value in y list that corresponds to the position
            of the initial x0 value
        """

        if self.n == 1:
            return y[self.indexes[0]]+((y[self.indexes[0]+1] - y[self.indexes[0]])*self.x_diff_ratios)
        else:
            return [y[self.indexes[i]]+((y[self.indexes[i]+1] - y[self.indexes[i]])*self.x_diff_ratios[i]) for i in range(self.n)]

    @staticmethod
    def find_interp_indexes(x0, x):
        """
        Finding out the right indexes of all x0 values in the x list,
            so that we can then interpolate from list almost instantly
        """

        indexes = []

        # When the x0 is not a list or array, but individual value,
        #   transform it into a list, to stay consistent everywhere
        # NOTE: the following handling is not the cleanest one, but as we
        #   could be operating on all iterables (lists, tuples, numpy arrays),
        #   it is the easiest one to implement for everything
        try:
            len(x0)
        except TypeError:
            x0 = [x0]

        # Looping through all the x0 values (even if there is only one) and
        #   searching for the index whose value is less than the x0 value,
        #   but the further index is already bigger than the x0 value
        for item_x0 in x0:
            idx = 0
            while x[idx] < item_x0:
                idx += 1
            indexes.append(idx-1)

        return indexes
