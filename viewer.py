from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, Signal
from OpenGL.GL import *
from OpenGL.GLU import *
import math

class NCPreviewWidget(QOpenGLWidget):
    toolMoved = Signal(float, float, float, int) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_limits = True
        self.machine_size = [300, 200, 100]
        self.path_data = [] 
        self.lastPos = None
        self.is_dark = True
        self.highlight_line = -1 
        
        self.tool_pos = None 
        self.tool_diameter = 10.0
        self.tool_library = {1: 10.0} 
        self.current_tool_id = 1
        
        self.reset_view()

    def set_tool_library(self, lib):
        self.tool_library = {int(k): float(v) for k, v in lib.items()}
        self.update()

    def update_path(self, new_data):
        self.path_data = new_data
        self.tool_pos = None 
        self.update()

    def set_highlight(self, line_idx):
        if self.highlight_line != line_idx:
            self.highlight_line = line_idx
            self.update()

    def set_tool_state(self, pos, tool_id):
        self.tool_pos = pos
        self.current_tool_id = tool_id
        self.toolMoved.emit(pos[0], pos[1], pos[2], tool_id)
        self.update()
        
    def set_tool_diameter(self, dia):
        self.tool_diameter = dia
        self.update()

    def set_theme(self, is_dark):
        self.is_dark = is_dark
        if self.isValid():
            self.makeCurrent()
            if self.is_dark: glClearColor(0.12, 0.12, 0.12, 1.0)
            else: glClearColor(0.9, 0.9, 0.9, 1.0)
            self.doneCurrent()
            self.update()

    def reset_view(self):
        self.camera_distance = max(self.machine_size) * 1.2 # Auto zoom fit
        self.rotation_x = -60
        self.rotation_z = -45
        # Centriramo kameru na sredinu masine
        self.pan_x = -self.machine_size[0] / 2
        self.pan_y = self.machine_size[1] / 2
        self.update()

    def initializeGL(self):
        if self.is_dark: glClearColor(0.12, 0.12, 0.12, 1.0)
        else: glClearColor(0.9, 0.9, 0.9, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glLightfv(GL_LIGHT0, GL_POSITION, [100.0, 100.0, 200.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(45, w / h, 0.1, 5000.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        glTranslatef(0.0, 0.0, -self.camera_distance)
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_z, 0, 0, 1)
        glTranslatef(self.pan_x, self.pan_y, 0.0)

        glDisable(GL_LIGHTING)
        self.draw_grid()
        if self.show_limits: self.draw_machine_box()
        self.draw_axes()
        
        if self.path_data:
            glLineWidth(2.0)
            glBegin(GL_LINES)
            for segment in self.path_data:
                is_dimmed = (self.highlight_line != -1 and segment.get('source_line') != self.highlight_line)
                alpha = 0.2 if is_dimmed else 1.0
                typ = segment['type']
                if typ == 'G0': glColor4f(1.0, 0.3, 0.3, alpha)
                elif typ == 'G1': glColor4f(0.0, 0.6, 1.0, alpha)
                elif typ == 'DRILL': glColor4f(1.0, 1.0, 0.0, alpha)
                else: glColor4f(0.0, 0.8, 0.4, alpha)
                glVertex3f(*segment['start']); glVertex3f(*segment['end'])
            glEnd()

            if self.highlight_line != -1:
                glLineWidth(4.0)
                glBegin(GL_LINES)
                glColor3f(1.0, 1.0, 1.0)
                for segment in self.path_data:
                    if segment.get('source_line') == self.highlight_line:
                        glVertex3f(*segment['start']); glVertex3f(*segment['end'])
                glEnd()
        
        if self.tool_pos:
            glEnable(GL_LIGHTING)
            self.draw_tool()
            glDisable(GL_LIGHTING)

    def draw_tool(self):
        glPushMatrix()
        glTranslatef(self.tool_pos[0], self.tool_pos[1], self.tool_pos[2])
        quad = gluNewQuadric()
        
        diameter = self.tool_library.get(self.current_tool_id, 10.0)
        radius = diameter / 2.0
        
        cutting_len = 20.0
        shank_len = 15.0
        shank_radius = radius * 0.8
        if shank_radius < 1.0: shank_radius = 1.0
        
        # REZNI DEO
        glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, [0.7, 0.7, 0.7, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.9, 0.9, 0.9, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 80.0)
        gluCylinder(quad, radius, radius, cutting_len, 24, 1)
        glPushMatrix(); glRotatef(180, 1,0,0); gluDisk(quad, 0, radius, 24, 1); glPopMatrix()
        glPushMatrix(); glTranslatef(0, 0, cutting_len); gluDisk(quad, 0, radius, 24, 1); glPopMatrix()

        # DRSKA
        glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
        glPushMatrix(); glTranslatef(0, 0, cutting_len)
        gluCylinder(quad, shank_radius, shank_radius, shank_len, 16, 1)
        glTranslatef(0, 0, shank_len); gluDisk(quad, 0, shank_radius, 16, 1); glPopMatrix()

        # VIZUELIZACIJA
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glColor4f(0.0, 1.0, 1.0, 0.2) 
        viz_radius = radius + 0.1
        gluCylinder(quad, viz_radius, viz_radius, cutting_len + 2, 24, 1)
        gluDisk(quad, viz_radius-0.5, viz_radius, 24, 1)
        glEnable(GL_LIGHTING)
        glPopMatrix()

    def draw_machine_box(self):
        mx, my, mz = self.machine_size
        glColor4f(1.0, 1.0, 0.0, 0.15)
        glLineWidth(1.0)
        glBegin(GL_LINE_LOOP); glVertex3f(0,0,0); glVertex3f(mx,0,0); glVertex3f(mx,my,0); glVertex3f(0,my,0); glEnd()
        glBegin(GL_LINE_LOOP); glVertex3f(0,0,mz); glVertex3f(mx,0,mz); glVertex3f(mx,my,mz); glVertex3f(0,my,mz); glEnd()
        glBegin(GL_LINES)
        glVertex3f(0,0,0); glVertex3f(0,0,mz); glVertex3f(mx,0,0); glVertex3f(mx,0,mz)
        glVertex3f(mx,my,0); glVertex3f(mx,my,mz); glVertex3f(0,my,0); glVertex3f(0,my,mz)
        glEnd()

    def draw_axes(self):
        glLineWidth(3.0); glBegin(GL_LINES)
        glColor3f(0.9, 0.2, 0.2); glVertex3f(0,0,0); glVertex3f(40,0,0)
        glColor3f(0.2, 0.8, 0.2); glVertex3f(0,0,0); glVertex3f(0,40,0)
        glColor3f(0.2, 0.6, 1.0); glVertex3f(0,0,0); glVertex3f(0,0,40)
        glEnd()

    def draw_grid(self):
        # --- NOVO: PRILAGODLJIVA MREZA ---
        if self.is_dark: glColor3f(0.3, 0.3, 0.3)
        else: glColor3f(0.7, 0.7, 0.7)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        
        # Uzimamo velicinu masine
        mx, my, _ = self.machine_size
        step = 50 # Svakih 50mm
        
        # Crtamo X linije (duz Y ose)
        for x in range(0, int(mx) + 1, step):
            glVertex3f(x, 0, 0)
            glVertex3f(x, my, 0)
            
        # Crtamo Y linije (duz X ose)
        for y in range(0, int(my) + 1, step):
            glVertex3f(0, y, 0)
            glVertex3f(mx, y, 0)
            
        glEnd()

    def mousePressEvent(self, e): self.lastPos = e.pos()
    def mouseMoveEvent(self, e):
        dx = e.x()-self.lastPos.x(); dy = e.y()-self.lastPos.y()
        if e.buttons() & Qt.LeftButton: self.rotation_x += dy; self.rotation_z += dx
        elif e.buttons() & Qt.RightButton: self.pan_x += dx*0.5; self.pan_y -= dy*0.5
        self.lastPos = e.pos(); self.update()
    def wheelEvent(self, e):
        if e.angleDelta().y() > 0: self.camera_distance *= 0.9
        else: self.camera_distance *= 1.1
        self.update()