from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from typing import Dict, List
import uuid

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# In-memory storage
rapps_db: Dict[str, dict] = {
    "qos-optimizer": {
        "rappId": "qos-optimizer",
        "name": "QoS Optimizer rApp",
        "state": "PRIMED",
        "reason": "Successfully primed and ready for instantiation",
        "packageLocation": "/packages/qos-optimizer-v1.0.csar",
        "packageName": "qos-optimizer-v1.0.csar",
        "rappInstances": {}
    }
}

@mcp.tool()
def get_rapps() -> List[dict]:
    """Get all rApps"""
    return list(rapps_db.values())

@mcp.tool()
def create_rapp(package_name: str) -> dict:
    """Create a new rApp"""
    rapp_id = f"rapp-{uuid.uuid4().hex[:8]}"
    new_rapp = {
        "rappId": rapp_id,
        "name": f"rApp {rapp_id}",
        "state": "COMMISSIONED",
        "reason": "rApp package uploaded and validated",
        "packageLocation": f"/packages/{package_name}",
        "packageName": package_name,
        "rappInstances": {}
    }
    rapps_db[rapp_id] = new_rapp
    return {"rappId": rapp_id, "message": "rApp created successfully"}

@mcp.tool()
def get_rapp(rapp_id: str) -> dict:
    """Get rApp by ID"""
    if rapp_id not in rapps_db:
        return {"error": "rApp not found"}
    return rapps_db[rapp_id]

@mcp.tool()
def delete_rapp(rapp_id: str) -> dict:
    """Delete rApp"""
    if rapp_id not in rapps_db:
        return {"error": "rApp not found"}
    del rapps_db[rapp_id]
    return {"message": "rApp deleted successfully"}

@mcp.tool()
def prime_rapp(rapp_id: str, prime_order: str) -> dict:
    """Prime or deprime rApp"""
    if rapp_id not in rapps_db:
        return {"error": "rApp not found"}
    
    rapp = rapps_db[rapp_id]
    if prime_order == "PRIME":
        rapp["state"] = "PRIMED"
        rapp["reason"] = "rApp primed successfully"
    else:
        rapp["state"] = "COMMISSIONED"
        rapp["reason"] = "rApp deprimed successfully"
    
    return {"message": f"rApp {prime_order.lower()} operation accepted"}

@mcp.tool()
def get_rapp_instances(rapp_id: str) -> List[dict]:
    """Get rApp instances"""
    if rapp_id not in rapps_db:
        return []
    
    rapp = rapps_db[rapp_id]
    return list(rapp["rappInstances"].values())

@mcp.tool()
def create_rapp_instance(rapp_id: str, instance_id: str = None) -> dict:
    """Create rApp instance"""
    if rapp_id not in rapps_db:
        return {"error": "rApp not found"}
    
    rapp = rapps_db[rapp_id]
    if rapp["state"] != "PRIMED":
        return {"error": "rApp must be primed before creating instances"}
    
    if not instance_id:
        instance_id = f"instance-{uuid.uuid4().hex[:8]}"
    
    new_instance = {
        "rappInstanceId": instance_id,
        "state": "UNDEPLOYED",
        "reason": "Instance created successfully"
    }
    
    rapp["rappInstances"][instance_id] = new_instance
    return {"rappInstanceId": instance_id, "message": "Instance created successfully"}

@mcp.tool()
def get_rapp_instance(rapp_id: str, instance_id: str) -> dict:
    """Get rApp instance"""
    if rapp_id not in rapps_db:
        return {"error": "rApp not found"}
    
    rapp = rapps_db[rapp_id]
    if instance_id not in rapp["rappInstances"]:
        return {"error": "Instance not found"}
    
    return rapp["rappInstances"][instance_id]

@mcp.tool()
def delete_rapp_instance(rapp_id: str, instance_id: str) -> dict:
    """Delete rApp instance"""
    if rapp_id not in rapps_db:
        return {"error": "rApp not found"}
    
    rapp = rapps_db[rapp_id]
    if instance_id not in rapp["rappInstances"]:
        return {"error": "Instance not found"}
    
    del rapp["rappInstances"][instance_id]
    return {"message": "Instance deleted successfully"}

@mcp.tool()
def deploy_rapp_instance(rapp_id: str, instance_id: str, deploy_order: str) -> dict:
    """Deploy or undeploy instance"""
    if rapp_id not in rapps_db:
        return {"error": "rApp not found"}
    
    rapp = rapps_db[rapp_id]
    if instance_id not in rapp["rappInstances"]:
        return {"error": "Instance not found"}
    
    instance = rapp["rappInstances"][instance_id]
    if deploy_order == "DEPLOY":
        instance["state"] = "DEPLOYED"
        instance["reason"] = "Instance deployed successfully"
    else:
        instance["state"] = "UNDEPLOYED"
        instance["reason"] = "Instance undeployed successfully"
    
    return {"message": f"Instance {deploy_order.lower()} operation accepted"}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
