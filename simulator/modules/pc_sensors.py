import threading
import time
import math
import sys

_has_opencv = False
_has_pyaudio = False
_has_psutil = False
_has_wmi = False

try:
    import cv2
    _has_opencv = True
except ImportError:
    pass

try:
    import pyaudio
    _has_pyaudio = True
except ImportError:
    pass

try:
    import psutil
    _has_psutil = True
except ImportError:
    pass

try:
    import wmi
    _has_wmi = True
except ImportError:
    pass


class PCSensors:
    def __init__(self):
        self._running = False
        self._thread = None
        
        self._camera_frame = None
        self._camera_available = False
        self._camera = None
        
        self._audio_level = 0
        self._audio_available = False
        self._audio_stream = None
        self._audio_p = None
        
        self._light_level = 0
        self._light_available = False
        
        self._cpu_temperature = 0
        self._battery_level = 100
        self._battery_charging = False
        
        self._sensor_data = {
            'light': 0,
            'sound': 0,
            'cpu_temp': 0,
            'battery': 100,
            'charging': False,
            'camera_active': False
        }
        
        self._lock = threading.Lock()
        self._callback = None
    
    def set_callback(self, callback):
        self._callback = callback
    
    def _init_camera(self):
        if not _has_opencv:
            return
        try:
            self._camera = cv2.VideoCapture(0)
            if self._camera.isOpened():
                self._camera_available = True
        except Exception:
            pass
    
    def _init_audio(self):
        if not _has_pyaudio:
            return
        try:
            self._audio_p = pyaudio.PyAudio()
            stream = self._audio_p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024,
                stream_callback=self._audio_callback
            )
            self._audio_stream = stream
            self._audio_stream.start_stream()
            self._audio_available = True
        except Exception:
            pass
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        import numpy as np
        try:
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            rms = np.sqrt(np.mean(np.square(audio_data)))
            with self._lock:
                self._audio_level = int(min(rms * 10, 3000))
        except:
            pass
        return (in_data, pyaudio.paContinue)
    
    def _read_light(self):
        if not _has_wmi:
            return
        try:
            c = wmi.WMI(namespace='root\\wmi')
            sensors = c.WmiMonitorBrightness()
            if sensors:
                self._light_level = sensors[0].CurrentBrightness * 100
                self._light_available = True
        except Exception:
            pass
    
    def _read_system_info(self):
        if not _has_psutil:
            return
        try:
            battery = psutil.sensors_battery()
            if battery:
                self._battery_level = battery.percent
                self._battery_charging = battery.power_plugged
            
            if sys.platform == 'linux':
                try:
                    temps = psutil.sensors_temperatures()
                    if 'cpu-thermal' in temps:
                        self._cpu_temperature = temps['cpu-thermal'][0].current
                    elif 'coretemp' in temps:
                        self._cpu_temperature = temps['coretemp'][0].current
                except:
                    pass
        except Exception:
            pass
    
    def _update_loop(self):
        while self._running:
            self._read_light()
            self._read_system_info()
            
            if self._camera_available and self._camera:
                try:
                    ret, frame = self._camera.read()
                    if ret:
                        self._camera_frame = frame
                except:
                    pass
            
            with self._lock:
                self._sensor_data = {
                    'light': self._light_level if self._light_available else 0,
                    'sound': self._audio_level,
                    'cpu_temp': self._cpu_temperature,
                    'battery': self._battery_level,
                    'charging': self._battery_charging,
                    'camera_active': self._camera_available
                }
            
            if self._callback:
                try:
                    self._callback(self._sensor_data.copy())
                except:
                    pass
            
            time.sleep(0.1)
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        self._init_camera()
        self._init_audio()
        
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        
        if self._audio_stream:
            try:
                self._audio_stream.stop_stream()
                self._audio_stream.close()
            except:
                pass
        
        if self._audio_p:
            try:
                self._audio_p.terminate()
            except:
                pass
        
        if self._camera:
            try:
                self._camera.release()
            except:
                pass
    
    def get_sensor_data(self):
        with self._lock:
            return self._sensor_data.copy()
    
    def get_camera_frame(self):
        with self._lock:
            return self._camera_frame
    
    def is_camera_available(self):
        return self._camera_available
    
    def is_audio_available(self):
        return self._audio_available
    
    def is_light_available(self):
        return self._light_available


pc_sensors = PCSensors()
