"""
CSV Import Script for Inventory and Treatments
Usage: python import_csv.py --file <csv_file> --type <inventory|treatments>
"""

import csv
import argparse
from database import SessionLocal
from models import InventoryItem, Treatment, Hospital

def import_inventory(csv_file, hospital_id):
    db = SessionLocal()
    try:
        added = 0
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if already exists
                existing = db.query(InventoryItem).filter(
                    InventoryItem.name == row['name'],
                    InventoryItem.hospital_id == hospital_id
                ).first()
                
                if existing:
                    print(f"⚠ Skipping '{row['name']}' - already exists")
                    continue
                
                item = InventoryItem(
                    name=row['name'],
                    quantity=int(row['quantity']),
                    unit=row['unit'],
                    min_threshold=int(row['min_threshold']),
                    buying_cost=float(row['buying_cost']),
                    hospital_id=hospital_id
                )
                db.add(item)
                added += 1
        
        db.commit()
        print(f"\n✅ Successfully imported {added} inventory items!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

def import_treatments(csv_file):
    db = SessionLocal()
    try:
        added = 0
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if already exists
                existing = db.query(Treatment).filter(Treatment.name == row['name']).first()
                
                if existing:
                    print(f"⚠ Skipping '{row['name']}' - already exists")
                    continue
                
                treatment = Treatment(
                    name=row['name'],
                    cost=float(row['cost']),
                    price=float(row['price']),
                    duration=int(row['duration'])
                )
                db.add(treatment)
                added += 1
        
        db.commit()
        print(f"\n✅ Successfully imported {added} treatments!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import CSV data into database')
    parser.add_argument('--file', required=True, help='Path to CSV file')
    parser.add_argument('--type', required=True, choices=['inventory', 'treatments'], help='Type of data to import')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"CSV IMPORT - {args.type.upper()}")
    print("=" * 60)
    
    if args.type == 'inventory':
        # Get hospital
        db = SessionLocal()
        hospital = db.query(Hospital).first()
        db.close()
        
        if not hospital:
            print("❌ No hospital found. Please create a hospital first.")
        else:
            print(f"Using Hospital: {hospital.name}\n")
            import_inventory(args.file, hospital.id)
    else:
        import_treatments(args.file)
    
    print("=" * 60)
