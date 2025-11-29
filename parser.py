import math
import re

class SimpleParser:
    def __init__(self):
        self.rapid_feed = 3000.0 
        self.reset_stats()

    def set_rapid_feed(self, feed):
        self.rapid_feed = float(feed)

    def reset_stats(self):
        self.min_point = [0, 0, 0]
        self.max_point = [0, 0, 0]
        self.total_length = 0.0
        self.estimated_time = 0.0

    # --- NOVO: Funkcija za detekciju gresaka ---
    def scan_for_errors(self, text, tool_library, machine_limits):
        """
        Vraca listu problema: 
        [{'line': 10, 'type': 'CRITICAL', 'msg': 'Crash detected!'}, ...]
        """
        issues = []
        
        # Stanje simulacije
        cx, cy, cz = 0.0, 0.0, 0.0 # Pretpostavljamo start na nuli
        current_feed = 0.0
        current_spindle = 0.0
        current_tool = 0
        
        # Limiti
        lim_x, lim_y, lim_z = machine_limits
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_num = i + 1
            line = line.upper().strip()
            if not line: continue
            
            # 1. Citanje parametara
            # Trazimo F, S, T pre nego sto obradimo kretanje
            if 'F' in line:
                m = re.search(r'F([\d\.]+)', line)
                if m: current_feed = float(m.group(1))
            
            if 'S' in line:
                m = re.search(r'S([\d\.]+)', line)
                if m: current_spindle = float(m.group(1))
                
            if 'T' in line:
                m = re.search(r'T(\d+)', line)
                if m: 
                    t_val = int(m.group(1))
                    # PROVERA: Da li alat postoji?
                    if str(t_val) not in tool_library and t_val != 0:
                        issues.append({'line': line_num, 'type': 'WARNING', 'msg': f"Tool T{t_val} not in Tool Library."})
                    current_tool = t_val

            # Kretanje
            clean_line = line.split('(')[0].split(';')[0]
            if not clean_line: continue
            
            # Parsiranje koordinata
            nx, ny, nz = cx, cy, cz
            mode = None
            
            # Prosta detekcija G koda
            if 'G0' in clean_line or 'G00' in clean_line: mode = 'G0'
            elif 'G1' in clean_line or 'G01' in clean_line: mode = 'G1'
            elif 'G2' in clean_line or 'G02' in clean_line: mode = 'G2'
            elif 'G3' in clean_line or 'G03' in clean_line: mode = 'G3'
            
            # Koordinate
            tokens = clean_line.replace('X',' X').replace('Y',' Y').replace('Z',' Z').split()
            moved = False
            for token in tokens:
                if token.startswith('X'): nx = float(token[1:]); moved = True
                if token.startswith('Y'): ny = float(token[1:]); moved = True
                if token.startswith('Z'): nz = float(token[1:]); moved = True

            if moved:
                # 2. PROVERA: Limiti masine
                if nx > lim_x or ny > lim_y or nz > lim_z:
                    issues.append({'line': line_num, 'type': 'WARNING', 'msg': f"Move exceeds machine limits ({nx},{ny},{nz})"})
                
                # 3. PROVERA: Sudar (G0 ispod nule)
                # Ako idemo brzo (G0) i cilj je ispod nule
                if mode == 'G0' and nz < 0.0:
                     issues.append({'line': line_num, 'type': 'CRITICAL', 'msg': f"Rapid move (G0) into material (Z{nz})!"})
                
                # Ako idemo brzo (G0) horizontalno, a vec smo ispod nule
                if mode == 'G0' and cz < 0.0 and (nx != cx or ny != cy):
                     issues.append({'line': line_num, 'type': 'CRITICAL', 'msg': f"Rapid lateral move inside material (Z{cz})!"})

                # 4. PROVERA: Nema posmaka (F)
                if mode in ['G1', 'G2', 'G3']:
                    if current_feed <= 0.001:
                        issues.append({'line': line_num, 'type': 'ERROR', 'msg': "Cutting move without Feed Rate (F)!"})
                    
                    # 5. PROVERA: Vreteno ne radi (S)
                    # (Ovo je warning jer nekad ljudi pale vreteno rucno)
                    if current_spindle <= 0.001:
                         issues.append({'line': line_num, 'type': 'WARNING', 'msg': "Cutting move with Spindle Speed 0 (S)!"})

                cx, cy, cz = nx, ny, nz

        return issues

    # --- STARA FUNKCIJA (Ostaje ista, samo je kopiraj ispod) ---
    def parse(self, text):
        lines_to_draw = []
        self.reset_stats()
        current_feed = 100.0
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
        cx, cy, cz = 0.0, 0.0, 0.0
        current_mode = 'G0'
        current_tool = 1
        points_found = False
        current_accumulated_dist = 0.0 
        raw_lines = text.split('\n')
        for line_idx, line in enumerate(raw_lines):
            line = line.upper().strip()
            if not line: continue
            if 'F' in line:
                m = re.search(r'F([\d\.]+)', line); 
                if m: current_feed = float(m.group(1))
            if 'T' in line:
                m = re.search(r'T(\d+)', line)
                if m: current_tool = int(m.group(1))
            clean = line.split('(')[0].split(';')[0]
            if not clean: continue
            start_pos = (cx, cy, cz)
            min_x, max_x = min(min_x, cx), max(max_x, cx)
            min_y, max_y = min(min_y, cy), max(max_y, cy)
            min_z, max_z = min(min_z, cz), max(max_z, cz)
            points_found = True
            tokens = clean.replace('G', ' G').replace('X', ' X').replace('Y', ' Y').replace('Z', ' Z').replace('I', ' I').replace('J', ' J').replace('R', ' R').split()
            nx, ny, nz = cx, cy, cz; i_v, j_v, r_v = 0,0,0; mv = False; is_d = False; d_r = 0.0
            for t in tokens:
                if not t: continue
                try:
                    c = t[0]; v = float(t[1:])
                    if c == 'G':
                        code = int(v)
                        if code in [0,1,2,3]: current_mode = f'G{code}'
                        elif code in [81,83]: current_mode = f'G{code}'; is_d = True
                    elif c == 'X': nx=v; mv=True
                    elif c == 'Y': ny=v; mv=True
                    elif c == 'Z': nz=v; mv=True
                    elif c == 'I': i_v=v
                    elif c == 'J': j_v=v
                    elif c == 'R': r_v=v; d_r=v
                except: pass
            
            segs = []
            if mv or is_d:
                base = {'source_line': line_idx, 'tool': current_tool}
                if is_d:
                    segs.append({**base, 'type': 'G0', 'start': start_pos, 'end': (nx, ny, d_r)})
                    segs.append({**base, 'type': 'DRILL', 'start': (nx, ny, d_r), 'end': (nx, ny, nz)})
                    nz = d_r
                elif current_mode in ['G2', 'G3']:
                    arcs, al = self.generate_arc((cx, cy), (nx, ny), (cx+i_v, cy+j_v), current_mode, cz, nz, line_idx, current_tool)
                    segs.extend(arcs)
                else:
                    segs.append({**base, 'type': current_mode, 'start': start_pos, 'end': (nx, ny, nz)})
                
                for s in segs:
                    dx, dy, dz = s['end'][0]-s['start'][0], s['end'][1]-s['start'][1], s['end'][2]-s['start'][2]
                    sl = math.sqrt(dx*dx+dy*dy+dz*dz)
                    s['dist_start'] = current_accumulated_dist; current_accumulated_dist += sl; s['dist_end'] = current_accumulated_dist
                    lines_to_draw.append(s)
                    
                    # Time calc
                    if s['type'] == 'G0': self.estimated_time += sl / self.rapid_feed
                    elif current_feed > 0: self.estimated_time += sl / current_feed

                cx, cy, cz = nx, ny, nz
        
        self.total_length = current_accumulated_dist
        if points_found:
            self.min_point = [min(min_x, cx), min(min_y, cy), min(min_z, cz)]
            self.max_point = [max(max_x, cx), max(max_y, cy), max(max_z, cz)]
        return lines_to_draw

    def generate_arc(self, start, end, center, mode, start_z, end_z, line_idx, tool_id):
        segments = []
        radius = math.sqrt((start[0]-center[0])**2 + (start[1]-center[1])**2)
        if radius < 0.001: return [], 0
        start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
        end_angle = math.atan2(end[1] - center[1], end[0] - center[0])
        if mode == 'G2': 
            if end_angle > start_angle: end_angle -= 2 * math.pi
        else:
            if end_angle < start_angle: end_angle += 2 * math.pi
        sweep = abs(end_angle - start_angle)
        length = sweep * radius
        steps = max(6, int(sweep * radius * 0.5))
        for i in range(1, steps + 1):
            theta = start_angle + i * (sweep / steps) * (-1 if mode=='G2' else 1)
            # Fix za smer
            if mode == 'G2': theta = start_angle + i * ((end_angle - start_angle) / steps)
            else: theta = start_angle + i * ((end_angle - start_angle) / steps)
            
            cur_x = center[0] + radius * math.cos(theta)
            cur_y = center[1] + radius * math.sin(theta)
            cur_z = start_z + i * ((end_z - start_z) / steps)
            prv_x = center[0] + radius * math.cos(start_angle + (i-1)*((end_angle-start_angle)/steps))
            prv_y = center[1] + radius * math.sin(start_angle + (i-1)*((end_angle-start_angle)/steps))
            prv_z = start_z + (i-1)*((end_z-start_z)/steps)
            segments.append({'source_line': line_idx, 'tool': tool_id, 'type': mode, 'start': (prv_x, prv_y, prv_z), 'end': (cur_x, cur_y, cur_z)})
        return segments, length