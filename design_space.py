import numpy as np
from math import pi
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.coupler import GratingCoupler
from shapely.geometry import Polygon
from gdshelpers.layout import GridLayout


from components import *
from parameters import *

# Path where you want your GDS to be saved to
savepath = r"./"


def generate_blank_gds(d_height=3000,
                       d_width=6000):
    """
    Function which creates the appropriately sized blank design space.
    :return:
    """
    # Define a design bounding box as a guide for our eyes
    outer_corners = [(0, 0), (d_width, 0), (d_width, d_height), (0, d_height)]
    polygon = Polygon(outer_corners)

    layout = GridLayout(title='Yu-Kun_Feng_2120013_Nano_Mask_13.03.2022',
                        frame_layer=99,
                        text_layer=4,
                        region_layer_type=None,
                        tight=True,
                        vertical_spacing=100,
                        vertical_alignment=1,
                        horizontal_spacing=10,
                        horizontal_alignment=10,
                        text_size=20,
                        row_text_size=15
                        )

    return layout, polygon


def grating_sweep(layout_cell):
    """
    Function which takes a layout cell as an argument
    and adds a sweep of grating coupler loopbacks
    with different periods.
    """
    # 这里可以改周期
    # periods we will sweep over
    periods = np.linspace(0.67, 0.67, 1)

    # add a new row in the layout cell
    layout_cell.begin_new_row()

    # for each period create a grating loop back and add to the loopback row
    for i, period in enumerate(periods):
        sweep_coupler_parameters = {
            'width': GRATING_COUPLER_WIDTH,
            'full_opening_angle': np.deg2rad(GRATING_FAN_ANGLE),
            'grating_period': period,
            'grating_ff': GRATING_FILL_FACTOR,
            'n_gratings': GRATING_NO_PERIODS,
            'taper_length': GRATING_TAPER_LENGTH
        }
        sweep_grating_loopback = grating_loopback(sweep_coupler_parameters, name='GRATING_' + str(i))
        layout_cell.add_to_row(sweep_grating_loopback)

    return layout_cell


def populate_gds(layout_cell, polygon):
    """
    Function which takes in the blank design space and populates it

    :param polygon: Shape of bounding box
    :param layout_cell: The blank layout cell
    :return: Populated design space
    """
    # Call the grating coupler loopback function from components,py
    grating_loopback_test = grating_loopback(coupler_parameters, name='grating1', position=(0, 0))

    # Add a new row to the layout cell and stamp out devices
    layout_cell.begin_new_row()
    layout_cell.add_to_row(grating_loopback_test, alignment='center-bottom')
    layout_cell = grating_sweep(layout_cell)

    # Generate the design space populated with the devices
    design_space_cell, mapping = layout_cell.generate_layout()

    # Add our bounding box
    design_space_cell.add_to_layer(99, polygon)

    # Save our GDS
    design_space_cell.save('{0}Yu-Kun_Feng_Nanofab_example_design.gds'.format(savepath))
    design_space_cell.show()

    return design_space_cell


# Call the function which generates a blank design space
blank_design_space, bounding_box = generate_blank_gds()

# Populate the blank gds with all of our devices
populate_gds(blank_design_space, bounding_box)
