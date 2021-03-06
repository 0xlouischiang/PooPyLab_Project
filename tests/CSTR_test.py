#   This file is part of PooPyLab.
#
#    PooPyLab is a simulation software for biological wastewater treatment
#    processes using the International Water Association Activated Sludge
#    Models.
#   
#    Copyright (C) Kai Zhang
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# --------------------------------------------------------------------
#    Testing the influent/effluent/pipe/reactor classes.
#
#
# Change Log:
# 2020-07-11 KZ: added handling of CSTR w/o RAS/WAS
# 2020-07-08 KZ: init
#

from unit_procs.streams import pipe, influent, effluent
from unit_procs.bio import asm_reactor
import utils.pfd
import utils.run
import pdb
import timeit, cProfile

if __name__ == '__main__':

    import CSTR

    wwtp = CSTR.construct()

    utils.pfd.check(wwtp)

    utils.pfd.show(wwtp)

    # identify units of different types
    _inf = utils.pfd.get_all_units(wwtp, 'Influent')

    _reactors = utils.pfd.get_all_units(wwtp, 'ASMReactor')

    _WAS = utils.pfd.get_all_units(wwtp, 'WAS')

    _splitters = utils.pfd.get_all_units(wwtp, 'Splitter')

    _srt_ctrl = [_u for _u in _splitters if _u.is_SRT_controller()]

    _final_clar = utils.pfd.get_all_units(wwtp, 'Final_Clarifier')

    _eff = utils.pfd.get_all_units(wwtp, 'Effluent')

    print('Influent in the PFD: {}'.format([_u.__name__ for _u in _inf]))
    _inf[0].blend_inlet_comps()
    print("Influent Conc:", _inf[0]._in_comps)

    _plant_inf_flow = sum([_u.get_main_outflow() for _u in _inf])
    print(' Total influent flow into plant:', _plant_inf_flow)

    print('Reactors in the PFD: {}'.format([_u.__name__ for _u in _reactors]))

    print('WAS units in the PFD: {}'.format([_u.__name__ for _u in _WAS]))

    print('Splitters in the PFD: {}'.format(
        [_u.__name__ for _u in _splitters]))

    print('SRT Controlling Splitter in the PFD: {}'.format(
        [_u.__name__ for _u in _srt_ctrl]))

    print('Final Clarifier in the PFD: {}'.format(
        [_u.__name__ for _u in _final_clar]))

    print('Effluent in the PFD: {}'.format([_u.__name__ for _u in _eff]))

    # start the main loop
    _WAS_flow = 0.0  # M3/d
    _SRT = CSTR.SRT

    # get the influent ready
    for _u in _inf:
        _u.update_combined_input()
        _u.discharge()

    # TODO: what if there are multiple influent units?
    _params = _reactors[0].get_model_params()
    _seed = utils.run.initial_guess(_params, 
                                    _reactors,
                                    _inf[0].get_main_outflow(), 
                                    _inf[0].get_main_outlet_concs())
    
    print('Initial guess = {}'.format(_seed))

    for _r in wwtp:
        _r.assign_initial_guess(_seed)

    for fc in _final_clar:
        fc.set_capture_rate(0.992)

    
    utils.run.forward_set_flow(wwtp)
    
    # collect all the possible starting points for backward flow setting
    _backward_start_points = [_w for _w in _WAS] + [_e for _e in _eff]
    
    profile = cProfile.Profile()
    profile.enable()

    #start_t = timeit.default_timer()


    #pdb.set_trace()
    if len(_WAS) == 0:
        _WAS_flow = 0
    else:
        _WAS_flow = _WAS[0].set_WAS_flow(_SRT, _reactors, _eff)
        _WAS[0].set_mainstream_flow(_WAS_flow)
    _eff[0].set_mainstream_flow(_plant_inf_flow - _WAS_flow)
    utils.run.backward_set_flow(_backward_start_points)
    utils.run.traverse_plant(wwtp, _inf[0])
    
    r = 1
    while True:
        if len(_WAS) == 0:
            _WAS_flow = 0
        else:
            _WAS_flow = _WAS[0].set_WAS_flow(_SRT, _reactors, _eff)
            _WAS[0].set_mainstream_flow(_WAS_flow)
        _eff[0].set_mainstream_flow(_plant_inf_flow - _WAS_flow)
        utils.run.backward_set_flow(_backward_start_points)
        utils.run.traverse_plant(wwtp, _inf[0])

        if utils.run.check_global_cnvg(wwtp):
            break
        r += 1

    #core_run_time = timeit.default_timer() - start_t
    profile.disable()

    utils.run.show_concs(wwtp)

    profile.print_stats()

    #print("TOTAL ITERATION = ", r, " RUN TIME = ", core_run_time)

    print(_reactors[0].get_active_vol())
    print(_reactors[0].get_model_params())
    print(_reactors[0].get_model_stoichs())
