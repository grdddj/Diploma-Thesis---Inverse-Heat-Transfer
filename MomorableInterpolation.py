import numpy as np
import random

class Interpolate_1D():
    def __init__(self, x, y, start_ahead_idx=0):
        """Interpolation looking for values in vicinity of where it has found the answer before."""
        self.x = np.array(x)  # placeholder for x coordinates
        self.y = np.array(y)  # placeholder for y coordinates
        self.x_min = self.x[0]
        self.x_max = self.x[-1]
        self.ahead_idx = start_ahead_idx  # where was the last found x coordinate
        self.previous_call_x = x[0]  # last lookup value of x for case we actually need to go back

    def __call__(self,x):
        try:
            length=len(x)
            return self.calculate_list(x,length)
        except:
            return self.calculate_item(x)

    def calculate_item(self,x):

        if x > self.previous_call_x:  # check if x increased between calls
            while x > self.x[self.ahead_idx+1] and x < self.x_max:
                self.ahead_idx += 1
        elif x < self.previous_call_x:
            while x < self.x[self.ahead_idx+1] and x > self.x_min:
                self.ahead_idx -= 1

        self.previous_call_x = x

        return self.y[self.ahead_idx]+((self.y[self.ahead_idx+1] - self.y[self.ahead_idx])/(self.x[self.ahead_idx+1] - self.x[self.ahead_idx]))*(x-self.x[self.ahead_idx])

    def calculate_list(self,x,length):
        y = np.zeros(length)
        for i in range(length):
            y[i] = self.calculate_item(x[i])
        return y
