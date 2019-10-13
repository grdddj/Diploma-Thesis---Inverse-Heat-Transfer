import numpy as np

class Interpolate_1D():

    def __init__(self, x, y, start_ahead_idx = 0):
        """This will look forward from point where it found the value
           last time. We will never be looking for values that are infront"""
        self.x = np.array(x)  # placeholder for x coordinates
        self.y = np.array(y)  # placeholder for y coordinates
        self.x_min = x[0]
        self.x_max = x[-1]
        self.max_idx = len(x)  # maximum index of data
        self.ahead_idx = start_ahead_idx  # where was the last found x coordinate
        self.previous_call_x = x[0]  # last lookup value of x for case we actually need to go back

    def __call__(self,x,record_call=True):
        try:
            len(x)
            return self.calculate_list(x,record_call)
        except:
            return self.calculate_item(x,record_call)

    def calculate_item(self,x,record_call):
        idx = self.ahead_idx  # look around from here

        if x >= self.x_max:
            return self.y[-2]+((self.y[-1] - self.y[-2])/(self.x[-1] - self.x[-2]))*(x-self.x[-2])
        elif x <= self.x_min:
            return self.y[0]+((self.y[1] - self.y[0])/(self.x[1] - self.x[0]))*(x-self.x[0])
        elif x > self.previous_call_x:  # check if x increased between calls
            while not x <= self.x[idx+1]:
                idx += 1
        elif x < self.previous_call_x:
            while not x >= self.x[idx+1]:
                idx -= 1

        if record_call:
            self.ahead_idx = idx
            self.previous_call_x = x
        # calculate value
        return self.y[idx]+((self.y[idx+1] - self.y[idx])/(self.x[idx+1] - self.x[idx]))*(x-self.x[idx])

    def calculate_list(self,x,record_call):
        y=[]
        for item in x:
            y.append(self.calculate_item(item,record_call))
        return np.array(y)
