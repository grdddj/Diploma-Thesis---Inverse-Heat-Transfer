"""
This module is serving as a helper for a very quick linear interpolation,
    that is always happening at the one point, which is specified
    at the initialisation, and is not changed.
"""

from typing import List, Union


class PredefinedInterp:
    """
    Base class for interpolation, hosting just one helper method
    """

    @staticmethod
    def find_interp_index(x0: float, x: list):
        """
        Finding out the right indexes of x0 value in the x list,
            so that we can then interpolate from list almost instantly
        """

        # Searching for the index whose value is less than the x0 value,
        #   but the further index is already bigger than the x0 value
        idx = 0
        while x[idx] < x0:
            idx += 1

        return idx - 1


class PredefinedInterpForFloat(PredefinedInterp):
    """
    Class set to interpolate only one float value

    Is the basic class for when we perform the temperature measurements
        only at one place
    """

    def __init__(self, x0: float, x: list):
        """
        Initialising all the internal variables
        """

        self.index = self.find_interp_index(x0, x)

        # Determining where exactly is the x0 point in relation to the
        #   two indexes around it (one being smaller than x0 and the second one bigger)
        self.x_diff_ratio = (x0-x[self.index])/(x[self.index+1] - x[self.index])

    def __call__(self, y: list) -> float:
        return y[self.index]+((y[self.index+1] - y[self.index])*self.x_diff_ratio)


class PredefinedInterpForList(PredefinedInterp):
    """
    Class set to interpolate the whole list of multiple float values

    Comes into play when we want to determine more values at the same time
        (the temperature should be determined at more places)
    """

    def __init__(self, x0: list, x: list):
        """
        Initialising all the internal variables
        """

        self.indexes = [self.find_interp_index(x0_point, x) for x0_point in x0]
        self.n = len(self.indexes)
        self.x_diff_ratios = [(x0[i]-x[self.indexes[i]])/(x[self.indexes[i]+1] - x[self.indexes[i]]) for i in range(self.n)]

    def __call__(self, y: list) -> List[float]:
        return [y[self.indexes[i]]+((y[self.indexes[i]+1] - y[self.indexes[i]])*self.x_diff_ratios[i]) for i in range(self.n)]


def predefined_interp_class_factory(x0: Union[float, list], x: list):
    """
    According to the value(s) we want to interpolate in, returning the
        right object for interpolating that specific data type (float or list)

    Utilizing the factory design pattern
    """

    try:
        iter(x0)  # type: ignore
        return PredefinedInterpForList(x0, x)  # type: ignore
    except TypeError:
        return PredefinedInterpForFloat(x0, x)  # type: ignore
