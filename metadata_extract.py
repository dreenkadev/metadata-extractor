#!/usr/bin/env python3
"""
Metadata Extractor - Extract metadata from various file types

Features:
- Image EXIF data
- PDF metadata  
- Document properties
- GPS coordinates
- Camera info
- Software info
"""

import argparse
import json
import os
import re
import struct
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

VERSION = "1.0.0"

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


EXIF_TAGS = {
    0x010F: 'Make',
    0x0110: 'Model',
    0x0112: 'Orientation',
    0x011A: 'XResolution',
    0x011B: 'YResolution',
    0x0132: 'DateTime',
    0x829A: 'ExposureTime',
    0x829D: 'FNumber',
    0x8827: 'ISOSpeedRatings',
    0x9003: 'DateTimeOriginal',
    0x9004: 'DateTimeDigitized',
    0x920A: 'FocalLength',
    0xA001: 'ColorSpace',
    0xA002: 'PixelXDimension',
    0xA003: 'PixelYDimension',
    0xA430: 'CameraOwnerName',
    0xA431: 'BodySerialNumber',
    0xA432: 'LensSpecification',
    0xA433: 'LensMake',
    0xA434: 'LensModel',
}

GPS_TAGS = {
    0x0001: 'GPSLatitudeRef',
    0x0002: 'GPSLatitude',
    0x0003: 'GPSLongitudeRef',
    0x0004: 'GPSLongitude',
    0x0005: 'GPSAltitudeRef',
    0x0006: 'GPSAltitude',
    0x001D: 'GPSDateStamp',
}


class MetadataExtractor:
    def __init__(self):
        self.metadata: Dict[str, Any] = {}
        self.warnings: List[str] = []
        
    def extract(self, filepath: str) -> Dict[str, Any]:
        """Extract metadata from file"""
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
            self.extract_exif(filepath)
        elif ext == '.png':
            self.extract_png(filepath)
        elif ext == '.pdf':
            self.extract_pdf(filepath)
        elif ext in ['.mp3']:
            self.extract_mp3(filepath)
        elif ext in ['.docx', '.xlsx', '.pptx']:
            self.extract_office(filepath)
        
        return self.metadata
    
    def extract_exif(self, filepath: str):
        """Extract EXIF data from JPEG/TIFF"""
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            
            # Find EXIF marker
            exif_start = data.find(b'\xFF\xE1')
            if exif_start == -1:
                return
            
            # Check for EXIF header
            if data[exif_start+4:exif_start+10] != b'Exif\x00\x00':
                return
            
            tiff_start = exif_start + 10
            
            # Check byte order
            byte_order = data[tiff_start:tiff_start+2]
            if byte_order == b'II':
                endian = '<'
            elif byte_order == b'MM':
                endian = '>'
            else:
                return
            
            # Parse IFD0
            ifd_offset = struct.unpack(endian + 'I', data[tiff_start+4:tiff_start+8])[0]
            
            exif_data = {}
            gps_data = {}
            
            self.parse_ifd(data, tiff_start, ifd_offset, endian, exif_data, gps_data)
            
            if exif_data:
                self.metadata['exif'] = exif_data
            if gps_data:
                self.metadata['gps'] = gps_data
                # Calculate coordinates
                coords = self.calculate_coords(gps_data)
                if coords:
                    self.metadata['coordinates'] = coords
                    
        except Exception as e:
            self.warnings.append(f"EXIF parsing error: {e}")
    
    def parse_ifd(self, data: bytes, tiff_start: int, ifd_offset: int, 
                  endian: str, exif_data: Dict, gps_data: Dict):
        """Parse IFD entries"""
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
                    value = self.read_value(data, tiff_start, data_type, count, value_offset, endian)
                    if value:
                        exif_data[tag_name] = value
                        
                elif tag in GPS_TAGS:
                    tag_name = GPS_TAGS[tag]
                    value = self.read_value(data, tiff_start, data_type, count, value_offset, endian)
                    if value:
                        gps_data[tag_name] = value
                        
        except:
            pass
    
    def read_value(self, data: bytes, tiff_start: int, data_type: int, 
                   count: int, value_offset: int, endian: str):
        """Read EXIF value"""
        try:
            type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}
            size = type_sizes.get(data_type, 1) * count
            
            if size <= 4:
                raw = struct.pack(endian + 'I', value_offset)[:size]
            else:
                offset = tiff_start + value_offset
                raw = data[offset:offset+size]
            
            if data_type == 2:  # ASCII
                return raw.decode('ascii', errors='ignore').strip('\x00')
            elif data_type == 3:  # SHORT
                return struct.unpack(endian + 'H', raw[:2])[0]
            elif data_type == 4:  # LONG
                return struct.unpack(endian + 'I', raw[:4])[0]
            elif data_type == 5:  # RATIONAL
                num = struct.unpack(endian + 'I', raw[:4])[0]
                den = struct.unpack(endian + 'I', raw[4:8])[0]
                return num / den if den else 0
                
        except:
            return None
        return None
    
    def calculate_coords(self, gps_data: Dict) -> Optional[Dict]:
        """Calculate GPS coordinates"""
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
    
    def extract_png(self, filepath: str):
        """Extract PNG metadata"""
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            
            # Check PNG signature
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
    
    def extract_pdf(self, filepath: str):
        """Extract PDF metadata"""
        try:
            with open(filepath, 'rb') as f:
                data = f.read(10000)  # Read first 10KB
            
            pdf_data = {}
            
            # Check PDF header
            if not data.startswith(b'%PDF'):
                return
            
            pdf_data['version'] = data[:8].decode('ascii', errors='ignore').strip()
            
            # Find Info dictionary
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

    def extract_mp3(self, filepath: str):
        """Extract MP3 ID3 tags"""
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
    
    def extract_office(self, filepath: str):
        """Extract Office document metadata"""
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


def print_banner():
    print(f"""{Colors.CYAN}
  __  __      _            _       _        
 |  \/  | ___| |_ __ _  __| | __ _| |_ __ _ 
 | |\/| |/ _ \ __/ _` |/ _` |/ _` | __/ _` |
 | |  | |  __/ || (_| | (_| | (_| | || (_| |
 |_|  |_|\___|\__\__,_|\__,_|\__,_|\__\__,_|
  _____      _                  _             
 | ____|_  _| |_ _ __ __ _  ___| |_ ___  _ __ 
 |  _| \ \/ / __| '__/ _` |/ __| __/ _ \| '__|
 | |___ >  <| |_| | | (_| | (__| || (_) | |   
 |_____/_/\_\\__|_|  \__,_|\___|\__\___/|_|   
{Colors.RESET}                                      v{VERSION}
""")


def print_result(metadata: Dict):
    """Print extracted metadata"""
    print(f"{Colors.CYAN}{'─' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}File Information{Colors.RESET}")
    print(f"{Colors.CYAN}{'─' * 60}{Colors.RESET}")
    
    print(f"  Filename: {metadata.get('filename')}")
    print(f"  Size: {metadata.get('size'):,} bytes")
    print(f"  Type: {metadata.get('extension')}")
    
    # EXIF data
    if 'exif' in metadata:
        print(f"\n{Colors.BOLD}EXIF Data:{Colors.RESET}")
        for key, value in metadata['exif'].items():
            print(f"  {key}: {value}")
    
    # GPS data
    if 'coordinates' in metadata:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}⚠ GPS Location Found:{Colors.RESET}")
        coords = metadata['coordinates']
        print(f"  Latitude: {coords.get('latitude')}")
        print(f"  Longitude: {coords.get('longitude')}")
        print(f"  Maps: {coords.get('google_maps')}")
    
    # PNG data
    if 'png' in metadata:
        print(f"\n{Colors.BOLD}PNG Data:{Colors.RESET}")
        for key, value in metadata['png'].items():
            print(f"  {key}: {value}")
    
    # PDF data
    if 'pdf' in metadata:
        print(f"\n{Colors.BOLD}PDF Data:{Colors.RESET}")
        for key, value in metadata['pdf'].items():
            print(f"  {key}: {value}")
    
    # Office data
    if 'office' in metadata:
        print(f"\n{Colors.BOLD}Office Data:{Colors.RESET}")
        for key, value in metadata['office'].items():
            print(f"  {key}: {value}")


def demo_mode():
    """Run demo"""
    print(f"{Colors.CYAN}Running demo...{Colors.RESET}\n")
    
    demo = {
        'filename': 'photo.jpg',
        'filepath': '/path/to/photo.jpg',
        'size': 2456789,
        'extension': '.jpg',
        'exif': {
            'Make': 'Canon',
            'Model': 'Canon EOS R5',
            'DateTime': '2024:01:15 10:30:45',
            'ExposureTime': 0.004,
            'FNumber': 2.8,
            'ISOSpeedRatings': 400,
        },
        'coordinates': {
            'latitude': 40.7128,
            'longitude': -74.0060,
            'google_maps': 'https://www.google.com/maps?q=40.7128,-74.0060'
        }
    }
    
    print_result(demo)


def main():
    parser = argparse.ArgumentParser(description="Metadata Extractor")
    parser.add_argument("file", nargs="?", help="File to analyze")
    parser.add_argument("-o", "--output", help="Output file (JSON)")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.demo:
        demo_mode()
        return
    
    if not args.file:
        print(f"{Colors.YELLOW}No file specified. Use --demo for demonstration.{Colors.RESET}")
        return
    
    try:
        extractor = MetadataExtractor()
        metadata = extractor.extract(args.file)
        print_result(metadata)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"\n{Colors.GREEN}Results saved to: {args.output}{Colors.RESET}")
            
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")


if __name__ == "__main__":
    main()
