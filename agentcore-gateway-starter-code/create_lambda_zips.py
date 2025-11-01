#!/usr/bin/env python3
import os
import zipfile
import json
import ast

def extract_tool_functions():
    """Extract all @tool decorated functions from smo_planner_extended.py"""
    with open('smo_planner_extended.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the AST to find @tool decorated functions
    tree = ast.parse(content)
    
    tool_functions = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if function has @tool decorator
            for decorator in node.decorator_list:
                if (isinstance(decorator, ast.Name) and decorator.id == 'tool') or \
                   (isinstance(decorator, ast.Attribute) and decorator.attr == 'tool'):
                    # Extract function source
                    func_start = node.lineno - 1
                    func_end = node.end_lineno if hasattr(node, 'end_lineno') else func_start + 20
                    
                    lines = content.split('\n')
                    
                    # Find actual start (including decorator)
                    actual_start = func_start
                    while actual_start > 0 and (lines[actual_start - 1].strip().startswith('@') or 
                                               lines[actual_start - 1].strip() == ''):
                        actual_start -= 1
                    
                    # Find actual end (next function or end of file)
                    actual_end = func_end
                    for i in range(func_end, len(lines)):
                        if lines[i].startswith('@tool') or lines[i].startswith('def ') or \
                           lines[i].startswith('class ') or lines[i].startswith('if __name__'):
                            actual_end = i
                            break
                    
                    func_source = '\n'.join(lines[actual_start:actual_end])
                    tool_functions[node.name] = func_source.strip()
    
    return tool_functions

def create_lambda_handler(tool_name, tool_source):
    """Generate complete Lambda handler with actual tool function"""
    # Remove @tool decorator and add necessary imports
    clean_source = tool_source.replace('@tool\n', '').replace('@tool ', '')
    
    return f'''import json
import uuid
from typing import Dict, List, Any, Optional

# Global storage (in production, use DynamoDB/RDS)
active_plans = {{}}
slice_registry = {{}}
optimization_jobs = {{}}
handover_policies = {{}}
energy_profiles = {{}}
interference_maps = {{}}

# Helper functions that tools depend on
def deploy_a1_policy(policy_type: str, s_nssai: str, policy_params: Dict[str, Any]):
    policy_id = f"policy-{{uuid.uuid4().hex[:8]}}"
    print(f"A1: Deployed policy {{policy_id}} for slice {{s_nssai}}")
    return {{"policyId": policy_id, "status": "DEPLOYED"}}

def configure_e2_subscription(node_id: str, metrics: List[str], reporting_period: int):
    sub_id = f"e2sub-{{uuid.uuid4().hex[:8]}}"
    print(f"E2: Configured subscription {{sub_id}} for node {{node_id}}")
    return {{"subscriptionId": sub_id, "status": "ACTIVE"}}

def configure_slice_parameters(node_id: str, s_nssai: str, slice_config: Dict[str, Any]):
    config_id = f"o1cfg-{{uuid.uuid4().hex[:8]}}"
    print(f"O1: Applied slice config {{config_id}} to node {{node_id}}")
    return {{"configId": config_id, "status": "APPLIED"}}

def instantiate_vnf(vnf_type: str, flavor: str, slice_id: str):
    vnf_id = f"vnf-{{uuid.uuid4().hex[:8]}}"
    print(f"O2: Instantiated VNF {{vnf_id}} of type {{vnf_type}}")
    return {{"vnfId": vnf_id, "status": "INSTANTIATED"}}

# Main tool function
{clean_source}

def lambda_handler(event, context):
    """AWS Lambda entry point"""
    try:
        # Extract parameters from event body
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        # Get function parameters
        params = body.get('params', {{}})
        
        # Call the tool function with unpacked parameters
        result = {tool_name}(**params)
        
        return {{
            'statusCode': 200,
            'headers': {{
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }},
            'body': json.dumps(result, default=str)
        }}
    except Exception as e:
        print(f"Error in {tool_name}: {{str(e)}}")
        return {{
            'statusCode': 500,
            'headers': {{
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }},
            'body': json.dumps({{'error': str(e), 'tool': '{tool_name}'}})
        }}
'''

def create_zip_for_tool(tool_name, tool_source):
    """Create deployment zip for a single tool"""
    zip_dir = f"lambda_zips/{tool_name}"
    os.makedirs(zip_dir, exist_ok=True)
    
    # Create lambda_function.py with actual tool code
    handler_code = create_lambda_handler(tool_name, tool_source)
    with open(f"{zip_dir}/lambda_function.py", "w", encoding='utf-8') as f:
        f.write(handler_code)
    
    # Create deployment zip
    zip_path = f"lambda_zips/{tool_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(f"{zip_dir}/lambda_function.py", "lambda_function.py")
    
    print(f"Created {zip_path}")
    return zip_path

def main():
    """Create Lambda deployment zips for all tools"""
    print("Extracting tool functions from smo_planner_extended.py...")
    
    try:
        tool_functions = extract_tool_functions()
        print(f"Found {len(tool_functions)} tool functions")
        
        os.makedirs("lambda_zips", exist_ok=True)
        
        created_zips = []
        for tool_name, tool_source in tool_functions.items():
            print(f"Processing {tool_name}...")
            zip_path = create_zip_for_tool(tool_name, tool_source)
            created_zips.append(zip_path)
        
        print(f"\nSuccessfully created {len(created_zips)} Lambda deployment packages:")
        for zip_path in created_zips:
            print(f"  ✓ {zip_path}")
        
    except FileNotFoundError:
        print("Error: smo_planner_extended.py not found in current directory")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
