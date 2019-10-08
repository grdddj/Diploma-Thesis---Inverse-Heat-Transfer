"""
This module is responsible for defining information we want to get from user.
"""

class UserInputService:
    def __init__(self):
        self.number_parameters_to_get_from_user = [
            {"name": "Simulation step",
                "input_name": "simulation_step_input_seconds",
                "default_value": 1.0,
                "parse_function": float,
                "multiplicate_to_SI": 1,
                "unit": "seconds",
                "unit_abbrev": "s"},
            {"name": "Object length",
                "input_name": "object_length_input_centimetres",
                "default_value": 1,
                "parse_function": float,
                "multiplicate_to_SI": 0.01,
                "unit": "centimeters",
                "unit_abbrev": "cm"},
            {"name": "Position of interest",
                "input_name": "place_position_input_centimetres",
                "default_value": 0.445,
                "parse_function": float,
                "multiplicate_to_SI": 0.01,
                "unit": "centimetres",
                "unit_abbrev": "cm"},
            {"name": "Number of elements",
                "input_name": "number_of_elements_input",
                "default_value": 100,
                "parse_function": int,
                "multiplicate_to_SI": 1,
                "unit": "",
                "unit_abbrev": "-"}
        ]
