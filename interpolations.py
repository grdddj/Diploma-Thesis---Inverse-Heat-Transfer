"""
This module is serving as a helper for a very quick linear interpolation,
    that is always happening at the one point, which is specified
    at the initialisation, and is not changed

The previous version of this module, containing two implementations, was
    transferred to "Older stuff" folder, and the not used class
    was removed from here.

Long time I was thinking about unifying those two subclasses (for float and
    for list) into only one (which would mean there could be only one class
    in total) - and I actually did it ("interpolations_no_subclasses"),
    because it is reducing the code complexity in return of just one more
    if statement.
In the end however, I decided to leave it like this, because it is a
    masterpiece of yours, and also it will be another speed-improving
    technique that I could describe in the thesis itself.
"""

from typing import List, Union


class PredefinedInterp:
    """
    Base class for interpolation, that is responsible for setting up the
        important internal variables.
    """

    def __init__(self,
                 x0: Union[list, float],
                 x: list):
        self.indexes = self.find_interp_indexes(x0, x)
        self.n = len(self.indexes)

        # Determining where exactly is the x0 point in relation to the
        #   two indexes around it (one being smaller than x0 and the second one bigger)
        if self.n == 1:
            self.x_diff_ratios = (x0-x[self.indexes[0]])/(x[self.indexes[0]+1] - x[self.indexes[0]])
        else:
            self.x_diff_ratios = [(x0[i]-x[self.indexes[i]])/(x[self.indexes[i]+1] - x[self.indexes[i]]) for i in range(self.n)]  # type: ignore

    @staticmethod
    def find_interp_indexes(x0: Union[list, float],
                            x: list) -> list:
        """
        Finding out the right indexes of all x0 values in the x list,
            so that we can then interpolate from list almost instantly

        NOTE: the method changed to static, as it is not utilising self at all
        """

        indexes = []

        # When the x0 is not a list or array, but individual value,
        #   transform it into a list, to stay consistent everywhere
        # NOTE: the following handling is not the cleanest one, but as we
        #   could be operating on all iterables (lists, tuples, numpy arrays),
        #   it is the easiest one to implement for everything
        try:
            len(x0)  # type: ignore
        except TypeError:
            x0 = [x0]

        # Looping through all the x0 values (even if there is only one) and
        #   searching for the index whose value is less than the x0 value,
        #   but the further index is already bigger than the x0 value
        for item_x0 in x0:  # type: ignore
            idx = 0
            while x[idx] < item_x0:
                idx += 1
            indexes.append(idx-1)

        return indexes


class PredefinedInterpForFloat(PredefinedInterp):
    """
    Class set to interpolate only one float value

    Is the basic class for when we perform the temperature measurements
        only at one place
    """

    def __call__(self, y: list) -> float:
        return y[self.indexes[0]]+((y[self.indexes[0]+1] - y[self.indexes[0]])*self.x_diff_ratios)


class PredefinedInterpForList(PredefinedInterp):
    """
    Class set to interpolate the whole list of multiple float values

    Comes into play when we want to determine more values at the same time
        (the temperature should be determined at more places)
    """

    def __call__(self, y: list) -> List[float]:
        return [y[self.indexes[i]]+((y[self.indexes[i]+1] - y[self.indexes[i]])*self.x_diff_ratios[i]) for i in range(self.n)]
