# proxmox_mcp.py
import asyncio
import json
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import time

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from proxmoxer import ProxmoxAPI

load_dotenv()

# --- Configuration ---
PROXMOX_HOST = os.getenv("PROXMOX_HOST")
PROXMOX_USER = os.getenv("PROXMOX_USER")
PROXMOX_PASSWORD = os.getenv("PROXMOX_PASSWORD")
PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "true").lower() not in ('false', '0', 'f')

# Basic validation
if not all([PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASSWORD]):
    print("Error: Please set PROXMOX_HOST, PROXMOX_USER, and PROXMOX_PASSWORD environment variables.")
    print("You can create a .env file based on .env.example")
    exit(1)

# --- Proxmox Context ---
@dataclass
class ProxmoxContext:
    """Context holding the ProxmoxAPI client."""
    proxmox_client: ProxmoxAPI

@asynccontextmanager
async def proxmox_lifespan(server: FastMCP) -> AsyncIterator[ProxmoxContext]:
    """Manages the ProxmoxAPI client lifecycle."""
    print(f"Connecting to Proxmox at {PROXMOX_HOST}...")
    proxmox_client = None
    try:
        proxmox_client = ProxmoxAPI(
            PROXMOX_HOST,
            user=PROXMOX_USER,
            password=PROXMOX_PASSWORD,
            verify_ssl=PROXMOX_VERIFY_SSL
        )
        # Test connection (optional but recommended)
        proxmox_client.version.get()
        print("Successfully connected to Proxmox.")
        
        # Create the context with a valid connection
        yield ProxmoxContext(proxmox_client=proxmox_client)
    except Exception as e:
        print(f"Error connecting to Proxmox: {e}")
        # Yield a context with None to indicate failure
        yield ProxmoxContext(proxmox_client=None)
    finally:
        # No explicit cleanup needed for Proxmoxer client in this simple case
        print("Proxmox client context closing.")
        pass

# --- MCP Server Setup ---
mcp = FastMCP(
    "mcp-proxmox",
    description="MCP server for interacting with a Proxmox VE cluster.",
    lifespan=proxmox_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8051"))
)

# --- Tools ---
@mcp.tool()
async def get_nodes(ctx: Context) -> str:
    """Lists all nodes in the Proxmox cluster.

    Retrieves information about each node, such as its name, status, CPU usage,
    memory usage, and disk space.

    Args:
        ctx: The MCP server provided context.

    Returns:
        A JSON formatted string containing a list of nodes and their details.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        nodes = proxmox_client.nodes.get()
        return json.dumps(nodes, indent=2)
    except Exception as e:
        return f"Error retrieving nodes from Proxmox: {str(e)}"

def get_online_nodes(proxmox_client: ProxmoxAPI):
    """Gets a list of online nodes from the Proxmox cluster.
    
    Args:
        proxmox_client: The ProxmoxAPI client instance.
        
    Returns:
        A list of node dictionaries that are online.
        Returns an empty list if the API call fails or no online nodes are found.
    """
    try:
        if proxmox_client is None:
            print("Warning: Proxmox client is not initialized.")
            return []
            
        # Get all nodes in one API call
        nodes = proxmox_client.nodes.get()
        
        if not nodes:
            print("Warning: No nodes returned from Proxmox API.")
            return []
        
        # Filter to only include online nodes
        online_nodes = [node for node in nodes if node['status'] != 'offline']
        
        if not online_nodes:
            print("Warning: No online nodes found in the cluster.")
        
        return online_nodes
    except Exception as e:
        print(f"Error retrieving online nodes: {str(e)}")
        return []

@mcp.tool()
async def get_node_status(ctx: Context, node_name: str) -> str:
    """Retrieves detailed status information for a specific node in the Proxmox cluster.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node to get status for.

    Returns:
        A JSON formatted string containing detailed status information for the specified node.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get node status (includes CPU, memory, disk info)
        status = proxmox_client.nodes(node_name).status.get()
        
        # Get node network information
        network = proxmox_client.nodes(node_name).network.get()
        
        # Get QEMU VMs (if available)
        try:
            qemu = proxmox_client.nodes(node_name).qemu.get()
        except Exception as e:
            qemu = f"QEMU info not available: {str(e)}"
        
        # Get LXC containers (if available)
        try:
            lxc = proxmox_client.nodes(node_name).lxc.get()
        except Exception as e:
            lxc = f"LXC info not available: {str(e)}"
        
        # Get storage information
        try:
            storage = proxmox_client.nodes(node_name).storage.get()
        except Exception as e:
            storage = f"Storage info not available: {str(e)}"
        
        # Combine all information
        node_info = {
            "node_name": node_name,
            "status": status,
            "network": network,
            "qemu": qemu,
            "lxc": lxc,
            "storage": storage
        }
        
        return json.dumps(node_info, indent=2)
    except Exception as e:
        return f"Error retrieving status for node '{node_name}': {str(e)}"

@mcp.tool()
async def get_lxc_containers(ctx: Context, node_name: str) -> str:
    """Retrieves information about LXC containers on a specific node.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node to get LXC container information for.

    Returns:
        A JSON formatted string containing LXC container information for the specified node.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get LXC containers
        lxc_containers = proxmox_client.nodes(node_name).lxc.get()
        
        return json.dumps(lxc_containers, indent=2)
    except Exception as e:
        return f"Error retrieving LXC containers for node '{node_name}': {str(e)}"

@mcp.tool()
async def get_lxc_container_info(ctx: Context, node_name: str, vmid: int) -> str:
    """Retrieves detailed information about a specific LXC container.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the LXC container.
        vmid: The VM ID of the LXC container.

    Returns:
        A JSON formatted string containing detailed information about the specified LXC container.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get LXC container configuration
        config = proxmox_client.nodes(node_name).lxc(vmid).config.get()
        
        # Get LXC container status
        status = proxmox_client.nodes(node_name).lxc(vmid).status.current.get()
        
        # Combine information
        container_info = {
            "node_name": node_name,
            "vmid": vmid,
            "config": config,
            "status": status
        }
        
        return json.dumps(container_info, indent=2)
    except Exception as e:
        return f"Error retrieving information for LXC container {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def manage_lxc_container(ctx: Context, node_name: str, vmid: int, action: str) -> str:
    """Manages an LXC container by performing actions like start, stop, or reboot.

    This tool allows you to control the lifecycle of an LXC container by performing
    various actions such as starting, stopping, rebooting, shutting down, suspending,
    or resuming the container.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the LXC container.
        vmid: The VM ID of the LXC container.
        action: The action to perform on the container. Valid values are:
                'start' - Start the container
                'stop' - Stop the container immediately
                'reboot' - Reboot the container (shutdown and start)
                'shutdown' - Gracefully shut down the container
                'suspend' - EXPERIMENTAL: Suspend the container (use with caution)
                'resume' - EXPERIMENTAL: Resume a suspended container

    Returns:
        A string indicating the result of the action.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Validate action
        valid_actions = ['start', 'stop', 'reboot', 'shutdown', 'suspend', 'resume']
        if action not in valid_actions:
            return f"Invalid action '{action}'. Valid actions are: {', '.join(valid_actions)}"
        
        # Perform the action
        if action == 'start':
            proxmox_client.nodes(node_name).lxc(vmid).status.start.post()
        elif action == 'stop':
            proxmox_client.nodes(node_name).lxc(vmid).status.stop.post()
        elif action == 'reboot':
            proxmox_client.nodes(node_name).lxc(vmid).status.reboot.post()
        elif action == 'shutdown':
            proxmox_client.nodes(node_name).lxc(vmid).status.shutdown.post()
        elif action == 'suspend':
            print("WARNING: The 'suspend' action is experimental and may cause issues with some containers.")
            proxmox_client.nodes(node_name).lxc(vmid).status.suspend.post()
        elif action == 'resume':
            print("WARNING: The 'resume' action is experimental and may cause issues with some containers.")
            proxmox_client.nodes(node_name).lxc(vmid).status.resume.post()
        
        return f"Successfully performed '{action}' action on LXC container {vmid} on node '{node_name}'."
    except Exception as e:
        return f"Error performing '{action}' action on LXC container {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def manage_vm(ctx: Context, node_name: str, vmid: int, action: str) -> str:
    """Manages a virtual machine by performing actions like start, stop, or reboot.

    This tool allows you to control the lifecycle of a VM by performing
    various actions such as starting, stopping, rebooting, shutting down, resetting,
    suspending, or resuming the VM.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.
        action: The action to perform on the VM. Valid values are:
                'start' - Start the VM
                'stop' - Stop the VM immediately
                'reboot' - Reboot the VM (shutdown and start)
                'shutdown' - Gracefully shut down the VM
                'reset' - Perform a hard reset on the VM (equivalent to pressing the reset button)
                'suspend' - Suspend the VM to RAM
                'resume' - Resume a previously suspended VM

    Returns:
        A string indicating the result of the action.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Validate action
        valid_actions = ['start', 'stop', 'reboot', 'shutdown', 'reset', 'suspend', 'resume']
        if action not in valid_actions:
            return f"Invalid action '{action}'. Valid actions are: {', '.join(valid_actions)}"
        
        # Perform the action
        if action == 'start':
            proxmox_client.nodes(node_name).qemu(vmid).status.start.post()
        elif action == 'stop':
            proxmox_client.nodes(node_name).qemu(vmid).status.stop.post()
        elif action == 'reboot':
            proxmox_client.nodes(node_name).qemu(vmid).status.reboot.post()
        elif action == 'shutdown':
            proxmox_client.nodes(node_name).qemu(vmid).status.shutdown.post()
        elif action == 'reset':
            proxmox_client.nodes(node_name).qemu(vmid).status.reset.post()
        elif action == 'suspend':
            proxmox_client.nodes(node_name).qemu(vmid).status.suspend.post()
        elif action == 'resume':
            proxmox_client.nodes(node_name).qemu(vmid).status.resume.post()
        
        return f"Successfully performed '{action}' action on VM {vmid} on node '{node_name}'."
    except Exception as e:
        return f"Error performing '{action}' action on VM {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def get_cluster_log(ctx: Context, limit: int = 50, since: str = None) -> str:
    """Retrieve recent cluster-wide log entries.

    Args:
        ctx: The MCP server provided context.
        limit: Maximum number of log entries to return (default: 50).
        since: Optional timestamp to filter logs from a specific time.

    Returns:
        A JSON formatted string containing cluster log entries.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        # Get all logs and then limit them in Python
        logs = proxmox_client.cluster.log.get()
        if since:
            # Filter logs by timestamp if provided
            logs = [log for log in logs if log['time'] >= since]
        # Limit the number of logs returned
        logs = logs[:limit]
        return json.dumps(logs, indent=2)
    except Exception as e:
        return f"Error retrieving cluster logs: {str(e)}"

@mcp.tool()
async def get_cluster_tasks(ctx: Context) -> str:
    """List recent or currently running cluster-wide tasks.

    Args:
        ctx: The MCP server provided context.

    Returns:
        A JSON formatted string containing cluster tasks.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        tasks = proxmox_client.cluster.tasks.get()
        return json.dumps(tasks, indent=2)
    except Exception as e:
        return f"Error retrieving cluster tasks: {str(e)}"

@mcp.tool()
async def get_task_status(ctx: Context, node: str, upid: str) -> str:
    """Get the current status of a specific task.

    Args:
        ctx: The MCP server provided context.
        node: The node where the task is running.
        upid: The Unique Process ID of the task.

    Returns:
        A JSON formatted string containing task status.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        status = proxmox_client.nodes(node).tasks(upid).status.get()
        return json.dumps(status, indent=2)
    except Exception as e:
        return f"Error retrieving task status: {str(e)}"

@mcp.tool()
async def get_task_log(ctx: Context, node: str, upid: str) -> str:
    """Retrieve the full log output for a specific task.

    Args:
        ctx: The MCP server provided context.
        node: The node where the task is running.
        upid: The Unique Process ID of the task.

    Returns:
        A JSON formatted string containing task log.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        log = proxmox_client.nodes(node).tasks(upid).log.get()
        return json.dumps(log, indent=2)
    except Exception as e:
        return f"Error retrieving task log: {str(e)}"

@mcp.tool()
async def get_cluster_ha_status(ctx: Context) -> str:
    """Get High Availability status information.

    Args:
        ctx: The MCP server provided context.

    Returns:
        A JSON formatted string containing HA status information.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        ha_status = proxmox_client.cluster.ha.status.get()
        return json.dumps(ha_status, indent=2)
    except Exception as e:
        return f"Error retrieving HA status: {str(e)}"

@mcp.tool()
async def get_cluster_firewall_rules(ctx: Context) -> str:
    """Retrieve firewall rules configured at the datacenter level.

    Args:
        ctx: The MCP server provided context.

    Returns:
        A JSON formatted string containing cluster firewall rules.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        rules = proxmox_client.cluster.firewall.rules.get()
        return json.dumps(rules, indent=2)
    except Exception as e:
        return f"Error retrieving cluster firewall rules: {str(e)}"

@mcp.tool()
async def get_node_firewall_rules(ctx: Context, node: str) -> str:
    """Retrieve firewall rules configured at the node level.

    Args:
        ctx: The MCP server provided context.
        node: The node to get firewall rules for.

    Returns:
        A JSON formatted string containing node firewall rules.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        rules = proxmox_client.nodes(node).firewall.rules.get()
        return json.dumps(rules, indent=2)
    except Exception as e:
        return f"Error retrieving node firewall rules: {str(e)}"

@mcp.tool()
async def get_vm_firewall_rules(ctx: Context, node: str, vmid: int) -> str:
    """Retrieve firewall rules configured for a specific VM.

    Args:
        ctx: The MCP server provided context.
        node: The node hosting the VM.
        vmid: The ID of the VM.

    Returns:
        A JSON formatted string containing VM firewall rules.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # First determine if this is a VM or LXC
        try:
            # Try to get VM info first
            vm_info = proxmox_client.nodes(node).qemu(vmid).status.current.get()
            rules = proxmox_client.nodes(node).qemu(vmid).firewall.rules.get()
        except Exception:
            try:
                # If not a VM, try to get LXC info
                lxc_info = proxmox_client.nodes(node).lxc(vmid).status.current.get()
                rules = proxmox_client.nodes(node).lxc(vmid).firewall.rules.get()
            except Exception:
                return f"Could not find VM or LXC with ID {vmid} on node {node}"
        
        return json.dumps(rules, indent=2)
    except Exception as e:
        return f"Error retrieving VM firewall rules: {str(e)}"

@mcp.tool()
async def get_lxc_firewall_rules(ctx: Context, node: str, vmid: int) -> str:
    """Retrieve firewall rules configured for a specific LXC container.

    Args:
        ctx: The MCP server provided context.
        node: The node hosting the LXC container.
        vmid: The ID of the LXC container.

    Returns:
        A JSON formatted string containing LXC firewall rules.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        rules = proxmox_client.nodes(node).lxc(vmid).firewall.rules.get()
        return json.dumps(rules, indent=2)
    except Exception as e:
        return f"Error retrieving LXC firewall rules: {str(e)}"

@mcp.tool()
async def get_storage_list(ctx: Context, node: str = 'local') -> str:
    """Get a list of all available storage locations on a node.

    Args:
        ctx: The MCP server provided context.
        node: The node to get storage information from (default: 'local').

    Returns:
        A JSON formatted string containing storage information.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        storage_list = proxmox_client.nodes(node).storage.get()
        return json.dumps(storage_list, indent=2)
    except Exception as e:
        return f"Error retrieving storage list: {str(e)}"

@mcp.tool()
async def get_storage_content(ctx: Context, node: str, storage_id: str) -> str:
    """Get the content of a specific storage location.

    Args:
        ctx: The MCP server provided context.
        node: The node where the storage is located.
        storage_id: The ID of the storage to check.

    Returns:
        A JSON formatted string containing storage content.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        content = proxmox_client.nodes(node).storage(storage_id).content.get()
        return json.dumps(content, indent=2)
    except Exception as e:
        return f"Error retrieving storage content: {str(e)}"

@mcp.tool()
async def get_backup_storage_locations(ctx: Context, node: str = 'local') -> str:
    """Get a list of storage locations that can be used for backups.

    Args:
        ctx: The MCP server provided context.
        node: The node to check for backup-capable storage (default: 'local').

    Returns:
        A JSON formatted string containing backup-capable storage locations.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        storage_list = proxmox_client.nodes(node).storage.get()
        
        # Filter for backup-capable storage types
        backup_storage = [
            storage for storage in storage_list 
            if storage.get('type') in ['dir', 'nfs', 'cifs', 'pbs']
        ]
        
        return json.dumps(backup_storage, indent=2)
    except Exception as e:
        return f"Error retrieving backup storage locations: {str(e)}"

@mcp.tool()
async def list_backups(ctx: Context, node: str = 'local', storage_id: str = None, vmid: int = None) -> str:
    """List available backups, optionally filtered by storage location or VM/LXC ID.

    Args:
        ctx: The MCP server provided context.
        node: The node to check for backups (default: 'local').
        storage_id: Optional storage ID to filter backups by location.
        vmid: Optional VM/LXC ID to filter backups by.

    Returns:
        A JSON formatted string containing backup information.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # First, get all backup-capable storage locations
        backup_storage = json.loads(await get_backup_storage_locations(ctx, node))
        if not backup_storage:
            return "No backup-capable storage locations found."
        
        # Get all storage content
        if storage_id:
            # Validate the specified storage
            if not any(storage['storage'] == storage_id for storage in backup_storage):
                return f"Storage '{storage_id}' is not a valid backup storage location."
            
            # Get content from specific storage
            content = json.loads(await get_storage_content(ctx, node, storage_id))
        else:
            # Get content from all backup-capable storages
            content = []
            for storage in backup_storage:
                try:
                    storage_content = json.loads(await get_storage_content(ctx, node, storage['storage']))
                    content.extend(storage_content)
                except Exception as e:
                    print(f"Warning: Could not access storage {storage['storage']}: {str(e)}")
        
        # Filter for backup files
        backups = [item for item in content if item.get('format') == 'vma' or item.get('format') == 'lxc']
        
        # Filter by VMID if specified
        if vmid is not None:
            backups = [backup for backup in backups if backup.get('vmid') == str(vmid)]
        
        return json.dumps(backups, indent=2)
    except Exception as e:
        return f"Error listing backups: {str(e)}"

@mcp.tool()
async def create_backup(ctx: Context, node: str, vmid: int, storage_id: str, mode: str = 'snapshot', 
                       compress: str = 'lzo', remove: bool = False) -> str:
    """Create a backup of a VM or LXC container.

    Args:
        ctx: The MCP server provided context.
        node: The node where the VM/LXC is located.
        vmid: The ID of the VM/LXC to backup.
        storage_id: The storage ID where the backup should be stored.
        mode: Backup mode ('snapshot', 'suspend', or 'stop').
        compress: Compression type ('lzo', 'gzip', or 'zstd').
        remove: Whether to remove old backups after successful backup.

    Returns:
        A string containing the task ID of the backup operation.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Check if we have a valid connection
        if proxmox_client is None:
            return "Error: Not connected to Proxmox server. Please check your connection settings."
        
        # Validate parameters
        valid_modes = ['snapshot', 'suspend', 'stop']
        if mode not in valid_modes:
            return f"Invalid mode '{mode}'. Valid modes are: {', '.join(valid_modes)}"
        
        valid_compress = ['lzo', 'gzip', 'zstd']
        if compress not in valid_compress:
            return f"Invalid compression type '{compress}'. Valid types are: {', '.join(valid_compress)}"
        
        # First determine if this is a VM or LXC
        try:
            # Try to get VM info first
            vm_info = proxmox_client.nodes(node).qemu(vmid).status.current.get()
            vm_type = 'qemu'
        except Exception:
            try:
                # If not a VM, try to get LXC info
                lxc_info = proxmox_client.nodes(node).lxc(vmid).status.current.get()
                vm_type = 'lxc'
            except Exception:
                return f"Could not find VM or LXC with ID {vmid} on node {node}"
        
        # Prepare backup parameters
        params = {
            'mode': mode,
            'compress': compress,
            'remove': 1 if remove else 0,
            'storage': storage_id,
            'vmid': str(vmid)  # Convert to string as required by the API
        }
        
        # Start backup task using the vzdump endpoint
        try:
            task = proxmox_client.nodes(node).vzdump.post(**params)
            # The task response is a string containing the UPID
            upid = task
            return f"Backup task started for {vm_type} {vmid}. UPID: {upid}"
        except Exception as e:
            return f"Error starting backup task: {str(e)}"
            
    except Exception as e:
        return f"Error creating backup: {str(e)}"

@mcp.tool()
async def get_backup_status(ctx: Context, node: str, upid: str) -> str:
    """Get the status of a backup task.

    Args:
        ctx: The MCP server provided context.
        node: The node where the backup task is running.
        upid: The Unique Process ID of the backup task.

    Returns:
        A JSON formatted string containing backup task status.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get task status
        status = proxmox_client.nodes(node).tasks(upid).status.get()
        
        # Get task log
        log = proxmox_client.nodes(node).tasks(upid).log.get()
        
        # Combine status and log
        backup_status = {
            "status": status,
            "log": log
        }
        
        return json.dumps(backup_status, indent=2)
    except Exception as e:
        return f"Error getting backup status: {str(e)}"

@mcp.tool()
async def restore_backup(ctx: Context, node: str, storage_id: str, backup_file: str, 
                        vmid: int = None, force: bool = False) -> str:
    """Restore a VM or LXC container from a backup.

    Args:
        ctx: The MCP server provided context.
        node: The node where the backup should be restored.
        storage_id: The storage ID where the backup is located.
        backup_file: The name of the backup file to restore.
        vmid: Optional new VMID for the restored VM/LXC.
        force: Whether to force the restore operation.

    Returns:
        A string containing the task ID of the restore operation.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Determine if this is a VM or LXC backup based on the file extension
        is_lxc = backup_file.endswith('.tar.gz')
        
        # Prepare restore parameters
        params = {
            'archive': backup_file,
            'storage': storage_id,
            'force': 1 if force else 0
        }
        
        if vmid is not None:
            params['vmid'] = vmid
        
        # Start restore task using the appropriate endpoint
        if is_lxc:
            task = proxmox_client.nodes(node).lxc.restore.post(**params)
        else:
            task = proxmox_client.nodes(node).qemu.restore.post(**params)
        
        return f"Restore task started. Task ID: {task['data']}"
    except Exception as e:
        return f"Error restoring backup: {str(e)}"

@mcp.tool()
async def get_vms(ctx: Context) -> str:
    """Lists all virtual machines across the cluster.

    This tool retrieves information about all QEMU/KVM virtual machines
    across all nodes in the Proxmox cluster.

    Args:
        ctx: The MCP server provided context.

    Returns:
        A JSON formatted string containing information about all VMs across the cluster.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Check if we have a valid connection
        if proxmox_client is None:
            return "Error: Not connected to Proxmox server. Please check your connection settings."
        
        # Get online nodes
        online_nodes = get_online_nodes(proxmox_client)
        
        # Check if we got any online nodes
        if not online_nodes:
            return "No online nodes found in the cluster."
        
        # Get VMs from each online node
        all_vms = []
        for node in online_nodes:
            node_name = node['node']
            try:
                # Get QEMU VMs from this node
                vms = proxmox_client.nodes(node_name).qemu.get()
                
                # Add node information to each VM
                for vm in vms:
                    vm['node'] = node_name
                
                all_vms.extend(vms)
            except Exception as e:
                # If we can't get VMs from a node, log it but continue with other nodes
                print(f"Error getting VMs from node {node_name}: {str(e)}")
        
        if not all_vms:
            return "No VMs found on any online nodes."
            
        return json.dumps(all_vms, indent=2)
    except Exception as e:
        return f"Error retrieving VMs from cluster: {str(e)}"

@mcp.tool()
async def get_storage(ctx: Context) -> str:
    """Lists available storage pools across the cluster.

    This tool retrieves information about all storage pools
    across all nodes in the Proxmox cluster.

    Args:
        ctx: The MCP server provided context.

    Returns:
        A JSON formatted string containing information about all storage pools across the cluster.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get online nodes
        online_nodes = get_online_nodes(proxmox_client)
        
        # Get storage from each online node
        all_storage = []
        for node in online_nodes:
            node_name = node['node']
            try:
                # Get storage from this node
                storage = proxmox_client.nodes(node_name).storage.get()
                
                # Add node information to each storage entry
                for store in storage:
                    store['node'] = node_name
                
                all_storage.extend(storage)
            except Exception as e:
                # If we can't get storage from a node, log it but continue with other nodes
                print(f"Error getting storage from node {node_name}: {str(e)}")
        
        return json.dumps(all_storage, indent=2)
    except Exception as e:
        return f"Error retrieving storage from cluster: {str(e)}"

@mcp.tool()
async def get_vm_info(ctx: Context, node_name: str, vmid: int) -> str:
    """Retrieves detailed information about a specific virtual machine.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.

    Returns:
        A JSON formatted string containing detailed information about the specified VM.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get VM configuration
        config = proxmox_client.nodes(node_name).qemu(vmid).config.get()
        
        # Get VM status
        status = proxmox_client.nodes(node_name).qemu(vmid).status.current.get()
        
        # Get VM's snapshots if available
        try:
            snapshots = proxmox_client.nodes(node_name).qemu(vmid).snapshot.get()
        except Exception:
            snapshots = "Snapshot information not available"
        
        # Combine information
        vm_info = {
            "node_name": node_name,
            "vmid": vmid,
            "config": config,
            "status": status,
            "snapshots": snapshots
        }
        
        return json.dumps(vm_info, indent=2)
    except Exception as e:
        return f"Error retrieving information for VM {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def get_vm_status(ctx: Context, node_name: str, vmid: int) -> str:
    """Retrieves the current dynamic status of a specific virtual machine.

    Gets current status information such as running state, uptime, CPU usage,
    memory usage, disk I/O, and network I/O for a specific VM.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.

    Returns:
        A JSON formatted string containing current status information for the specified VM.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get VM status
        status = proxmox_client.nodes(node_name).qemu(vmid).status.current.get()
        
        # Optionally get more detailed runtime data if available
        try:
            # Get detailed VM runtime info
            rrd_data = proxmox_client.nodes(node_name).qemu(vmid).rrddata.get(
                timeframe="hour"  # Options: hour, day, week, month, year
            )
            status["rrd_data"] = rrd_data
        except Exception:
            # RRD data might not be available for all VMs
            pass
        
        return json.dumps(status, indent=2)
    except Exception as e:
        return f"Error retrieving status for VM {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def get_node_services(ctx: Context, node_name: str) -> str:
    """List the status of various Proxmox-related services running on a specific node.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node to get service status for.

    Returns:
        A JSON formatted string containing service status information.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get all services on the node
        services = proxmox_client.nodes(node_name).services.get()
        
        # Get detailed status for each service
        service_details = []
        for service in services:
            service_name = service.get('name')
            try:
                # Get detailed service state
                state = proxmox_client.nodes(node_name).services(service_name).state.get()
                service['state'] = state
                service_details.append(service)
            except Exception as e:
                # If we can't get state for a particular service, include the error
                service['state_error'] = str(e)
                service_details.append(service)
        
        return json.dumps(service_details, indent=2)
    except Exception as e:
        return f"Error retrieving services for node '{node_name}': {str(e)}"

@mcp.tool()
async def get_node_time(ctx: Context, node_name: str) -> str:
    """Get the current system time on the specified node.

    This is useful for checking time synchronization across the cluster.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node to get time information for.

    Returns:
        A JSON formatted string containing time information.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get time information from the node
        time_info = proxmox_client.nodes(node_name).time.get()
        
        # Add a human-readable timestamp for convenience
        if 'localtime' in time_info:
            timestamp = time_info['localtime']
            time_info['human_readable'] = time.strftime(
                '%Y-%m-%d %H:%M:%S', 
                time.localtime(timestamp)
            )
            
            # Calculate time difference with server running MCP
            server_time = int(time.time())
            time_diff = server_time - timestamp
            time_info['time_diff_seconds'] = time_diff
            time_info['server_time'] = server_time
            time_info['server_time_human'] = time.strftime(
                '%Y-%m-%d %H:%M:%S', 
                time.localtime(server_time)
            )
        
        return json.dumps(time_info, indent=2)
    except Exception as e:
        return f"Error retrieving time information for node '{node_name}': {str(e)}"

@mcp.tool()
async def get_cluster_status(ctx: Context) -> str:
    """Provides overall Proxmox cluster status information.

    This tool aggregates information about the cluster, including nodes,
    quorum status, cluster resources, and high availability status.

    Args:
        ctx: The MCP server provided context.

    Returns:
        A JSON formatted string containing cluster status information.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Collect various aspects of cluster status
        cluster_status = {}
        
        # Get basic cluster status and information
        try:
            cluster_status['status'] = proxmox_client.cluster.status.get()
        except Exception as e:
            cluster_status['status_error'] = str(e)
        
        # Get cluster resources (VMs, containers, storage)
        try:
            cluster_status['resources'] = proxmox_client.cluster.resources.get()
        except Exception as e:
            cluster_status['resources_error'] = str(e)
        
        # Get high availability status if configured
        try:
            cluster_status['ha_status'] = proxmox_client.cluster.ha.status.get()
        except Exception as e:
            cluster_status['ha_status_error'] = str(e)
        
        # Get replication status
        try:
            cluster_status['replication'] = proxmox_client.cluster.replication.get()
        except Exception as e:
            cluster_status['replication_error'] = str(e)
        
        # Get tasks
        try:
            cluster_status['tasks'] = proxmox_client.cluster.tasks.get()
        except Exception as e:
            cluster_status['tasks_error'] = str(e)
        
        # Get log
        try:
            cluster_status['log'] = proxmox_client.cluster.log.get(limit=20)  # Limit to recent entries
        except Exception as e:
            cluster_status['log_error'] = str(e)
        
        # Get backup schedule
        try:
            cluster_status['backup_schedule'] = proxmox_client.cluster.backup.get()
        except Exception as e:
            cluster_status['backup_schedule_error'] = str(e)
        
        # Add timestamp for when this status was generated
        cluster_status['timestamp'] = time.time()
        cluster_status['time_human'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        
        return json.dumps(cluster_status, indent=2)
    except Exception as e:
        return f"Error retrieving cluster status: {str(e)}"

# --- Main Execution ---
async def main():
    transport = os.getenv("TRANSPORT", "sse") # Default to SSE
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8051"))
    if transport == 'sse':
        print(f"Starting MCP server with SSE transport on {host}:{port}")
        await mcp.run_sse_async()
    else:
        print(f"Starting MCP server with STDIO transport")
        await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())
