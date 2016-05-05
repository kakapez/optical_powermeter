# -*- coding: utf-8 -*-
"""
Created on Wed Aug 27 11:13:37 2014

@author: nick
"""

from kivy.config import Config
Config.set('graphics', 'width', '1280')# set screen size to nexus 7 dimensions looks ok on PC
Config.set('graphics', 'height', '720')
Config.write()
from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.properties import NumericProperty, BooleanProperty, ObjectProperty, BoundedNumericProperty,ListProperty, StringProperty
from kivy.clock import Clock
from kivy.utils import platform
from kivy.garden.graph import Graph, MeshLinePlot
from kivy.uix.tabbedpanel import TabbedPanel
import re
import os
import glob
import json
import time
import powermeter as pm
import numpy as np


class FloatInput(TextInput): 

    pat = re.compile('[^0-9]')
    multiline = False
    halign = 'center'

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)

class PowerMeterControl(TabbedPanel):
    fpower = StringProperty('0.0')
    power = NumericProperty(0.0)
    max_power = NumericProperty(0.0)
    voltage = NumericProperty(0)
    tick_color = ListProperty([0,1,0,1])
    wavelength = BoundedNumericProperty(780.0,min=340.0,max=1180,errorhandler=lambda x: 1180 if x > 1180 else 340)
    connected = BooleanProperty(False)
    logo = 'CQTtools_inverted.png'
    graph = Graph()


    plot = ObjectProperty(None)

    powermeter = None
    
    pm_range = 4
    
    iteration = 0
    
    dt = 0.25
    

    def update(self, dt):
        v=[]
        average_v=0
        for i in range(0,50):
           v.append(float(self.powermeter.get_voltage()))
           average_v=np.mean(v)
        #self.voltage = float(self.powermeter.get_voltage())
        self.voltage=float(average_v)
        self.power = self.amp2power(self.voltage,self.wavelength,int(self.pm_range))
        self.fpower = self.formated_power() #
        #self.power_max()
        self.plot.points.append((self.iteration*dt,self.power*1000))
        #print self.plot.points
        self.iteration += 1*dt
        if self.iteration > 150:
            self.iteration = 0
            self.plot.points = []
            self.ids.graph1.remove_plot(self.plot)
  
       

    def update_range(self, value):
        self.pm_range = value
        if self.connected == True:
            self.pm_range = value
            self.powermeter.set_range(int(self.pm_range))
            print self.pm_range
            return self.pm_range
        

    def connect_to_powermeter(self, connection):
        if not self.connected:
            if platform == 'android': #to get access to serial port on android
                os.system("su -c chmod 777 " + connection)#has to run as child otherwise will not work with all su binarys
            self.data = self._read_cal_file()
            self.powermeter = pm.pmcommunication(connection)
            Clock.schedule_interval(self.update, self.dt)
            self.connected = True
            self.update_range(self.pm_range)
            plot = MeshLinePlot(color=[0, 1, 0, 1])
            self.ids.graph1.add_plot(plot)
            self.plot = plot
            return self.powermeter
 
    def serial_ports_android(self):
        #Lists serial ports
        ports = glob.glob('/dev/ttyACM*')
        return ports
    
    
        """this section of the code deals with converting between the voltage value and the
    optical power at the wavelength of interest"""
    
    resistors = [1e6,110e3,10e3,1e3,20]    #sense resistors adjust to what is on the board
    
    file_name = 's5106_interpolated.cal'    #detector calibration file
    

    
    def _read_cal_file(self): # read in calibration file for sensor
        f = open(self.file_name,'r')
        x = json.load(f)
        f.close()
        return x
        

    def volt2amp(self,voltage,range_number):
        self.amp = voltage/self.resistors[range_number]
        return self.amp
								
    
    def amp2power(self,voltage,wavelength,range_number):
        amp = self.volt2amp(voltage,range_number-1)
        xdata = self.data[0]
        ydata = self.data[1]
        i = xdata.index(int(wavelength))
        responsivity = ydata[i]
        power = amp/float(responsivity)
        return power
    
    def formated_power(self):
        power = self.amp2power(self.voltage,self.wavelength,int(self.pm_range))
        fpower = power*1000
        if 1 < fpower < 500:
            fpower = round(fpower,2)
            out = str(fpower) + 'mW'
        elif 0.001 < fpower < 1:
            fpower = round(fpower*1000,2)
            out =  str(fpower) + 'uW'
        elif 10e-6 < fpower < 0.001:
            fpower = round(fpower*1e6,2)
            out =  str(fpower) + 'nW'
        elif fpower < 10e-6:
            out = 'Low'
        else:
            out = 'High'
        return out
    
    def power_max(self):
        if self.max_power < self.power:
            self.max_power = self.power
        return self.max_power
      
class PowermeterApp(App):
    def build(self):
        self.control = PowerMeterControl()
        return self.control
    
    def on_pause(self):
        return True
        
    def on_resume(self):
        pass
    
    def on_stop(self):
        self.control.powermeter.reset()
        self.control.powermeter.close_port()
        #from jnius import autoclass
        #UsbDeviceConnection = autoclass('android.hardware.usb.UsbDeviceConnection')
        #usbotg = UsbDeviceConnection()
        #usbotg.close()
        print 'Port Closed'
        return 





if __name__ == '__main__':
    PowermeterApp().run()
