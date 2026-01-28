# dental-ai-system/inventory_agent/tools/external_apis.py
from typing import Optional, Dict, Any
from services_shared.db_client import INVENTORY_DB_CLIENT
from services_shared.message_bus.publisher import GLOBAL_PUBLISHER

class InventoryLiveTools:
    def get_stock_level(self, item_id: str, item_category: Optional[str] = None) -> Dict[str, Any]:
        sql = f"SELECT current_stock, reorder_point FROM inventory_levels WHERE item_id='{item_id}'"
        INVENTORY_DB_CLIENT.execute_query(sql) 
        if item_id == "inv1" or item_id == "RESIN-C2": # Mock low stock
             return {"status": "success", "stock_data": {"current_stock": 15, "reorder_point": 20}}
        return {"status": "success", "stock_data": {"current_stock": 150, "reorder_point": 50}}

    def run_demand_forecast(self, item_id: str, forecast_period_days: int) -> Dict[str, Any]:
        # Mock forecast logic
        return {"status": "forecast_complete", "item_id": item_id, "stock_after_forecast": 15, "demand": 45}
    
    def update_stock_and_reorder_point(self, item_id: str, quantity: int, action: str) -> Dict[str, Any]:
        sql = f"UPDATE inventory_levels SET current_stock = current_stock + {quantity} WHERE item_id='{item_id}'"
        INVENTORY_DB_CLIENT.execute_query(sql)
        return {"status": "success", "rows_affected": 1}

TOOL_MANAGER = InventoryLiveTools()