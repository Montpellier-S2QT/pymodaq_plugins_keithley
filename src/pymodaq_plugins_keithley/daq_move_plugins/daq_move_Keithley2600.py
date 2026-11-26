from typing import Union, List, Dict
from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun,
                                                          main, DataActuatorType, DataActuator)

from pymodaq_utils.utils import ThreadCommand  # object used to send info back to the main thread
from pymodaq_gui.parameter import Parameter
from collections.abc import Callable

import pyvisa
from pymodaq_plugins_keithley.hardware.keithley2600.keithley2600_VISADriver import Keithley2600VISADriver, Keithley2600Channel, get_VISA_resources


# Helper functions
def _build_param(name, title, type, value, limits=None, unit=None, **kwargs):
    params = {}
    params["name"] = name
    params["title"] = title
    params["type"] = type
    params["value"] = value
    if limits is not None:
        params["limits"] = limits
    if unit is not None:
        params["suffix"] = unit
        params["siPrefix"] = True
    for argn, argv in kwargs.items():
        params[argn] = argv
    return params


class DAQ_Move_Keithley2600(DAQ_Move_base):
    """ Instrument plugin class for an actuator.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through inheritance via
    DAQ_Move_base. It makes a bridge between the DAQ_Move module and the Python wrapper of a particular instrument.

    Compatible devices: Keithley 2600 series sourcemeters
    Tested on: Keithley 2636B / PyMoDAQ 5.1.1 / Ubuntu 24.04 LTS
    Installation instructions: no special drivers other than PyVISA

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
    """

    # General parameters
    is_multiaxes = True
    _axis_names: Union[List[str], Dict[str, int]] = ["Voltage", "Current"]
    _controller_units: Union[str, List[str]] = ["V", "A"]
    _epsilons: Union[float, List[float]] = [0.01, 1e-6]
    data_actuator_type = DataActuatorType.DataActuator

    # Parameter tree
    params = comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilons) + [
            _build_param("resource_name", "VISA resource", "list", "", limits=get_VISA_resources()),
            _build_param("channel", "Channel", "str", "A"),
            _build_param("autorange", "Autorange", "bool", True),
            _build_param("current_limit", "Current limit (A)", "float", "0.0001"),
            _build_param("voltage_limit", "Voltage limit (V)", "float", "100"),
            ]


    def ini_attributes(self):
        # For autocompletion
        self.controller: Keithley2600VISADriver = None
        self.channel: Keithley2600Channel = None

    @property
    def move_function(self):
        if self.axis_name == "Voltage":
            return self.channel.sourceV
        elif self.axis_name == "Current":
            return self.channel.sourceI

    @property
    def meas_function(self):
        if self.axis_name == "Voltage":
            return self.channel.measureV
        elif self.axis_name == "Current":
            return self.channel.measureI


    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = DataActuator(data=self.meas_function(), units=self.axis_unit)
        pos = self.get_position_with_scaling(pos)
        return pos


    def user_condition_to_reach_target(self) -> bool:
        """ Implement a condition for exiting the polling mechanism and specifying that the
        target value has been reached

       Returns
        -------
        bool: if True, PyMoDAQ considers the target value has been reached
        """
        return True


    def close(self):
        """Terminate the communication protocol"""
        if self.is_master:
            self.controller.close()


    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        # Dispatch arguments
        name = param.name()
        val = param.value()
        unit = param.opts.get("suffix")

        if name == "current_limit":
            self.channel.Ilimit = val

        if name == "voltage_limit":
            self.channel.Vlimit = val


    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        # Get initialization parameters
        resource_name = self.settings["resource_name"]
        channel = self.settings["channel"]
        autorange = self.settings["autorange"]

        # If stand-alone device, initialize controller object
        if self.is_master:

            # Initialize device
            self.controller = Keithley2600VISADriver(resource_name)
            initialized = True

        # If slave device, retrieve controller object
        else:
            self.controller = controller
            initialized = True

        # Initialize channel
        self.channel = self.controller.create_channel(channel_name=channel,
                                                      autorange=autorange)
        
        # Initialization successful
        info = "Keithey 2600 initialization finished."
        return info, initialized


    def move_abs(self, value: DataActuator):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """
        value = self.check_bound(value)  #if user checked bounds, the defined bounds are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply scaling if the user specified one
        self.move_function(value.value(self.axis_unit))
        self.emit_status(ThreadCommand('Update_Status', [f"Moving abs to {value}"]))


    def move_rel(self, value: DataActuator):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position
        value = self.set_position_relative_with_scaling(value)
        self.move_function(self.target_value.value(self.axis_unit))
        self.emit_status(ThreadCommand('Update_Status', [f"Moving ref by {value}"]))


    def move_home(self):
        """Call the reference method of the controller"""
        pass


    def stop_motion(self):
        """Stop the actuator and emits move_done signal"""
        self.channel.off()
        self.emit_status(ThreadCommand('Update_Status', [f"Stopping movement"]))


if __name__ == '__main__':
    main(__file__)
