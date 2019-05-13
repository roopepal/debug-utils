#!/usr/bin/env python3
import re
import sdl2.ext
import shlex
import subprocess
import sys

if len(sys.argv) < 2:
    print("Usage:")
    print(__file__ + " device_serial [downscaling_factor]")
    sys.exit(1)
SERIAL = sys.argv[1]
print("Watching " + SERIAL)

DOWNSCALE = 4
if len(sys.argv) > 2:
    try:
        DOWNSCALE = int(sys.argv[2])
    except:
        print("'" + sys.argv[2] + "' is not a valid downscale argument. Must be an integer.")
        sys.exit(1)

BLACK = sdl2.ext.Color(0,0,0)
MAGENTA = sdl2.ext.Color(255,0,255)
CYAN = sdl2.ext.Color(0,255,255)
COLOR_CORNER = MAGENTA
COLOR_HINT = CYAN

NOTHING = 0
CORNERS = 1
HINTS = 2


class OutputHandler():
    def __init__(self, renderer):
        self.renderer = renderer
        self.points = [None,[],[]] # corners at 1, hints at 2
        self.previous = [None,[],[]]
        self.colors = [None, MAGENTA, CYAN]

    def handle_coordinate_lines(self, lines, typ):
        #print(lines, typ)
        self.points[typ] = []
        for l in lines:
            coords = self.parse_coordinates(l)
            if coords:
                for c in coords:
                    self.points[typ].append(c)
        self.draw()

    def parse_coordinates(self, s):
        coords = re.sub(r"\(|\)|\,", "", s).split()
        try:
            coords = [int(x)//DOWNSCALE for x in coords]
            return [[coords[0], coords[1]],
                    [coords[2], coords[3]]]    
        except:
            return False
    
    def draw_point(self, point, typ):
        size = 2
        pixels = []
        if typ == HINTS: # x shape
            pixels = [point,
                     [point[0]+size, point[1]+size],
                     [point[0]-size, point[1]+size],
                     [point[0]+size, point[1]-size],
                     [point[0]-size, point[1]-size]]
        else: # + shape
            pixels = [point,
                     [point[0]+size, point[1]     ],
                     [point[0]-size, point[1]     ],
                     [point[0],      point[1]+size],
                     [point[0],      point[1]-size]]
 
        for p in pixels:
            self.renderer.draw_point(p, self.colors[typ])
            self.previous[typ].append(p)

    def draw(self):
        self.renderer.clear(BLACK)
        for p in self.points[CORNERS]:
            self.draw_point(p, CORNERS)
        for p in self.points[HINTS]:
            self.draw_point(p, HINTS)
        self.renderer.present()


sdl2.ext.init()
W = 1080 // DOWNSCALE
H = 1920 // DOWNSCALE
window = sdl2.ext.Window("Corner debugger", size=(W, H))
window.show()
renderer = sdl2.ext.Renderer(window)
handler = OutputHandler(renderer)

adb_clear_command = "adb -s " + SERIAL + " logcat -c"
adb_clear = subprocess.Popen(shlex.split(adb_clear_command))
while adb_clear.poll() is None:
    pass

adb_command = "adb -s " + SERIAL + " logcat -v raw JNIpart:D '*:S'"
adb = subprocess.Popen(shlex.split(adb_command), stdin=subprocess.PIPE, stdout=subprocess.PIPE)

lines = []
grab = NOTHING

try:
    while True:
        for e in sdl2.ext.get_events():
            if e.type == sdl2.SDL_QUIT:
                break
        
        line = adb.stdout.readline().decode("utf-8", "replace").strip()
        
        if len(line) == 0:
            break

        if line.startswith("corners"):
            grab = CORNERS
            continue

        elif line.startswith("hints"):
            grab = HINTS
            continue

        if grab == CORNERS or grab == HINTS:
            lines.append(line)
            if len(lines) == 3:
                handler.handle_coordinate_lines(lines, grab)
                lines = []
                grab = NOTHING

except KeyboardInterrupt:
    pass

sdl2.ext.quit()
adb.kill()