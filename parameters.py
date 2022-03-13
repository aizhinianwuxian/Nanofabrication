import numpy as np
from math import pi

#################
# GENERAL PARAMS
################
WAVEGUIDE_LAYER = 3
GRATING_LAYER = 4
BEND_RADIUS = 10

###########################
# GRATING COUPLER PARAMETERS
###########################
GRATING_COUPLER_WIDTH = 0.5
GRATING_FAN_ANGLE = 1
GRATING_PERIOD = 0.670
GRATING_FILL_FACTOR = 0.5
GRATING_NO_PERIODS = 60
GRATING_TAPER_LENGTH = 700
GRATING_PITCH = 127.0

coupler_parameters = {
    'width': GRATING_COUPLER_WIDTH,
    'full_opening_angle': np.deg2rad(GRATING_FAN_ANGLE),
    'grating_period': GRATING_PERIOD,
    'grating_ff': GRATING_FILL_FACTOR,
    'n_gratings': GRATING_NO_PERIODS,
    'taper_length': GRATING_TAPER_LENGTH
}


