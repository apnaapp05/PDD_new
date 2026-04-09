# CSV Import Guide

## Inventory Import (`inventory_template.csv`)

**Columns:**
- `name`: Item name (e.g., "Dental Gloves (Box)")
- `quantity`: Current stock quantity (integer)
- `unit`: Unit of measurement (e.g., "box", "piece", "pack")
- `min_threshold`: Minimum threshold for reorder alert (integer)
- `buying_cost`: Cost per unit in PKR (decimal)

**Notes:**
- The agent will automatically update `min_threshold` based on usage patterns
- Set initial threshold values based on your estimates

## Treatments Import (`treatments_template.csv`)

**Columns:**
- `name`: Treatment name
- `cost`: Cost to perform treatment (COGS - materials + overhead)
- `price`: Price charged to patient
- `duration`: Typical duration in minutes

**Notes:**
- Profit margin = (price - cost) / price * 100%
- The Revenue Agent uses these values for profitability analysis

## How to Use

1. **Edit CSV files** in Excel or any spreadsheet software
2. **Save as CSV** (comma-separated values)
3. **Import via API** or use the CSV import script (to be created)

## Example Import Script

```python
# Import inventory
python import_csv.py --file inventory_template.csv --type inventory

# Import treatments
python import_csv.py --file treatments_template.csv --type treatments
```
