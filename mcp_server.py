from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Optional
import uuid
import base64
from datetime import datetime

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# In-memory storage simulating INF platform
ocloud_db = {
    "oCloudId": "f078a1d3-56df-46c2-88a2-dd659aa3f6bd",
    "globalCloudId": "10a07219-4201-4b3e-a52d-81ab6a755d8a",
    "name": "INF O-Cloud Platform",
    "description": "O-RAN Infrastructure O-Cloud instance",
    "serviceUri": "https://128.224.115.51:30205"
}

resource_pools_db: Dict[str, dict] = {
    "f078a1d3-56df-46c2-88a2-dd659aa3f6bd": {
        "resourcePoolId": "f078a1d3-56df-46c2-88a2-dd659aa3f6bd",
        "name": "RegionOne",
        "description": "INF Platform Resource Pool",
        "oCloudId": "f078a1d3-56df-46c2-88a2-dd659aa3f6bd",
        "location": "Edge Site 1"
    }
}

deployment_managers_db: Dict[str, dict] = {
    "c765516a-a84e-30c9-b954-9c3031bf71c8": {
        "deploymentManagerId": "c765516a-a84e-30c9-b954-9c3031bf71c8",
        "name": "kubernetes-cluster",
        "description": "INF Kubernetes DMS",
        "oCloudId": "f078a1d3-56df-46c2-88a2-dd659aa3f6bd",
        "serviceUri": "https://128.224.115.51:6443",
        "profileSupportList": ["native_k8sapi"],
        "capabilities": {"OS": "low_latency"},
        "capacity": {"cpu": "32", "hugepages-2Mi": "2048", "hugepages-1Gi": "2048"}
    }
}

resource_types_db: Dict[str, dict] = {
    "60cba7be-e2cd-3b8c-a7ff-16e0f10573f9": {
        "resourceTypeId": "60cba7be-e2cd-3b8c-a7ff-16e0f10573f9",
        "name": "pserver",
        "description": "Physical Server resource type",
        "vendor": "Dell",
        "model": "PowerEdge R740"
    },
    "a45983bb-199a-30ec-b7a1-eab2455f333c": {
        "resourceTypeId": "a45983bb-199a-30ec-b7a1-eab2455f333c",
        "name": "cpu",
        "description": "CPU resource type",
        "vendor": "Intel",
        "model": "Xeon E5-2670 v2"
    }
}

resources_db: Dict[str, dict] = {
    "5b3a2da8-17da-466c-b5f7-972590c7baf2": {
        "resourceId": "5b3a2da8-17da-466c-b5f7-972590c7baf2",
        "resourceTypeId": "60cba7be-e2cd-3b8c-a7ff-16e0f10573f9",
        "resourcePoolId": "f078a1d3-56df-46c2-88a2-dd659aa3f6bd",
        "description": "controller-0;hostname:controller-0;personality:controller;administrative:unlocked;operational:enabled"
    }
}

subscriptions_db: Dict[str, dict] = {}
alarm_subscriptions_db: Dict[str, dict] = {}
alarms_db: Dict[str, dict] = {}

@mcp.tool()
def get_inventory_api_versions() -> dict:
    """Get O2 IMS inventory API versions"""
    return {
        "uriPrefix": "https://128.224.115.36:30205/o2ims-infrastructureInventory",
        "apiVersions": [{"version": "1.0.0"}]
    }

@mcp.tool()
def get_monitoring_api_versions() -> dict:
    """Get O2 IMS monitoring API versions"""
    return {
        "uriPrefix": "https://128.224.115.36:30205/o2ims-infrastructureMonitoring",
        "apiVersions": [{"version": "1.0.0"}]
    }

@mcp.tool()
def get_ocloud_info(fields: str = None, exclude_fields: str = None) -> dict:
    """Get O-Cloud information with field filtering support"""
    return ocloud_db

@mcp.tool()
def get_deployment_managers(filter_criteria: str = None, fields: str = None) -> List[dict]:
    """Get deployment manager list from INF platform"""
    return list(deployment_managers_db.values())

@mcp.tool()
def get_deployment_manager(deployment_manager_id: str, profile: str = None) -> dict:
    """Get deployment manager with optional Kubernetes profile"""
    if deployment_manager_id not in deployment_managers_db:
        return {"error": "Deployment manager not found"}
    
    dm = deployment_managers_db[deployment_manager_id].copy()
    
    if profile == "native_k8sapi":
        dm["extensions"] = {
            "profileName": "native_k8sapi",
            "profileData": {
                "cluster_api_endpoint": "https://128.224.115.51:6443",
                "cluster_ca_cert": base64.b64encode(b"mock-ca-cert-data").decode(),
                "admin_user": "kubernetes-admin",
                "admin_client_cert": base64.b64encode(b"mock-client-cert-data").decode(),
                "admin_client_key": base64.b64encode(b"mock-client-key-data").decode(),
                "helmcli_host_with_port": "128.224.115.34:30022",
                "helmcli_username": "helm",
                "helmcli_password": "password",
                "helmcli_kubeconfig": "/share/kubeconfig_c765516a.config"
            }
        }
    
    return dm

@mcp.tool()
def get_resource_pools(filter_criteria: str = None) -> List[dict]:
    """Get resource pools from INF platform"""
    return list(resource_pools_db.values())

@mcp.tool()
def get_resource_pool(resource_pool_id: str) -> dict:
    """Get specific resource pool"""
    if resource_pool_id not in resource_pools_db:
        return {"error": "Resource pool not found"}
    return resource_pools_db[resource_pool_id]

@mcp.tool()
def get_resources(resource_pool_id: str, filter_criteria: str = None) -> List[dict]:
    """Get resources in a resource pool"""
    if resource_pool_id not in resource_pools_db:
        return []
    return [r for r in resources_db.values() if r["resourcePoolId"] == resource_pool_id]

@mcp.tool()
def get_resource(resource_pool_id: str, resource_id: str) -> dict:
    """Get specific resource with hierarchical elements"""
    if resource_id not in resources_db:
        return {"error": "Resource not found"}
    
    resource = resources_db[resource_id].copy()
    if resource["resourcePoolId"] != resource_pool_id:
        return {"error": "Resource not found in specified pool"}
    
    # Add mock hierarchical elements for pserver
    if resource["resourceTypeId"] == "60cba7be-e2cd-3b8c-a7ff-16e0f10573f9":
        resource["elements"] = [{
            "resourceId": "eee8b101-6b7f-4f0a-b54b-89adc0f3f906",
            "resourceTypeId": "a45983bb-199a-30ec-b7a1-eab2455f333c",
            "resourcePoolId": resource_pool_id,
            "parentId": resource_id,
            "description": "cpu:0;core:0;thread:0;cpu_family:6;allocated_function:Platform"
        }]
    
    return resource

@mcp.tool()
def get_resource_types(filter_criteria: str = None) -> List[dict]:
    """Get resource types available in INF platform"""
    return list(resource_types_db.values())

@mcp.tool()
def get_resource_type(resource_type_id: str) -> dict:
    """Get specific resource type with alarm dictionary"""
    if resource_type_id not in resource_types_db:
        return {"error": "Resource type not found"}
    
    resource_type = resource_types_db[resource_type_id].copy()
    
    # Add alarm dictionary for pserver type
    if resource_type_id == "60cba7be-e2cd-3b8c-a7ff-16e0f10573f9":
        resource_type["alarmDictionary"] = {
            "id": "7e1e59c3-c99e-3d1c-9934-21548a3a699a",
            "alarmDictionaryVersion": "0.1",
            "entityType": "pserver",
            "vendor": "Dell",
            "managementInterfaceId": "O2IMS"
        }
    
    return resource_type

@mcp.tool()
def create_subscription(callback: str, consumer_subscription_id: str = None, filter_criteria: str = "") -> dict:
    """Create inventory subscription for SMO notifications"""
    subscription_id = str(uuid.uuid4())
    subscription = {
        "subscriptionId": subscription_id,
        "callback": callback,
        "consumerSubscriptionId": consumer_subscription_id or str(uuid.uuid4()),
        "filter": filter_criteria
    }
    subscriptions_db[subscription_id] = subscription
    return subscription

@mcp.tool()
def get_subscriptions() -> List[dict]:
    """Get all inventory subscriptions"""
    return list(subscriptions_db.values())

@mcp.tool()
def get_subscription(subscription_id: str) -> dict:
    """Get specific subscription"""
    if subscription_id not in subscriptions_db:
        return {"error": "Subscription not found"}
    return subscriptions_db[subscription_id]

@mcp.tool()
def delete_subscription(subscription_id: str) -> dict:
    """Delete inventory subscription"""
    if subscription_id not in subscriptions_db:
        return {"error": "Subscription not found"}
    del subscriptions_db[subscription_id]
    return {"message": "Subscription deleted"}

@mcp.tool()
def create_alarm_subscription(callback: str, consumer_subscription_id: str = None, filter_criteria: str = "") -> dict:
    """Create alarm subscription for SMO alarm notifications"""
    alarm_subscription_id = str(uuid.uuid4())
    subscription = {
        "alarmSubscriptionId": alarm_subscription_id,
        "callback": callback,
        "consumerSubscriptionId": consumer_subscription_id or str(uuid.uuid4()),
        "filter": filter_criteria
    }
    alarm_subscriptions_db[alarm_subscription_id] = subscription
    return subscription

@mcp.tool()
def get_alarm_subscriptions() -> List[dict]:
    """Get all alarm subscriptions"""
    return list(alarm_subscriptions_db.values())

@mcp.tool()
def get_alarm_subscription(alarm_subscription_id: str) -> dict:
    """Get specific alarm subscription"""
    if alarm_subscription_id not in alarm_subscriptions_db:
        return {"error": "Alarm subscription not found"}
    return alarm_subscriptions_db[alarm_subscription_id]

@mcp.tool()
def delete_alarm_subscription(alarm_subscription_id: str) -> dict:
    """Delete alarm subscription"""
    if alarm_subscription_id not in alarm_subscriptions_db:
        return {"error": "Alarm subscription not found"}
    del alarm_subscriptions_db[alarm_subscription_id]
    return {"message": "Alarm subscription deleted"}

@mcp.tool()
def get_alarms(filter_criteria: str = None) -> List[dict]:
    """Get alarm event records from INF platform"""
    return list(alarms_db.values())

@mcp.tool()
def get_alarm(alarm_event_record_id: str) -> dict:
    """Get specific alarm event record"""
    if alarm_event_record_id not in alarms_db:
        return {"error": "Alarm event record not found"}
    return alarms_db[alarm_event_record_id]

@mcp.tool()
def patch_alarm(alarm_event_record_id: str, alarm_acknowledged: bool = None, perceived_severity: str = None) -> dict:
    """Patch alarm event record (acknowledge or clear)"""
    if alarm_event_record_id not in alarms_db:
        return {"error": "Alarm event record not found"}
    
    alarm = alarms_db[alarm_event_record_id]
    if alarm_acknowledged is not None:
        alarm["alarmAcknowledged"] = alarm_acknowledged
        alarm["alarmAcknowledgeTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if perceived_severity == "5":  # CLEARED
        alarm["perceivedSeverity"] = "5"
        alarm["alarmChangedTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return {"message": "Alarm updated successfully"}

@mcp.tool()
def create_test_alarm(resource_id: str = "5b3a2da8-17da-466c-b5f7-972590c7baf2", severity: str = "1") -> dict:
    """Create test alarm for INF platform resource"""
    alarm_id = str(uuid.uuid4())
    alarm = {
        "alarmEventRecordId": alarm_id,
        "resourceTypeId": "60cba7be-e2cd-3b8c-a7ff-16e0f10573f9",
        "resourceId": resource_id,
        "alarmDefinitionId": "1197f463-b3d4-3aa3-9c14-faa493baa069",
        "probableCauseId": "f52054c9-6f3c-39a0-aab8-e00e01d8c4d3",
        "alarmRaisedTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "alarmAcknowledged": False,
        "perceivedSeverity": severity  # 0=CRITICAL, 1=MAJOR, 2=MINOR, 3=WARNING, 4=INDETERMINATE, 5=CLEARED
    }
    alarms_db[alarm_id] = alarm
    return {"alarmEventRecordId": alarm_id, "message": "Test alarm created for INF platform"}

@mcp.tool()
def simulate_smo_registration(smo_register_url: str, ocloud_global_id: str) -> dict:
    """Simulate O2 service registration with SMO"""
    return {
        "message": f"O2 service registered with SMO at {smo_register_url}",
        "oCloudGlobalId": ocloud_global_id,
        "registrationTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
