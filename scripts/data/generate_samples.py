#!/usr/bin/env python3
"""
Упрощенная обертка для генерации embedded sample данных

Использует SampleDataGenerator из пакета bquant.data.samples
"""

import sys
import argparse
from pathlib import Path

# Добавляем корневую папку проекта в path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bquant.data.samples import SampleDataGenerator


def main():
    """Основная функция CLI."""
    parser = argparse.ArgumentParser(
        description="Generate embedded sample data using BQuant package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_samples.py --all
  python scripts/generate_samples.py --dataset tv_xauusd_1h
  python scripts/generate_samples.py --validate-sources
        """
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Generate all configured datasets'
    )
    
    parser.add_argument(
        '--dataset',
        type=str,
        help='Generate specific dataset (tv_xauusd_1h or mt_xauusd_m15)'
    )
    
    parser.add_argument(
        '--source',
        type=str,
        help='Custom source file path (use with --dataset)'
    )
    
    parser.add_argument(
        '--validate-sources',
        action='store_true',
        help='Validate that all source files exist'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Настраиваем логирование
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    generator = SampleDataGenerator()
    
    try:
        if args.validate_sources:
            print("Validating source files...")
            results = generator.validate_source_files()
            
            all_valid = all(results.values())
            
            print("\nValidation Results:")
            for dataset, valid in results.items():
                status = "✓" if valid else "✗"
                print(f"  {status} {dataset}")
            
            if all_valid:
                print("\n🎉 All source files are available!")
                return 0
            else:
                print("\n⚠️  Some source files are missing!")
                return 1
        
        elif args.all:
            print("Generating all datasets...")
            results = generator.generate_all()
            
            print("\nGeneration Results:")
            for dataset, file_path in results.items():
                print(f"  ✓ {dataset} -> {file_path}")
            
            print(f"\n🎉 Successfully generated {len(results)} datasets!")
            return 0
        
        elif args.dataset:
            print(f"Generating dataset: {args.dataset}")
            
            output_file = generator.generate_embedded_data(args.dataset, args.source)
            
            print(f"\nGenerated: {output_file}")
            print("\n🎉 Generation completed successfully!")
            return 0
        
        else:
            parser.print_help()
            return 1
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
