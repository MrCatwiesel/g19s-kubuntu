# Attrappe von python-evdev: echte Tastencodes aus der Kernel-Header-Liste (Auszug)
import re
_codes = {"KEY_ESC":1,"KEY_1":2,"KEY_2":3,"KEY_3":4,"KEY_4":5,"KEY_5":6,"KEY_6":7,"KEY_7":8,"KEY_8":9,"KEY_9":10,"KEY_0":11,
 "KEY_MINUS":12,"KEY_EQUAL":13,"KEY_BACKSPACE":14,"KEY_TAB":15,"KEY_Q":16,"KEY_W":17,"KEY_E":18,"KEY_R":19,"KEY_T":20,"KEY_Y":21,
 "KEY_U":22,"KEY_I":23,"KEY_O":24,"KEY_P":25,"KEY_LEFTBRACE":26,"KEY_RIGHTBRACE":27,"KEY_ENTER":28,"KEY_LEFTCTRL":29,"KEY_A":30,
 "KEY_S":31,"KEY_D":32,"KEY_F":33,"KEY_G":34,"KEY_H":35,"KEY_J":36,"KEY_K":37,"KEY_L":38,"KEY_SEMICOLON":39,"KEY_APOSTROPHE":40,
 "KEY_GRAVE":41,"KEY_LEFTSHIFT":42,"KEY_BACKSLASH":43,"KEY_Z":44,"KEY_X":45,"KEY_C":46,"KEY_V":47,"KEY_B":48,"KEY_N":49,"KEY_M":50,
 "KEY_COMMA":51,"KEY_DOT":52,"KEY_SLASH":53,"KEY_RIGHTSHIFT":54,"KEY_LEFTALT":56,"KEY_SPACE":57,"KEY_102ND":86,"KEY_RIGHTALT":100,
 "KEY_F5":63,"KEY_F13":183,"KEY_F14":184,"KEY_F15":185,"KEY_F16":186,"KEY_F17":187,"KEY_F18":188,"KEY_F19":189,"KEY_F20":190,
 "KEY_F21":191,"KEY_F22":192,"KEY_F23":193,"KEY_F24":194,"EV_KEY":1,
 "KEY_MUTE":113,"KEY_VOLUMEDOWN":114,"KEY_VOLUMEUP":115,"KEY_CALC":140,"KEY_NEXTSONG":163,"KEY_PLAYPAUSE":164,
 "KEY_PREVIOUSSONG":165,"KEY_STOPCD":166}
class _E: pass
ecodes = _E()
for k, v in _codes.items(): setattr(ecodes, k, v)
ecodes.ecodes = dict(_codes); ecodes.KEY = {v: k for k, v in _codes.items() if k.startswith("KEY_")}; ecodes.BTN = {}
SENT = []
class UInput:
    def __init__(self, *a, **k): pass
    def write(self, t, code, val): SENT.append((ecodes.KEY.get(code, code), val))
    def syn(self): pass
    def close(self): pass
def list_devices(): return []
class InputDevice: pass
