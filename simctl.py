#!/usr/bin/env python3
import sys, socket, json, time

USAGE = """
Usage:
  python simctl.py <port> set_bg r g b
  python simctl.py <port> set_bg565 <hex_or_int>
  python simctl.py <port> btn <A|B|C> <press|release>
  python simctl.py <port> scene <0|1|2>
Examples:
  python simctl.py 8765 set_bg 255 0 0
  python simctl.py 8765 btn A press
  python simctl.py 8765 scene 2
"""

def send(port:int, obj:dict):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', port))
    line = json.dumps(obj) + "\n"
    s.sendall(line.encode('utf-8'))
    s.close()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(USAGE)
        sys.exit(1)
    port = int(sys.argv[1])
    cmd = sys.argv[2].lower()

    if cmd == 'set_bg' and len(sys.argv) >= 6:
        r, g, b = map(int, sys.argv[3:6])
        send(port, {"method":"set_bg", "rgb":[r,g,b]})
    elif cmd == 'set_bg565' and len(sys.argv) >= 4:
        v = int(sys.argv[3], 0)
        send(port, {"method":"set_bg", "rgb565": v})
    elif cmd == 'btn' and len(sys.argv) >= 5:
        btn = sys.argv[3].upper()
        action = sys.argv[4].lower()
        pressed = action in ('press','pressed','down','1','true','on')
        send(port, {"method":"btn", "id": btn, "pressed": pressed})
    elif cmd == 'scene' and len(sys.argv) >= 4:
        v = int(sys.argv[3])
        send(port, {"method":"scene", "value": v})
    else:
        print(USAGE)
        sys.exit(1)
