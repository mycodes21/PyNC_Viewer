import ezdxf

class DXFExporter:
    def export(self, filepath, lines_data):
        """
        Kreira DXF fajl na osnovu linija iz parsera.
        lines_data: Lista rečnika koju vraća parser.py
        """
        try:
            # Kreiramo novi DXF dokument (Verzija R2010 je najkompatibilnija)
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # --- KREIRANJE SLOJEVA (LAYERS) ---
            # FEED Layer (Radni hod) - Plava boja (color 5)
            doc.layers.new(name='FEED', dxfattribs={'color': 5})
            
            # RAPID Layer (Brzi hod) - Crvena boja (color 1)
            doc.layers.new(name='RAPID', dxfattribs={'color': 1})
            
            # DRILL Layer (Bušenje) - Žuta boja (color 2)
            doc.layers.new(name='DRILL', dxfattribs={'color': 2})

            # --- CRTANJE LINIJA ---
            for segment in lines_data:
                start = segment['start'] # (x, y, z)
                end = segment['end']     # (x, y, z)
                typ = segment['type']
                
                layer_name = 'FEED'
                if typ == 'G0':
                    layer_name = 'RAPID'
                elif typ == 'DRILL':
                    layer_name = 'DRILL'
                
                # Dodajemo 3D liniju u DXF
                msp.add_line(start, end, dxfattribs={'layer': layer_name})

            # Cuvanje fajla
            doc.saveas(filepath)
            return True, "Success"
            
        except Exception as e:
            return False, str(e)