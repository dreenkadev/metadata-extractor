#!/usr/bin/env python3
"""Metadata Extractor - Entry point"""

import argparse
import json

from src import MetadataExtractor, print_banner, print_result, Colors


def demo_mode():
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
