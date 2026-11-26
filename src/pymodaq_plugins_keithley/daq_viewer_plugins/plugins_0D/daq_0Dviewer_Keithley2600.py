import numpy as np

from pymodaq_utils.utils import ThreadCommand
from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins

from pymodaq_plugins_keithley.hardware.keithley2600.keithley2600_VISADriver import Keithley2600VISADriver, Keithley2600Channel, get_VISA_resources



class DAQ_0DViewer_Keithley2600(DAQ_Viewer_base):
    """ Instrument plugin class for a OD viewer.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.


    """

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

    params = comon_parameters+[
        _build_param("resource_name", "VISA resource", "list", "", limits=get_VISA_resources()),
        _build_param("channel", "Channel", "str", "A"),
        _build_param("autorange", "Autorange", "bool", True),
        ]

    def ini_attributes(self):
        #  autocompletion
        self.controller: Keithley2600VISADriver = None
        self.channel: Keithley2600Channel = None


    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

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


    def close(self):
        if self.is_master and self.controller is not None:
            self.controller.close()

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """


        data_V = self.channel.measureV()
        data_I = self.channel.measureI()
        self.dte_signal.emit(DataToExport(name='Keithley2600',
                                          data=[DataFromPlugins(name='Voltage', data=data_V,
                                                                dim='Data0D', units='V', labels=['V']),
                                                DataFromPlugins(name='Intensity', data=data_I,
                                                                dim='Data0D', units='A', labels=['I'])
                                                ]))


    def stop(self):
        pass

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        pass


if __name__ == '__main__':
    main(__file__)
