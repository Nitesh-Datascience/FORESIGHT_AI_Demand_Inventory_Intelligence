FORESIGHT raw inputs
=====================
Required:
- sales_transactions.csv
- sku_master.csv
- store_master.csv
- inventory_snapshot.csv
- promotions.csv

Optional:
- sku_inventory_flags.csv (ground-truth anomaly labels)

The supplied retail_store_inventory(1).csv is a separate legacy dataset and is not used by this FORESIGHT pipeline.
The Zidio brief defines a relational sales/SKU/calendar/inventory design; this implementation adapts the supplied relational retail dataset to that scope.
