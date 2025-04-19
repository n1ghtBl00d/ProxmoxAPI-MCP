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
        yield ProxmoxContext(proxmox_client=proxmox_client)
    except Exception as e:
        print(f"Error connecting to Proxmox: {e}")
        # Don't raise the error, just yield None to allow the server to continue
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
