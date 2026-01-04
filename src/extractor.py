"""Metadata extraction core logic"""

import os
import re
import struct
from typing import Dict, List, Optional, Any

from .constants import EXIF_TAGS, GPS_TAGS


class MetadataExtractor:
    def __init__(self):
        self.metadata: Dict[str, Any] = {}
        self.warnings: List[str] = []
        
    def extract(self, filepath: str) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        self.metadata = {
            'filename': os.path.basename(filepath),
            'filepath': filepath,
            'size': os.path.getsize(filepath),
            'extension': os.path.splitext(filepath)[1].lower()
        }
        
        ext = self.metadata['extension']
        
        if ext in ['.jpg', '.jpeg', '.tiff', '.tif']:
            self._extract_exif(filepath)
        elif ext == '.png':
            self._extract_png(filepath)
        elif ext == '.pdf':
            self._extract_pdf(filepath)
        elif ext in ['.mp3']:
            self._extract_mp3(filepath)
        elif ext in ['.docx', '.xlsx', '.pptx']:
            self._extract_office(filepath)
        
        return self.metadata
    
    def _extract_exif(self, filepath: str):
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            
            exif_start = data.find(b'\xFF\xE1')
            if exif_start == -1:
                return
            
            if data[exif_start+4:exif_start+10] != b'Exif\x00\x00':
                return
            
            tiff_start = exif_start + 10
            byte_order = data[tiff_start:tiff_start+2]
            
            if byte_order == b'II':
                endian = '<'
            elif byte_order == b'MM':
                endian = '>'
            else:
                return
            
            ifd_offset = struct.unpack(endian + 'I', data[tiff_start+4:tiff_start+8])[0]
            
            exif_data = {}
            gps_data = {}
            
            self._parse_ifd(data, tiff_start, ifd_offset, endian, exif_data, gps_data)
            
            if exif_data:
                self.metadata['exif'] = exif_data
            if gps_data:
                self.metadata['gps'] = gps_data
                coords = self._calculate_coords(gps_data)
                if coords:
                    self.metadata['coordinates'] = coords
                    
        except Exception as e:
            self.warnings.append(f"EXIF parsing error: {e}")
    
    def _parse_ifd(self, data: bytes, tiff_start: int, ifd_offset: int, 
                  endian: str, exif_data: Dict, gps_data: Dict):
        try:
            pos = tiff_start + ifd_offset
            num_entries = struct.unpack(endian + 'H', data[pos:pos+2])[0]
            
            for i in range(num_entries):
                entry_pos = pos + 2 + (i * 12)
                tag = struct.unpack(endian + 'H', data[entry_pos:entry_pos+2])[0]
                data_type = struct.unpack(endian + 'H', data[entry_pos+2:entry_pos+4])[0]
                count = struct.unpack(endian + 'I', data[entry_pos+4:entry_pos+8])[0]
                value_offset = struct.unpack(endian + 'I', data[entry_pos+8:entry_pos+12])[0]
                
                if tag in EXIF_TAGS:
                    tag_name = EXIF_TAGS[tag]
                    value = self._read_value(data, tiff_start, data_type, count, value_offset, endian)
                    if value:
                        exif_data[tag_name] = value
                        
                elif tag in GPS_TAGS:
                    tag_name = GPS_TAGS[tag]
                    value = self._read_value(data, tiff_start, data_type, count, value_offset, endian)
                    if value:
                        gps_data[tag_name] = value
        except:
            pass
    
    def _read_value(self, data: bytes, tiff_start: int, data_type: int, 
                   count: int, value_offset: int, endian: str):
        try:
            type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}
            size = type_sizes.get(data_type, 1) * count
            
            if size <= 4:
                raw = struct.pack(endian + 'I', value_offset)[:size]
            else:
                offset = tiff_start + value_offset
                raw = data[offset:offset+size]
            
            if data_type == 2:
                return raw.decode('ascii', errors='ignore').strip('\x00')
            elif data_type == 3:
                return struct.unpack(endian + 'H', raw[:2])[0]
            elif data_type == 4:
                return struct.unpack(endian + 'I', raw[:4])[0]
            elif data_type == 5:
                num = struct.unpack(endian + 'I', raw[:4])[0]
                den = struct.unpack(endian + 'I', raw[4:8])[0]
                return num / den if den else 0
        except:
            return None
        return None
    
    def _calculate_coords(self, gps_data: Dict) -> Optional[Dict]:
        try:
            if 'GPSLatitude' not in gps_data or 'GPSLongitude' not in gps_data:
                return None
            
            lat = gps_data.get('GPSLatitude', 0)
            lon = gps_data.get('GPSLongitude', 0)
            
            lat_ref = gps_data.get('GPSLatitudeRef', 'N')
            lon_ref = gps_data.get('GPSLongitudeRef', 'E')
            
            if lat_ref == 'S':
                lat = -lat
            if lon_ref == 'W':
                lon = -lon
            
            return {
                'latitude': lat,
                'longitude': lon,
                'google_maps': f"https://www.google.com/maps?q={lat},{lon}"
            }
        except:
            return None
    
    def _extract_png(self, filepath: str):
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            
            if data[:8] != b'\x89PNG\r\n\x1a\n':
                return
            
            png_data = {}
            pos = 8
            
            while pos < len(data):
                length = struct.unpack('>I', data[pos:pos+4])[0]
                chunk_type = data[pos+4:pos+8].decode('ascii', errors='ignore')
                chunk_data = data[pos+8:pos+8+length]
                
                if chunk_type == 'IHDR':
                    png_data['width'] = struct.unpack('>I', chunk_data[:4])[0]
                    png_data['height'] = struct.unpack('>I', chunk_data[4:8])[0]
                    png_data['bit_depth'] = chunk_data[8]
                    png_data['color_type'] = chunk_data[9]
                    
                elif chunk_type == 'tEXt':
                    null_pos = chunk_data.find(b'\x00')
                    if null_pos > 0:
                        key = chunk_data[:null_pos].decode('latin-1')
                        value = chunk_data[null_pos+1:].decode('latin-1')
                        png_data[key] = value
                        
                elif chunk_type == 'IEND':
                    break
                    
                pos += 12 + length
            
            if png_data:
                self.metadata['png'] = png_data
                
        except Exception as e:
            self.warnings.append(f"PNG parsing error: {e}")
    
    def _extract_pdf(self, filepath: str):
        try:
            with open(filepath, 'rb') as f:
                data = f.read(10000)
            
            pdf_data = {}
            
            if not data.startswith(b'%PDF'):
                return
            
            pdf_data['version'] = data[:8].decode('ascii', errors='ignore').strip()
            
            info_patterns = [
                (b'/Title', 'title'),
                (b'/Author', 'author'),
                (b'/Subject', 'subject'),
                (b'/Creator', 'creator'),
                (b'/Producer', 'producer'),
                (b'/CreationDate', 'creation_date'),
                (b'/ModDate', 'modification_date'),
            ]
            
            for pattern, key in info_patterns:
                match = re.search(pattern + rb'\s*\(([^)]+)\)', data)
                if match:
                    pdf_data[key] = match.group(1).decode('latin-1', errors='ignore')
            
            if pdf_data:
                self.metadata['pdf'] = pdf_data
                
        except Exception as e:
            self.warnings.append(f"PDF parsing error: {e}")

    def _extract_mp3(self, filepath: str):
        try:
            with open(filepath, 'rb') as f:
                data = f.read(4096)
            
            if data[:3] != b'ID3':
                return
                
            mp3_data = {}
            mp3_data['id3_version'] = f"2.{data[3]}.{data[4]}"
            
            if mp3_data:
                self.metadata['mp3'] = mp3_data
        except:
            pass
    
    def _extract_office(self, filepath: str):
        try:
            import zipfile
            
            with zipfile.ZipFile(filepath, 'r') as zf:
                if 'docProps/core.xml' in zf.namelist():
                    core = zf.read('docProps/core.xml').decode('utf-8')
                    
                    office_data = {}
                    patterns = [
                        (r'<dc:creator>([^<]+)</dc:creator>', 'creator'),
                        (r'<dc:title>([^<]+)</dc:title>', 'title'),
                        (r'<dc:subject>([^<]+)</dc:subject>', 'subject'),
                        (r'<cp:lastModifiedBy>([^<]+)</cp:lastModifiedBy>', 'last_modified_by'),
                        (r'<dcterms:created[^>]*>([^<]+)</dcterms:created>', 'created'),
                        (r'<dcterms:modified[^>]*>([^<]+)</dcterms:modified>', 'modified'),
                    ]
                    
                    for pattern, key in patterns:
                        match = re.search(pattern, core)
                        if match:
                            office_data[key] = match.group(1)
                    
                    if office_data:
                        self.metadata['office'] = office_data
        except:
            pass
