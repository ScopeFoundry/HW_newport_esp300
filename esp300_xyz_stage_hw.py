from ScopeFoundry.hardware import HardwareComponent
import threading
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
        
        self.settings.New('port', str, initial='COM5')
        
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
                                vmin=-20,
                                vmax=20,
                                unit='mm',
                                spinbox_decimals=6,
                                spinbox_step=0.01,
                                si=False)
            
            
            self.settings.New(axis + '_enabled', bool, initial=True)
            self.settings.New(axis + '_is_moving', bool, ro=True)
            
            self.settings.New(axis + "_step_delta", dtype=float, unit='m', si=True, initial=100e-6, vmin=0 )
            
        
    def connect(self):
        S = self.settings
        
        from .esp300_dev import ESP300
        E = self.esp300 = ESP300(port=S['port'], debug=S['debug_mode'])
        
        for axis_index, axis_name in enumerate(self.ax_names):
            axis_num = axis_index + 1
            # skip axes that are excluded from ax_names
            if axis_name == '_' or axis_name == None:
                continue
            
            unit = E.read_unit(axis_num)
            self.settings.get_lq(axis_name + "_position").change_unit(unit)
            self.settings.get_lq(axis_name + "_target_position").change_unit(unit)
            
            self.settings.get_lq(axis_name + "_position").connect_to_hardware(
                lambda a=axis_num: E.read_pos(a))
    
            self.settings.get_lq(axis_name + "_target_position").connect_to_hardware(
                write_func = lambda new_pos, a=axis_num: E.write_target_pos_abs(a, new_pos))

            self.settings.get_lq(axis_name + "_enabled").connect_to_hardware(
                read_func = lambda a=axis_num: E.read_enabled(a),
                write_func = lambda enabled, a=axis_num: E.write_enabled(a, enabled))

            self.settings.get_lq(axis_name + "_is_moving").connect_to_hardware(
                read_func = lambda a=axis_num: E.read_is_moving(a))


        self.update_thread_interrupted = False
        self.update_thread = threading.Thread(target=self.update_thread_run)
        self.update_thread.start()

    def disconnect(self):
        self.settings.disconnect_all_from_hardware()
        
        if hasattr(self, 'esp300'):
            self.esp300.close()
            del self.esp300

        if hasattr(self, 'update_thread'):
            self.update_thread_interrupted = True
            self.update_thread.join(timeout=1.0)
            del self.update_thread
    
    def move_step_delta(self, axname, dir=+1):
        "dir should be +/- 1"
        dir = dir * 1.0/ abs(dir)
        self.settings[axname + "_target_position"] += dir * self.settings[axname + '_step_delta']


    def update_thread_run(self):
        while not self.update_thread_interrupted:            
            for axis_index, axis_name in enumerate(self.ax_names):
                if axis_name != '_':
                    self.settings.get_lq(axis_name + "_position").read_from_hardware()
            time.sleep(0.1)
        
