"""Output formatting for Metadata Extractor"""

from typing import Dict
from .constants import Colors, VERSION


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
    print(f"{Colors.CYAN}{'─' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}File Information{Colors.RESET}")
    print(f"{Colors.CYAN}{'─' * 60}{Colors.RESET}")
    
    print(f"  Filename: {metadata.get('filename')}")
    print(f"  Size: {metadata.get('size'):,} bytes")
    print(f"  Type: {metadata.get('extension')}")
    
    if 'exif' in metadata:
        print(f"\n{Colors.BOLD}EXIF Data:{Colors.RESET}")
        for key, value in metadata['exif'].items():
            print(f"  {key}: {value}")
    
    if 'coordinates' in metadata:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}[!] GPS Location Found:{Colors.RESET}")
        coords = metadata['coordinates']
        print(f"  Latitude: {coords.get('latitude')}")
        print(f"  Longitude: {coords.get('longitude')}")
        print(f"  Maps: {coords.get('google_maps')}")
    
    if 'png' in metadata:
        print(f"\n{Colors.BOLD}PNG Data:{Colors.RESET}")
        for key, value in metadata['png'].items():
            print(f"  {key}: {value}")
    
    if 'pdf' in metadata:
        print(f"\n{Colors.BOLD}PDF Data:{Colors.RESET}")
        for key, value in metadata['pdf'].items():
            print(f"  {key}: {value}")
    
    if 'office' in metadata:
        print(f"\n{Colors.BOLD}Office Data:{Colors.RESET}")
        for key, value in metadata['office'].items():
            print(f"  {key}: {value}")
