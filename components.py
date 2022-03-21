import numpy as np
from math import pi
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.coupler import GratingCoupler
from gdshelpers.parts.splitter import MMI
from gdshelpers.parts.port import Port
from gdshelpers.parts.spiral import Spiral
from gdshelpers.parts.interferometer import MachZehnderInterferometerMMI
from gdshelpers.parts.resonator import RingResonator
from gdshelpers.parts.optical_codes import QRCode

from parameters import *

# Do not delete or change!
# TODO: Find a less hacky fix SC 01/02/22
CORNERSTONE_GRATING_IDENTIFIER = 0


class CornerstoneGratingCoupler:
    """Class for linear grating coupler design
    compliant with Cornerstone fab.
    SC/QP 12/01/22"""

    def __init__(self):
        """
        :param origin: Position of the instance of the class
        :param coupler_params: Coupler parameters for this instance
        """
        self.coupler_params = None
        self.origin = None
        self.port = None
        self.cell = None

    def create_coupler(self, origin, coupler_params={'width': 0.5,
                                                     'full_opening_angle': np.deg2rad(0.8),
                                                     'n_gratings': 60,
                                                     'taper_length': 700,
                                                     'grating_period': 0.67,
                                                     'grating_ff': 0.5
                                                     }, name=None):
        """
        Function to create the Cornerstone compliant grating cell.
        """
        GC_proto = GratingCoupler.make_traditional_coupler(origin=origin,
                                                           extra_triangle_layer=False,
                                                           **coupler_params)
        GC_proto_shape_obj = GC_proto.get_shapely_object()
        GC_outline = GC_proto_shape_obj.convex_hull
        GC_teeth = GratingCoupler.make_traditional_coupler(origin=origin,
                                                           extra_triangle_layer=True,
                                                           **coupler_params)
        global CORNERSTONE_GRATING_IDENTIFIER
        cell = Cell("GC_period_{}_coords_{}_{}_{}".format(coupler_params['grating_period'],
                                                          origin[0],
                                                          origin[1], CORNERSTONE_GRATING_IDENTIFIER))
        CORNERSTONE_GRATING_IDENTIFIER += 1

        # add outline to draw layer
        cell.add_to_layer(WAVEGUIDE_LAYER, GC_outline)
        cell.add_to_layer(GRATING_LAYER, GC_teeth)

        self.cell = cell
        self.port = GC_proto.port

        return self

    @classmethod
    def create_cornerstone_coupler_at_port(self, port, **kwargs):
        """
        SC 20/01/22
        Make a grating coupler at a port.

        This function is identical to :func:`create_coupler`. Parameters of the port
        can also be overwritten via keyword arguments.

        :param port: The port at which the coupler shall be created.
        :type port: Port
        :param kwargs: Keyword arguments passed to :func:`make_traditional_coupler`.
        :return: The constructed traditional grating coupler.
        :rtype: GratingCoupler
        """

        if 'width' not in kwargs:
            kwargs['width'] = port.width

        if 'angle' not in kwargs:
            kwargs['angle'] = port.angle

        coup_params = kwargs

        return self.create_coupler(self,
                                   origin=port.origin,
                                   coupler_params=coup_params)


def grating_checker(gratings):
    """
    Utility function which checks that grating couplers are
    appropriately placed. SC 20/01/22.
    :param gratings: List of all the gratings in the device
    :return: x_diff, y_diff so these can be used to adjust position of gratings
    """

    y_diff = np.around(gratings[0].port.origin[1], 9) - np.around(gratings[1].port.origin[1], 9)
    x_diff = np.around(gratings[0].port.origin[0], 9) - np.around(gratings[1].port.origin[0], 9)

    if y_diff != 0:
        print(" \n \n WARNING: The gratings being checked have a y separation of {}  \n \n ".format(y_diff))
    if np.abs(x_diff) != GRATING_PITCH:
        print(" \n \n WARNING: The gratings being checked have a x separation of {}. Recommended is {} \n \n "
              .format(np.abs(x_diff), GRATING_PITCH))

    return x_diff, y_diff


def grating_loopback(coupler_params, position=(0, 0), name='GRATING_LOOPBACK'):
    """
    Function which returns a cell containing
    two connected gratings.
    :param position: x,y coordinates of loopback - leave as (0,0), overwritten by layout
    :param coupler_params: dict of specs for coupler
    :param name: String which uniquely identifies the cell
    :return: Cell containing the loopback
    """

    grating_loopback_cell = Cell(name)

    # Create the cell that we are going to add to

    position = (0, 0)
    left_grating_d1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d1.cell)

    wg_d1_1 = Waveguide.make_at_port(port=left_grating_d1.port)
    wg_d1_1.add_straight_segment(length=100)
    wg_d1_1.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    spiral_0 = Spiral.make_at_port(wg_d1_1.current_port, num=2, gap=5, inner_gap=50)
    wg_d1_2 = Waveguide.make_at_port(port=spiral_0.out_port)
    wg_d1_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=100)
    wg_d1_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=127)
    wg_d1_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=300 - 15 + 90-33)

    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d1_1, spiral_0, wg_d1_2)

    right_grating_d3 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d1_2.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d3.cell)


   # Spiral d2

    position = (231, 0)
    left_grating_d2 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d2.cell)

    wg_d2_1 = Waveguide.make_at_port(port=left_grating_d2.port)
    wg_d2_1.add_straight_segment(length=100)
    wg_d2_1.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    spiral_1 = Spiral.make_at_port(wg_d2_1.current_port, num=5, gap=5, inner_gap=50)
    wg_d2_2 = Waveguide.make_at_port(port=spiral_1.out_port)
    wg_d2_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=100)
    wg_d2_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=127)
    wg_d2_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=300-15+90)

    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d2_1, spiral_1, wg_d2_2)

    right_grating_d2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d2_2.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d2.cell)

    position = (480, 0)
    left_grating_d3 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d3.cell)

    wg_d3_1 = Waveguide.make_at_port(port=left_grating_d3.port)
    wg_d3_1.add_straight_segment(length=100)
    wg_d3_1.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    spiral_2 = Spiral.make_at_port(wg_d3_1.current_port, num=8, gap=5, inner_gap=50)
    wg_d3_2 = Waveguide.make_at_port(port=spiral_2.out_port)
    wg_d3_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=100)
    wg_d3_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=127)
    wg_d3_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=300 - 15 + 90 + 33)

    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d3_1, spiral_2, wg_d3_2)

    right_grating_d3 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d3_2.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d3.cell)

    position = (640, 0)
    left_grating_d4 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d4.cell)
    wg_d4_1 = Waveguide.make_at_port(port=left_grating_d4.port)
    wg_d4_1.add_straight_segment(length=200)
    wg_d4_1.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=127/2 - 10)
    resonator_1 = RingResonator.make_at_port(wg_d4_1.current_port, gap=1, radius=20)
    wg_d4_1.add_straight_segment(length=127 / 2 -10).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d4_1.add_straight_segment(length=200)

    right_grating_d4 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d4_1.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d4.cell)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d4_1, resonator_1)

    position = (800, 0)
    left_grating_d5 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d5.cell)
    wg_d5_1 = Waveguide.make_at_port(port=left_grating_d5.port)
    wg_d5_1.add_straight_segment(length=200)
    wg_d5_1.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=127 / 2 - 10)
    resonator_2 = RingResonator.make_at_port(wg_d5_1.current_port, gap=1, radius=35)
    wg_d5_1.add_straight_segment(length=127 / 2 - 10).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d5_1.add_straight_segment(length=200)

    right_grating_d5 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d5_1.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d5.cell)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d5_1, resonator_2)

    position = (960, 0)
    left_grating_d6 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d6.cell)
    wg_d6_1 = Waveguide.make_at_port(port=left_grating_d6.port)
    wg_d6_1.add_straight_segment(length=200)
    wg_d6_1.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=127 / 2 - 10)
    resonator_3 = RingResonator.make_at_port(wg_d6_1.current_port, gap=1, radius=50)
    wg_d6_1.add_straight_segment(length=127 / 2 - 10).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d6_1.add_straight_segment(length=200)

    right_grating_d6 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d6_1.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d6.cell)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d6_1, resonator_3)

    position = (1120, 0)
    left_grating_d7 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d7.cell)
    wg_d7_1 = Waveguide.make_at_port(port=left_grating_d7.port)
    wg_d7_1.add_straight_segment(length=200)
    wg_d7_1.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=19)
    mzi_1 = MachZehnderInterferometerMMI.make_at_port(port=wg_d7_1.current_port, splitter_length=33, splitter_width=7,
                                                      bend_radius=20, upper_vertical_length=50,
                                                      lower_vertical_length=100,
                                                      horizontal_length=30)
    wg_d7_2 = Waveguide.make_at_port(port=mzi_1.port)

    wg_d7_2.add_straight_segment(length=19).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d7_2.add_straight_segment(length=200)

    right_grating_d7 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d7_2.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d7.cell)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d7_1, mzi_1, wg_d7_2)

    position = (1410, 0)
    left_grating_d8 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d8.cell)
    wg_d8_1 = Waveguide.make_at_port(port=left_grating_d8.port)
    wg_d8_1.add_straight_segment(length=200)
    wg_d8_1.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=19)
    mzi_2 = MachZehnderInterferometerMMI.make_at_port(port=wg_d8_1.current_port, splitter_length=33, splitter_width=7,
                                                      bend_radius=20, upper_vertical_length=100,
                                                      lower_vertical_length=100,
                                                      horizontal_length=30)
    wg_d8_2 = Waveguide.make_at_port(port=mzi_2.port)

    wg_d8_2.add_straight_segment(length=19).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d8_2.add_straight_segment(length=200)

    right_grating_d8 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d8_2.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d8.cell)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d8_1, mzi_2, wg_d8_2)

    position = (1700, 0)
    left_grating_d9 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d9.cell)
    wg_d9_1 = Waveguide.make_at_port(port=left_grating_d9.port)
    wg_d9_1.add_straight_segment(length=200)
    wg_d9_1.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=19)
    mzi_3 = MachZehnderInterferometerMMI.make_at_port(port=wg_d9_1.current_port, splitter_length=33, splitter_width=7,
                                                      bend_radius=20, upper_vertical_length=150,
                                                      lower_vertical_length=100,
                                                      horizontal_length=30)
    wg_d9_2 = Waveguide.make_at_port(port=mzi_3.port)

    wg_d9_2.add_straight_segment(length=19).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d9_2.add_straight_segment(length=200)

    right_grating_d9 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d9_2.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d9.cell)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d9_1, mzi_3, wg_d9_2)

    position = (1990, 0)
    left_grating_d10 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d10.cell)
    wg_d10_1 = Waveguide.make_at_port(port=left_grating_d10.port)
    wg_d10_1.add_straight_segment(length=100)
    wg_d10_1.add_straight_segment(length=200).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d10_1.add_straight_segment(length=127-10-10).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d10_1.add_straight_segment(length=200).add_straight_segment(length=100)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d10_1)
    right_grating_d10 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d10_1.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d10.cell)

    position = (2150, 0)
    left_grating_d11 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d11.cell)
    wg_d11_1 = Waveguide.make_at_port(port=left_grating_d11.port)
    wg_d11_1.add_straight_segment(length=100)
    wg_d11_1.add_straight_segment(length=200).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d11_1.add_straight_segment(length=127 - 10 + 127 - 10).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d11_1.add_straight_segment(length=200).add_straight_segment(length=100)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d11_1)
    right_grating_d11 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d11_1.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d11.cell)

    position = (2440, 0)
    left_grating_d12 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_d12.cell)
    wg_d12_1 = Waveguide.make_at_port(port=left_grating_d12.port)
    wg_d12_1.add_straight_segment(length=100)
    wg_d12_1.add_straight_segment(length=200).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d12_1.add_straight_segment(length=127 - 10 + 127 + 127 -10).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_d12_1.add_straight_segment(length=200).add_straight_segment(length=100)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_d12_1)
    right_grating_d12 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_d12_1.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_d12.cell)



    position = (2900, 0)
    left_grating_a1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_a1.cell)
    wg_a1_1 = Waveguide.make_at_port(port=left_grating_a1.port)
    wg_a1_1.add_straight_segment(length=200).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_a1_1.add_straight_segment(length=100)
    spiral_a1 = Spiral.make_at_port(wg_a1_1.current_port, num=8, gap=5, inner_gap=50)
    wg_a1_2 = Waveguide.make_at_port(port=spiral_a1.out_port)
    wg_a1_2.add_straight_segment(length=100)
    wg_a1_2.add_bend(angle=pi / 2, radius=BEND_RADIUS).add_straight_segment(length=180 - 12)
    wg_a1_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=400 - 80)
    mzi_a1 = MachZehnderInterferometerMMI.make_at_port(port=wg_a1_2.current_port, splitter_length=33, splitter_width=7,
                                                      bend_radius=15, upper_vertical_length=50,
                                                      lower_vertical_length=100,
                                                      horizontal_length=30)
    wg_a1_3 = Waveguide.make_at_port(port=mzi_a1.port)
    wg_a1_3.add_straight_segment(length=26)
    wg_a1_3.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=200)
    right_grating_a1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_a1_3.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_a1.cell)

    wg_a1_7 = Waveguide.make_at_port(port=mzi_a1.port)
    wg_a1_7.add_straight_segment(length=26+127)
    wg_a1_7.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=200)
    right_grating_a1_1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_a1_7.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_a1_1.cell)


    position = (3154, 0)
    left_grating_a1_1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_a1_1.cell)
    wg_a1_4 = Waveguide.make_at_port(port=left_grating_a1_1.port)
    wg_a1_4.add_straight_segment(length=200).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_a1_4.add_straight_segment(length=100)
    spiral_a1_1 = Spiral.make_at_port(wg_a1_4.current_port, num=8, gap=5, inner_gap=50)
    wg_a1_5 = Waveguide.make_at_port(port=spiral_a1_1.out_port)
    wg_a1_5.add_straight_segment(length=100).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_a1_5.add_straight_segment(length=109).add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg_a1_5.add_straight_segment(length=20).add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg_a1_5.add_straight_segment(length=109+190-2).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_a1_5.add_straight_segment(length=20)

    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_a1_1, spiral_a1, wg_a1_2, mzi_a1, wg_a1_3, wg_a1_4,
                                       wg_a1_5, spiral_a1_1, wg_a1_7)

    position = (3846, 0)
    left_grating_aa1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_aa1.cell)
    wg_aa1_1 = Waveguide.make_at_port(port=left_grating_aa1.port)
    wg_aa1_1.add_straight_segment(length=200).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_aa1_1.add_straight_segment(length=100)
    spiral_aa1 = Spiral.make_at_port(wg_aa1_1.current_port, num=8, gap=5, inner_gap=50)
    wg_aa1_2 = Waveguide.make_at_port(port=spiral_aa1.out_port)
    wg_aa1_2.add_straight_segment(length=100)
    wg_aa1_2.add_bend(angle=pi / 2, radius=BEND_RADIUS).add_straight_segment(length=180 - 12)
    wg_aa1_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=400 - 80)
    wg_aa1_8 = Waveguide.make_at_port(port=wg_aa1_2.current_port)
    wg_aa1_8.add_straight_segment(length=88)
    resonator_aa1 = RingResonator.make_at_port(wg_aa1_8.current_port, gap=1, radius=50)
    wg_aa1_8.add_straight_segment(length=88)
    mzi_aa1 = MachZehnderInterferometerMMI.make_at_port(port=wg_aa1_2.current_port, splitter_length=33,
                                                        splitter_width=7,
                                                        bend_radius=15, upper_vertical_length=50,
                                                        lower_vertical_length=100,
                                                        horizontal_length=30)
    wg_aa1_3 = Waveguide.make_at_port(port=mzi_aa1.port)
    wg_aa1_3.add_straight_segment(length=26)
    wg_aa1_3.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=200)
    right_grating_aa1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_aa1_3.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_aa1.cell)

    wg_aa1_7 = Waveguide.make_at_port(port=mzi_aa1.port)
    wg_aa1_7.add_straight_segment(length=26 + 127)
    wg_aa1_7.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=200)
    right_grating_aa1_1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_aa1_7.current_port,
        **coupler_params)

    grating_loopback_cell.add_cell(right_grating_aa1_1.cell)

    position = (4100, 0)
    left_grating_aa1_1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_aa1_1.cell)
    wg_aa1_4 = Waveguide.make_at_port(port=left_grating_aa1_1.port)
    wg_aa1_4.add_straight_segment(length=200).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_aa1_4.add_straight_segment(length=100)
    spiral_a1_1 = Spiral.make_at_port(wg_aa1_4.current_port, num=8, gap=5, inner_gap=50)
    wg_aa1_5 = Waveguide.make_at_port(port=spiral_a1_1.out_port)
    wg_aa1_5.add_straight_segment(length=100).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_aa1_5.add_straight_segment(length=109).add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg_aa1_5.add_straight_segment(length=20).add_bend(angle=pi / 2, radius=BEND_RADIUS)
    wg_aa1_5.add_straight_segment(length=109 + 190 - 2 ).add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    wg_aa1_5.add_straight_segment(length=20)

    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_aa1_1, spiral_aa1, wg_aa1_2, wg_aa1_3, wg_aa1_4,
                                       wg_aa1_5, spiral_a1_1, wg_aa1_7, wg_aa1_8, resonator_aa1)



    position = (4820, 0)
    left_grating_aaa1_1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_aaa1_1.cell)
    wg_aaa1_1 = Waveguide.make_at_port(port=left_grating_aaa1_1.port)
    wg_aaa1_1.add_straight_segment(length=20)
    wg_aaa1_1.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    spiral_aaa1 = Spiral.make_at_port(wg_aaa1_1.current_port, num=3, gap=5, inner_gap=20)
    wg_aaa1_2 = Waveguide.make_at_port(port=spiral_aaa1.out_port)
    wg_aaa1_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=100 - 34 +22)
    wg_aaa1_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=127+127+127)

    position = (4820+127, 0)
    left_grating_aaa2_1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_aaa2_1.cell)
    wg_aaa2_1 = Waveguide.make_at_port(port=left_grating_aaa2_1.port)
    wg_aaa2_1.add_straight_segment(length=20)
    wg_aaa2_1.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    spiral_aaa2 = Spiral.make_at_port(wg_aaa2_1.current_port, num=5, gap=5, inner_gap=20)
    wg_aaa2_2 = Waveguide.make_at_port(port=spiral_aaa2.out_port)
    wg_aaa2_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=100 - 34)
    wg_aaa2_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=127 + 127)

    position = (4820 + 127 + 127, 0)
    left_grating_aaa3_1 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)
    grating_loopback_cell.add_cell(left_grating_aaa3_1.cell)
    wg_aaa3_1 = Waveguide.make_at_port(port=left_grating_aaa3_1.port)
    wg_aaa3_1.add_straight_segment(length=20)
    wg_aaa3_1.add_bend(angle=pi / 2, radius=BEND_RADIUS)
    spiral_aaa3 = Spiral.make_at_port(wg_aaa3_1.current_port, num=7, gap=5, inner_gap=20)
    wg_aaa3_2 = Waveguide.make_at_port(port=spiral_aaa3.out_port)
    wg_aaa3_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=100 - 34 - 22)
    wg_aaa3_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=127)
    wg_aaa3_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=200)

    right_grating_aaa3_1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_aaa3_2.current_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating_aaa3_1.cell)

    wg_aaa4_1 = Waveguide.make_at_port(port=wg_aaa1_2.current_port)
    wg_aaa4_1.add_straight_segment(length=100-20)
    mzi_aaa1 = MachZehnderInterferometerMMI.make_at_port(port=wg_aaa4_1.current_port, splitter_length=33,
                                                        splitter_width=7,
                                                        bend_radius=30, upper_vertical_length=100,
                                                        lower_vertical_length=100,
                                                        horizontal_length=30)
    wg_aaa4_2 = Waveguide.make_at_port(port=mzi_aaa1.port)
    wg_aaa4_2.add_straight_segment(length=100+5-40)
    wg_aaa4_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=200)

    right_grating_aaa3_2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_aaa4_2.current_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating_aaa3_2.cell)

    wg_aaa4_3 = Waveguide.make_at_port(port=mzi_aaa1.port)
    wg_aaa4_3.add_straight_segment(length=200 - 31 + 20)
    resonator_aaa1 = RingResonator.make_at_port(wg_aaa4_3.current_port, gap=1, radius=80)
    wg_aaa4_3.add_straight_segment(length=200 - 50 - 20)
    wg_aaa4_3.add_bend(angle=- pi / 2, radius=BEND_RADIUS).add_straight_segment(length=200)
    right_grating_aaa3_3 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_aaa4_3.current_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating_aaa3_3.cell)




    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_aaa1_1, spiral_aaa1, wg_aaa1_2, spiral_aaa2, wg_aaa2_2
                                       , wg_aaa2_1, wg_aaa3_2, wg_aaa3_1, spiral_aaa3
                                       , wg_aaa4_1, mzi_aaa1, wg_aaa4_2, wg_aaa4_3, resonator_aaa1)


    # Grating checker
    # grating_checker([left_grating_d1, right_grating])

    return grating_loopback_cell
