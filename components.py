import numpy as np
from math import pi
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.coupler import GratingCoupler
from gdshelpers.parts.splitter import MMI
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.port import Port
from gdshelpers.parts.spiral import Spiral
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.port import Port
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.interferometer import MachZehnderInterferometerMMI
from gdshelpers.parts.resonator import RingResonator
from gdshelpers.geometry.chip import Cell
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

    # Create the cell that we are going to add to
    grating_loopback_cell = Cell(name)

    # Create the left hand side grating
    left_grating = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params)

    # Add the left grating coupler cell to our loopback cell
    # grating_loopback_cell.add_cell(left_grating.cell)
    # Join our grating couplers together
    spiral_1 = Spiral.make_at_port(Port(origin=(0, -1000), angle=0, width=0.5), num=5, gap=10, inner_gap=50)
    wg = Waveguide.make_at_port(port=spiral_1.out_port)  # Create waveguide at the left grating port location
    wg1 = Waveguide.make_at_port(port=spiral_1.in_port)  # Create waveguide at the left grating port location
    wg1.add_straight_segment(length=147).add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg.add_straight_segment(length=100).add_bend(angle=pi / 2, radius=BEND_RADIUS)  # Do some routing
    wg.add_straight_segment(length=205)
    # wg.add_straight_segment(length=10)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg, spiral_1, wg1)  # Add the waveguide to the loopback cell

    # Create the right grating coupler at the waveguide port location
    right_grating = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg.current_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating.cell)


    left_grating = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg1.current_port,
        **coupler_params)
    # Add the right grating to the loopback cell
    grating_loopback_cell.add_cell(left_grating.cell)



    spiral_2 = Spiral.make_at_port(Port(origin=(500, -1000), angle=0, width=0.5), num=10, gap=10, inner_gap=50)
    wg2 = Waveguide.make_at_port(port=spiral_2.out_port)  # Create waveguide at the left grating port location
    wg3 = Waveguide.make_at_port(port=spiral_2.in_port)  # Create waveguide at the left grating port location
    wg3.add_straight_segment(length=174).add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg2.add_straight_segment(length=200).add_bend(angle=pi / 2, radius=BEND_RADIUS)  # Do some routing
    wg2.add_straight_segment(length=305)
    # wg.add_straight_segment(length=10)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg2, spiral_2, wg3)  # Add the waveguide to the loopback cell

    right_grating1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg2.current_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating1.cell)

    left_grating1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg3.current_port,
        **coupler_params)
    # Add the right grating to the loopback cell
    grating_loopback_cell.add_cell(left_grating1.cell)

    # spiral_3 = Spiral.make_at_port(Port(origin=(1000, 0), angle=0, width=0.5), num=15, gap=10, inner_gap=50)
    # wg4 = Waveguide.make_at_port(port=spiral_3.out_port)  # Create waveguide at the left grating port location
    # wg5 = Waveguide.make_at_port(port=spiral_3.in_port)  # Create waveguide at the left grating port location
    # wg5.add_straight_segment(length=100).add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    # wg4.add_straight_segment(length=300).add_bend(angle=pi / 2, radius=BEND_RADIUS)  # Do some routing
    # wg4.add_straight_segment(length=405)
    # # wg.add_straight_segment(length=10)
    # grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg4, spiral_3, wg5)  # Add the waveguide to the loopback cell
    #
    # right_grating2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
    #     port=wg4.current_port,
    #     **coupler_params)
    # grating_loopback_cell.add_cell(right_grating2.cell)
    #
    # left_grating2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
    #     port=wg5.current_port,
    #     **coupler_params)
    # # Add the right grating to the loopback cell
    # grating_loopback_cell.add_cell(left_grating2.cell)

    waveguide_1 = Waveguide.make_at_port(Port([1300, -1000], -pi / 2, 0.5))
    waveguide_1.add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    waveguide_1.add_straight_segment(100+47.6/2)
    resonator_1 = RingResonator.make_at_port(waveguide_1.current_port, gap=1, radius=50)
    waveguide_1.add_straight_segment(100+47.6/2)
    waveguide_1.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    left_grating_1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=waveguide_1.current_port,
        **coupler_params)
    # Add the right grating to the loopback cell
    grating_loopback_cell.add_cell(left_grating_1.cell)
    right_grating_1 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=waveguide_1.in_port,
        **coupler_params)
    # Add the right grating to the loopback cell
    grating_loopback_cell.add_cell(right_grating_1.cell)

    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, waveguide_1, resonator_1)

    waveguide_2 = Waveguide.make_at_port(Port([1800, -1000], -pi / 2, 0.5))
    waveguide_2.add_bend(angle=- pi / 2, radius=BEND_RADIUS)
    waveguide_2.add_straight_segment(100+47.6/2)
    resonator_2 = RingResonator.make_at_port(waveguide_2.current_port, gap=1, radius=100)
    waveguide_2.add_straight_segment(100+47.6/2)
    waveguide_2.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    left_grating_2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=waveguide_2.current_port,
        **coupler_params)
    # Add the right grating to the loopback cell
    grating_loopback_cell.add_cell(left_grating_2.cell)
    right_grating_2 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=waveguide_2.in_port,
        **coupler_params)
    # Add the right grating to the loopback cell
    grating_loopback_cell.add_cell(right_grating_2.cell)

    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, waveguide_2, resonator_2)




    coupler_params1 = {
        'width': GRATING_COUPLER_WIDTH,
        'full_opening_angle': np.deg2rad(GRATING_FAN_ANGLE),
        'grating_period': GRATING_PERIOD,
        'grating_ff': GRATING_FILL_FACTOR,
        'n_gratings': GRATING_NO_PERIODS,
        'taper_length': GRATING_TAPER_LENGTH
    }

    position = (2100, -500)
    coupler_params = coupler_params1
    left_grating10 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params1)
    wg10 = Waveguide.make_at_port(port=left_grating10.port)
    wg10.add_straight_segment(length=100).add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg10.add_straight_segment(length=120).add_bend(angle=-pi / 2, radius=BEND_RADIUS).add_straight_segment(length=100)
    # left_grating10 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
    #     port=Port(origin=(1500, 0), angle=0, width=0.5)
    #     **coupler_params)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg10)
    grating_loopback_cell.add_cell(left_grating10.cell)
    right_grating10 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg10.current_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating10.cell)

    coupler_params2 = {
        'width': GRATING_COUPLER_WIDTH,
        'full_opening_angle': np.deg2rad(GRATING_FAN_ANGLE),
        'grating_period': GRATING_PERIOD,
        'grating_ff': GRATING_FILL_FACTOR,
        'n_gratings': GRATING_NO_PERIODS,
        'taper_length': GRATING_TAPER_LENGTH
    }

    position = (2400, -500)
    coupler_params = coupler_params2
    left_grating20 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params2)
    wg20 = Waveguide.make_at_port(port=left_grating20.port)
    wg20.add_straight_segment(length=100).add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg20.add_straight_segment(length=117.3+127+2.6).add_bend(angle=-pi / 2, radius=BEND_RADIUS).add_straight_segment(length=100)
    # left_grating10 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
    #     port=Port(origin=(1500, 0), angle=0, width=0.5)
    #     **coupler_params)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg20)
    grating_loopback_cell.add_cell(left_grating20.cell)
    right_grating20 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg20.current_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating20.cell)

    coupler_params3 = {
        'width': GRATING_COUPLER_WIDTH,
        'full_opening_angle': np.deg2rad(GRATING_FAN_ANGLE),
        'grating_period': GRATING_PERIOD,
        'grating_ff': GRATING_FILL_FACTOR,
        'n_gratings': GRATING_NO_PERIODS,
        'taper_length': GRATING_TAPER_LENGTH
    }

    position = (2800, -500)
    coupler_params = coupler_params3
    left_grating30 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params3)
    wg30 = Waveguide.make_at_port(port=left_grating30.port)
    wg30.add_straight_segment(length=100).add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg30.add_straight_segment(length=117.3 + 127 + 127 + 3).add_bend(angle=-pi / 2, radius=BEND_RADIUS).add_straight_segment(length=100)
    # left_grating10 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
    #     port=Port(origin=(1500, 0), angle=0, width=0.5)
    #     **coupler_params)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg30)
    grating_loopback_cell.add_cell(left_grating30.cell)
    right_grating30 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg30.current_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating30.cell)




    wg_111 = Waveguide.make_at_port(Port(origin=(3500, -500), angle=pi/2, width=0.5))
    wg_111.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg_111.add_straight_segment(length=20+51.5)
    mzi_111 = MachZehnderInterferometerMMI.make_at_port(port=wg_111.current_port, splitter_length=33, splitter_width=7,
                                                      bend_radius=30, upper_vertical_length=10,
                                                      lower_vertical_length=10,
                                                      horizontal_length=25)

    wg_222 = Waveguide.make_at_port(port=mzi_111.port)
    wg_222.add_straight_segment(length=20+51.5).add_bend(angle=-pi / 2, radius=BEND_RADIUS)

    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_222, wg_111, mzi_111)

    right_grating11 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_111.in_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating11.cell)

    left_grating11 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_222.current_port,
        **coupler_params)
    # Add the right grating to the loopback cell
    grating_loopback_cell.add_cell(left_grating11.cell)


    wg_01 = Waveguide.make_at_port(Port(origin=(4000, -500), angle=pi/2, width=0.5))
    wg_01.add_bend(angle=-pi / 2, radius=BEND_RADIUS)
    wg_01.add_straight_segment(length=20+39)
    mzi_01 = MachZehnderInterferometerMMI.make_at_port(port=wg_01.current_port, splitter_length=33, splitter_width=7,
                                                      bend_radius=30, upper_vertical_length=10,
                                                      lower_vertical_length=10,
                                                      horizontal_length=50)

    wg_02 = Waveguide.make_at_port(port=mzi_01.port)
    wg_02.add_straight_segment(length=20+39).add_bend(angle=-pi / 2, radius=BEND_RADIUS)

    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_02, wg_01, mzi_01)

    right_grating111 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_01.in_port,
        **coupler_params)
    grating_loopback_cell.add_cell(right_grating111.cell)

    left_grating111 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_02.current_port,
        **coupler_params)
    # Add the right grating to the loopback cell
    grating_loopback_cell.add_cell(left_grating111.cell)

    position = (5000, -500)
    coupler_params = coupler_params3
    left_grating_30 = CornerstoneGratingCoupler().create_coupler(
        origin=(position[0], position[1]),
        coupler_params=coupler_params3)
    wg_03 = Waveguide.make_at_port(port=left_grating_30.port)
    wg_03.add_bend(angle=-pi / 2, radius=BEND_RADIUS).add_straight_segment(length=20)
    wg_03.add_straight_segment(length=80)
    resonator_3 = RingResonator.make_at_port(wg_03.current_port, gap=1, radius=50)
    wg_03.add_straight_segment(length=91)
    mzi_03 = MachZehnderInterferometerMMI.make_at_port(port=wg_03.current_port, splitter_length=33, splitter_width=7,
                                                       bend_radius=30, upper_vertical_length=10,
                                                       lower_vertical_length=10,
                                                       horizontal_length=50)
    wg_04 = Waveguide.make_at_port(port=mzi_03.port)
    wg_04.add_straight_segment(length=20)
    wg_04.add_straight_segment(length=71)
    wg_04.add_bend(angle=pi, radius=BEND_RADIUS).add_straight_segment(length=20)

    spiral_4 = Spiral.make_at_port(wg_04.current_port, num=5, gap=10, inner_gap=50)
    wg_05 = Waveguide.make_at_port(port=spiral_4.out_port)
    wg_05.add_bend(angle=-pi, radius=BEND_RADIUS).add_straight_segment(length=20)
    wg_05.add_straight_segment(length=90).add_bend(angle=-pi/2, radius=BEND_RADIUS).add_straight_segment(length=244)
    left_grating_05 = CornerstoneGratingCoupler().create_cornerstone_coupler_at_port(
        port=wg_05.current_port,
        **coupler_params)
    # Add the right grating to the loopback cell
    grating_loopback_cell.add_cell(left_grating_05.cell)

    grating_loopback_cell.add_cell(left_grating_30.cell)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, wg_03, resonator_3, mzi_03, wg_04, spiral_4, wg_05)

    qr_code_1 = QRCode(origin=[4625, -700], data='Yu-Kun FENG (2120013) Mask for Nanofabrication 13.03.2022', box_size=5.0, version=1, error_correction=QRCode.ERROR_CORRECT_M)
    grating_loopback_cell.add_to_layer(WAVEGUIDE_LAYER, qr_code_1)


    # Grating checker
    # grating_checker([left_grating, right_grating])

    return grating_loopback_cell
