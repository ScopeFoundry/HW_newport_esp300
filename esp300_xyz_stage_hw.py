from ScopeFoundry.hardware import HardwareComponent
from ScopeFoundryHW.newport_esp300.esp300_dev import ESP300
import time

class ESP300XYZStageHW(HardwareComponent):
    
    name = 'esp300_xyz_stage'
    
    
    def __init__(self, app, debug=False, name=None, ax_names='xyz'):
        """
        ax_names defines the names of the three axes connected to the stage.
        if an "_" underscore is found, that axis will be skipped.
        May be any iterable. examples include 'xyz' or ['r', 'theta', 'phi']
        
        """
        
        self.ax_names = ax_names
        HardwareComponent.__init__(self, app, debug=debug, name=name)
    
    
    def setup(self):
        
        self.settings.New('port', str, initial='COM1')
        
        for axis in self.ax_names:
            if axis == '_' or axis == None:
                continue
            self.settings.New(axis + "_position", 
                               dtype=float,
                               ro=True,
                               unit='mm',
                               spinbox_decimals=6,
                               si=False
                               )
            
            #self.settings.New(axis + "_ref_position", dtype=float, ro=True, unit='nm')
            
            self.settings.New(axis + "_target_position",
                                dtype=float,
                                ro=False,
                                vmin=-300,
                                vmax=300,
                                unit='mm',
                                spinbox_decimals=6,
                                spinbox_step=0.01,
                                si=False)
            
            
            self.settings.New(axis + '_enabled', bool, initial=True)
            self.settings.New(axis + '_is_moving', bool, ro=True)
            
            self.settings.New(axis + "_step_delta", dtype=float, unit='m', si=True, initial=100e-6, vmin=0 )
            
            self.add_operation(axis + "_home_neg", lambda ax=axis: self.home_axis_neg(ax))
        
    def connect(self):
        S = self.settings
        

        E = self.esp300 = ESP300(port=S['port'], debug=S['debug_mode'])
        
        for axis_index, axis_name in enumerate(self.ax_names):
            axis_num = axis_index + 1
            # skip axes that are excluded from ax_names
            if axis_name == '_' or axis_name == None:
                continue
            
            unit = E.read_unit(axis_num)
            self.settings.get_lq(axis_name + "_position").change_unit(unit)
            self.settings.get_lq(axis_name + "_target_position").change_unit(unit)
            
            pos = self.settings.get_lq(axis_name + "_position")
            def read_pos(a=axis_num, E=self.esp300):
                return E.read_pos(a)
            pos.connect_to_hardware(read_func=read_pos)
            pos.read_from_hardware()
    
            target = self.settings.get_lq(axis_name + "_target_position")
            target.update_value(pos.value)

            target.connect_to_hardware(
                write_func = lambda new_pos, a=axis_num: E.write_target_pos_abs(a, new_pos))

            enabled = self.settings.get_lq(axis_name + "_enabled")
            enabled.connect_to_hardware(
                read_func = lambda a=axis_num: E.read_enabled(a),
                write_func = lambda enabled, a=axis_num: E.write_enabled(a, enabled))
            enabled.read_from_hardware()

            is_moving = self.settings.get_lq(axis_name + "_is_moving")
            is_moving.connect_to_hardware(
                read_func = lambda a=axis_num: E.read_is_moving(a))
            is_moving.read_from_hardware()
            

    def disconnect(self):
        self.settings.disconnect_all_from_hardware()
        
        if hasattr(self, 'esp300'):
            self.esp300.close()
            del self.esp300
    
    def move_step_delta(self, axname, dir=+1):
        "dir should be +/- 1"
        dir = dir * 1.0/ abs(dir)
        # note meter to mm conversion
        self.settings[axname + "_target_position"] += dir * self.settings[axname + '_step_delta'] * 1e3 
        
    def home_axis_neg(self, axname):
        
        for axis_index, axis_name in enumerate(self.ax_names):
            axis_num = axis_index + 1

            if axname == axis_name:
                self.esp300.search_for_home(axis_num, method='neg_limit_signal')

    def threaded_update(self):
#         import time
        #print("asdf")
        for axis_index, axis_name in enumerate(self.ax_names):
            # skip axes that are excluded from ax_names
            if axis_name == '_' or axis_name == None:
                continue

            pos = self.settings.get_lq(axis_name + "_position")
            pos.read_from_hardware()
            
            enabled = self.settings.get_lq(axis_name + "_enabled")
            enabled.read_from_hardware()

            is_moving = self.settings.get_lq(axis_name + "_is_moving")
            is_moving.read_from_hardware()

                    
        time.sleep(0.500)

