import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor
from PySide6.QtCore import QRegularExpression

# --- BOJENJE SINTAKSE ---
class GCodeHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []

        # G i M kodovi (Plavo)
        g_format = QTextCharFormat()
        g_format.setForeground(QColor("#569CD6")) 
        g_format.setFontWeight(QFont.Bold)
        self.highlightingRules.append((QRegularExpression(r"[GM]\d+"), g_format))

        # Koordinate (Narandžasto/Crveno)
        coord_format = QTextCharFormat()
        coord_format.setForeground(QColor("#CE9178"))
        self.highlightingRules.append((QRegularExpression(r"[XYZIJR]-?\d*\.?\d*"), coord_format))

        # Feed i Speed (Zeleno svetlo)
        fs_format = QTextCharFormat()
        fs_format.setForeground(QColor("#B5CEA8"))
        self.highlightingRules.append((QRegularExpression(r"[FS]\d*\.?\d*"), fs_format))

        # Komentari (Sivo)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.highlightingRules.append((QRegularExpression(r"\(.*\)"), comment_format))
        self.highlightingRules.append((QRegularExpression(r";.*"), comment_format))

        # N brojevi (Tamno sivo)
        n_format = QTextCharFormat()
        n_format.setForeground(QColor("#808080"))
        self.highlightingRules.append((QRegularExpression(r"N\d+"), n_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            match = pattern.match(text)
            while match.hasMatch():
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
                match = pattern.match(text, match.capturedStart() + match.capturedLength())

# --- MANIPULACIJA TEKSTOM ---
class CodeTransformer:
    @staticmethod
    def modify_values(text, multipliers={'X':1, 'Y':1, 'Z':1, 'I':1, 'J':1}, offsets={'X':0, 'Y':0, 'Z':0}):
        new_lines = []
        lines = text.split('\n')
        pattern = re.compile(r'([XYZIJ])([-\d\.]+)')
        
        for line in lines:
            if line.strip().startswith('(') or line.strip().startswith(';'):
                new_lines.append(line)
                continue
            
            def replacement(match):
                axis = match.group(1)
                val = float(match.group(2))
                if axis in multipliers: val *= multipliers[axis]
                if axis in offsets: val += offsets[axis]
                return f"{axis}{val:.3f}"
            
            new_lines.append(pattern.sub(replacement, line))
        return '\n'.join(new_lines)

    @staticmethod
    def mirror_g2_g3(text, axis_mirrored):
        if not axis_mirrored: return text
        new_lines = []
        for line in text.split('\n'):
            if 'G2' in line: line = line.replace('G2', 'TEMP').replace('G02', 'TEMP')
            if 'G3' in line: line = line.replace('G3', 'G2').replace('G03', 'G2')
            line = line.replace('TEMP', 'G3')
            new_lines.append(line)
        return '\n'.join(new_lines)

    # --- NOVO: SWAP AXES (MAHO STYLE) ---
    @staticmethod
    def swap_axes_custom(text):
        new_lines = []
        # Trazimo slova X, Y, Z, I, J, K i broj iza njih
        pattern = re.compile(r'([XYZIJK])([-\d\.]+)')
        
        for line in text.split('\n'):
            # Preskacemo komentare
            if line.strip().startswith('(') or line.strip().startswith(';'):
                new_lines.append(line)
                continue
            
            def replacement(match):
                axis = match.group(1).upper()
                val = float(match.group(2))
                
                # Logika zamene:
                # X -> X- (Invert)
                # Y -> Z
                # Z -> Y
                # I -> I- (Invert, prati X)
                # J -> K (Prati Y koji postaje Z)
                # K -> J (Prati Z koji postaje Y)
                
                if axis == 'X':
                    return f"X{-val:.3f}"
                elif axis == 'Y':
                    return f"Z{val:.3f}"
                elif axis == 'Z':
                    return f"Y{val:.3f}"
                elif axis == 'I':
                    return f"I{-val:.3f}"
                elif axis == 'J':
                    return f"K{val:.3f}"
                elif axis == 'K':
                    return f"J{val:.3f}"
                else:
                    return match.group(0) # Ostalo ne diramo

            new_line = pattern.sub(replacement, line)
            new_lines.append(new_line)
            
        return '\n'.join(new_lines)