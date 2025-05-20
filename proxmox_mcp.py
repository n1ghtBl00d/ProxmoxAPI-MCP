# proxmox_mcp.py
import asyncio
import json
import os
import shlex
import argparse # Added for command-line argument parsing
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import time
from typing import Optional, Dict, List, Any, Union

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from proxmoxer import ProxmoxAPI

load_dotenv()

# --- Configuration ---
PROXMOX_HOST = os.getenv("PROXMOX_HOST")
# Simple fix for hostname format - strip protocol prefix if present
PROXMOX_HOST = PROXMOX_HOST.replace("https://", "").replace("http://", "") if PROXMOX_HOST else ""

PROXMOX_USER = os.getenv("PROXMOX_USER")
PROXMOX_PASSWORD = os.getenv("PROXMOX_PASSWORD")
PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "true").lower() not in ('false', '0', 'f')
# SSL options
PROXMOX_SSL_WARN_ONLY = os.getenv("PROXMOX_SSL_WARN_ONLY", "false").lower() in ('true', '1', 't')
PROXMOX_TIMEOUT = int(os.getenv("PROXMOX_TIMEOUT", "30"))

# Global flag for enabling dangerous actions
DANGEROUS_ACTIONS_ENABLED = False

# Basic validation
if not all([PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASSWORD]):
    print("Error: Please set PROXMOX_HOST, PROXMOX_USER, and PROXMOX_PASSWORD environment variables.")
    print("You can create a .env file based on .env.example")
    exit(1)

# Print SSL configuration for debugging
print(f"SSL verification: {'Enabled' if PROXMOX_VERIFY_SSL else 'Disabled'}")
if not PROXMOX_VERIFY_SSL:
    if PROXMOX_SSL_WARN_ONLY:
        print("WARNING: SSL verification is disabled. This is insecure and should only be used for testing.")
    else:
        print("WARNING: SSL verification is disabled. This is insecure.")
    
    # Suppress InsecureRequestWarning when verification is disabled
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        # Create client configuration
        proxmox_args = {
            'host': PROXMOX_HOST,
            'user': PROXMOX_USER,
            'password': PROXMOX_PASSWORD,
            'verify_ssl': PROXMOX_VERIFY_SSL,
            'timeout': PROXMOX_TIMEOUT
        }
        
        # Try to create client and test connection
        try:
            proxmox_client = ProxmoxAPI(**proxmox_args)
            # Test connection
            proxmox_client.version.get()
            print("Successfully connected to Proxmox.")
        except Exception as e:
            error_msg = str(e)
            # Handle common TLS/connection issues
            if 'SSL' in error_msg or 'TLS' in error_msg or 'certificate' in error_msg.lower():
                print(f"SSL/TLS Error connecting to Proxmox: {e}")
                print("This may be due to:")
                print("1. Self-signed or invalid certificates on the Proxmox server")
                print("2. TLS version mismatch")
                print("You can try setting PROXMOX_VERIFY_SSL=false in your .env file")
                print("Note: Disabling SSL verification reduces security!")
            elif 'timeout' in error_msg.lower():
                print(f"Timeout connecting to Proxmox: {e}")
                print(f"Current timeout is {PROXMOX_TIMEOUT} seconds.")
                print("You can increase the timeout by setting PROXMOX_TIMEOUT in your .env file.")
            elif 'refused' in error_msg.lower() or 'connection' in error_msg.lower():
                print(f"Connection Error: {e}")
                print("Please verify:")
                print(f"1. The Proxmox server at {PROXMOX_HOST} is running and accessible")
                print("2. Firewall settings allow connections")
                print("3. The hostname/IP and port are correct")
            elif 'Failed to parse' in error_msg:
                print(f"URL parsing error: {e}")
                print(f"The URL format for PROXMOX_HOST is invalid.")
                print("Should be either:")
                print("  - hostname:port (e.g., 192.168.1.100:8006)")
                print("  - https://hostname:port (e.g., https://192.168.1.100:8006)")
            else:
                print(f"Error connecting to Proxmox: {e}")
            
            # Rethrow the exception to fail initialization
            raise
        
        # Create the context with a valid connection
        yield ProxmoxContext(proxmox_client=proxmox_client)
    except Exception as e:
        print(f"Failed to initialize Proxmox client: {e}")
        # Yield a context with None to indicate failure
        yield ProxmoxContext(proxmox_client=None)
    finally:
        # No explicit cleanup needed for Proxmoxer client in this simple case
        print("Proxmox client context closing.")
        pass

# --- Helper Functions ---
def get_online_nodes(proxmox_client: ProxmoxAPI) -> List[Dict[str, Any]]:
    """Retrieves a list of online nodes from the Proxmox cluster."""
    try:
        all_nodes = proxmox_client.nodes.get()
        online_nodes = [node for node in all_nodes if node.get('status') == 'online']
        return online_nodes
    except Exception as e:
        print(f"Error retrieving online nodes: {str(e)}")
        return []

# --- MCP Server Setup ---
mcp = FastMCP(
    "mcp-proxmox",
    description="MCP server for interacting with a Proxmox VE cluster.",
    lifespan=proxmox_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8051"))
)

# --- Tools ---

# 1. Node-related tools (keep at top)
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

# 2. VM-related tools
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
async def create_vm_snapshot(ctx: Context, node_name: str, vmid: int, snapname: str, description: Optional[str] = None, vmstate: Optional[bool] = None) -> str:
    """Creates a snapshot of a virtual machine.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.
        snapname: The name of the snapshot.
        description: An optional description for the snapshot.
        vmstate: Optionally save the VM state (RAM). False if left blank.

    Returns:
        A string containing the task ID of the snapshot creation.
        Returns an error message string if the API call fails.
        Note: The task may return success even if the snapshot creation ultimately fails.
              Always check the task log for the final status.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        params = {'snapname': snapname}
        if description:
            params['description'] = description
        if vmstate is not None:
            params['vmstate'] = 1 if vmstate else 0
        
        task = proxmox_client.nodes(node_name).qemu(vmid).snapshot.post(**params)
        return f"Snapshot creation task started for VM {vmid}. Task ID: {task}"
    except Exception as e:
        return f"Error creating snapshot for VM {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def list_vm_snapshots(ctx: Context, node_name: str, vmid: int) -> str:
    """Lists all snapshots for a specific virtual machine.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.

    Returns:
        A JSON formatted string containing the list of snapshots.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        snapshots = proxmox_client.nodes(node_name).qemu(vmid).snapshot.get()
        return json.dumps(snapshots, indent=2)
    except Exception as e:
        return f"Error listing snapshots for VM {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def get_vm_snapshot_config(ctx: Context, node_name: str, vmid: int, snapname: str) -> str:
    """Retrieves the configuration of a specific VM snapshot.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.
        snapname: The name of the snapshot.

    Returns:
        A JSON formatted string containing the snapshot configuration.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        config = proxmox_client.nodes(node_name).qemu(vmid).snapshot(snapname).config.get()
        return json.dumps(config, indent=2)
    except Exception as e:
        return f"Error retrieving config for snapshot '{snapname}' of VM {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def delete_vm_snapshot(ctx: Context, node_name: str, vmid: int, snapname: str) -> str:
    """Deletes a specific snapshot of a virtual machine.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.
        snapname: The name of the snapshot to delete.

    Returns:
        A string containing the task ID of the snapshot deletion.
        Returns an error message string if the API call fails.

    Note: This is a dangerous action and requires dangerous mode to be enabled (--dangerous-mode or PROXMOX_DANGEROUS_MODE=true).
    """
    try:
        if not DANGEROUS_ACTIONS_ENABLED:
            return "Error: This is a dangerous action and requires dangerous mode to be enabled. Use --dangerous-mode flag or set PROXMOX_DANGEROUS_MODE=true."
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        task = proxmox_client.nodes(node_name).qemu(vmid).snapshot(snapname).delete()
        return f"Snapshot deletion task started for '{snapname}' of VM {vmid}. Task ID: {task}"
    except Exception as e:
        return f"Error deleting snapshot '{snapname}' for VM {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def rollback_vm_snapshot(ctx: Context, node_name: str, vmid: int, snapname: str) -> str:
    """Rolls back a virtual machine to a specific snapshot.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.
        snapname: The name of the snapshot to roll back to.

    Returns:
        A string containing the task ID of the rollback operation.
        Returns an error message string if the API call fails.

    Note: This is a dangerous action and requires dangerous mode to be enabled (--dangerous-mode or PROXMOX_DANGEROUS_MODE=true).
    """
    try:
        if not DANGEROUS_ACTIONS_ENABLED:
            return "Error: This is a dangerous action and requires dangerous mode to be enabled. Use --dangerous-mode flag or set PROXMOX_DANGEROUS_MODE=true."
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        task = proxmox_client.nodes(node_name).qemu(vmid).snapshot(snapname).rollback.post()
        return f"Rollback task started to snapshot '{snapname}' for VM {vmid}. Task ID: {task}"
    except Exception as e:
        return f"Error rolling back to snapshot '{snapname}' for VM {vmid} on node '{node_name}': {str(e)}"

# 3. LXC-related tools (parallel structure to VMs)
@mcp.tool()
async def get_lxcs(ctx: Context) -> str:
    """Lists all LXC containers across the cluster.

    This tool retrieves information about all LXC containers
    across all nodes in the Proxmox cluster.

    Args:
        ctx: The MCP server provided context.

    Returns:
        A JSON formatted string containing information about all LXC containers across the cluster.
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
        
        # Get LXC containers from each online node
        all_lxcs = []
        for node in online_nodes:
            node_name = node['node']
            try:
                # Get LXC containers from this node
                lxcs = proxmox_client.nodes(node_name).lxc.get()
                
                # Add node information to each LXC container
                for lxc in lxcs:
                    lxc['node'] = node_name
                
                all_lxcs.extend(lxcs)
            except Exception as e:
                # If we can't get LXCs from a node, log it but continue with other nodes
                print(f"Error getting LXC containers from node {node_name}: {str(e)}")
        
        if not all_lxcs:
            return "No LXC containers found on any online nodes."
            
        return json.dumps(all_lxcs, indent=2)
    except Exception as e:
        return f"Error retrieving LXC containers from cluster: {str(e)}"

@mcp.tool()
async def get_lxc_info(ctx: Context, node_name: str, vmid: int) -> str:
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
        
        # Try to get snapshot information if available
        try:
            snapshots = proxmox_client.nodes(node_name).lxc(vmid).snapshot.get()
        except Exception:
            snapshots = "Snapshot information not available"
        
        # Combine information
        container_info = {
            "node_name": node_name,
            "vmid": vmid,
            "config": config,
            "status": status,
            "snapshots": snapshots
        }
        
        return json.dumps(container_info, indent=2)
    except Exception as e:
        return f"Error retrieving information for LXC container {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def get_lxc_status(ctx: Context, node_name: str, vmid: int) -> str:
    """Retrieves the current dynamic status of a specific LXC container.

    Gets current status information such as running state, uptime, CPU usage,
    memory usage, disk I/O, and network I/O for a specific LXC container.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the LXC container.
        vmid: The VM ID of the LXC container.

    Returns:
        A JSON formatted string containing current status information for the specified LXC container.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get LXC container status
        status = proxmox_client.nodes(node_name).lxc(vmid).status.current.get()
        
        # Optionally get more detailed runtime data if available
        try:
            # Get detailed LXC runtime info
            rrd_data = proxmox_client.nodes(node_name).lxc(vmid).rrddata.get(
                timeframe="hour"  # Options: hour, day, week, month, year
            )
            status["rrd_data"] = rrd_data
        except Exception:
            # RRD data might not be available for all containers
            pass
        
        return json.dumps(status, indent=2)
    except Exception as e:
        return f"Error retrieving status for LXC container {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def manage_lxc(ctx: Context, node_name: str, vmid: int, action: str) -> str:
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
async def create_lxc_snapshot(ctx: Context, node_name: str, vmid: int, snapname: str, description: Optional[str] = None) -> str:
    """Creates a snapshot of an LXC container.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the LXC container.
        vmid: The VM ID of the LXC container.
        snapname: The name of the snapshot.
        description: An optional description for the snapshot.

    Returns:
        A string containing the task ID of the snapshot creation.
        Returns an error message string if the API call fails.
        Note: The task may return success even if the snapshot creation ultimately fails.
              Always check the task log for the final status.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        params = {'snapname': snapname}
        if description:
            params['description'] = description
        
        task = proxmox_client.nodes(node_name).lxc(vmid).snapshot.post(**params)
        return f"Snapshot creation task started for LXC container {vmid}. Task ID: {task}"
    except Exception as e:
        return f"Error creating snapshot for LXC container {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def list_lxc_snapshots(ctx: Context, node_name: str, vmid: int) -> str:
    """Lists all snapshots for a specific LXC container.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the LXC container.
        vmid: The VM ID of the LXC container.

    Returns:
        A JSON formatted string containing the list of snapshots.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        snapshots = proxmox_client.nodes(node_name).lxc(vmid).snapshot.get()
        return json.dumps(snapshots, indent=2)
    except Exception as e:
        return f"Error listing snapshots for LXC container {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def get_lxc_snapshot_config(ctx: Context, node_name: str, vmid: int, snapname: str) -> str:
    """Retrieves the configuration of a specific LXC snapshot.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the LXC container.
        vmid: The VM ID of the LXC container.
        snapname: The name of the snapshot.

    Returns:
        A JSON formatted string containing the snapshot configuration.
        Returns an error message string if the API call fails.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        config = proxmox_client.nodes(node_name).lxc(vmid).snapshot(snapname).config.get()
        return json.dumps(config, indent=2)
    except Exception as e:
        return f"Error retrieving config for snapshot '{snapname}' of LXC container {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def delete_lxc_snapshot(ctx: Context, node_name: str, vmid: int, snapname: str) -> str:
    """Deletes a specific snapshot of an LXC container.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the LXC container.
        vmid: The VM ID of the LXC container.
        snapname: The name of the snapshot to delete.

    Returns:
        A string containing the task ID of the snapshot deletion.
        Returns an error message string if the API call fails.

    Note: This is a dangerous action and requires dangerous mode to be enabled (--dangerous-mode or PROXMOX_DANGEROUS_MODE=true).
    """
    try:
        if not DANGEROUS_ACTIONS_ENABLED:
            return "Error: This is a dangerous action and requires dangerous mode to be enabled. Use --dangerous-mode flag or set PROXMOX_DANGEROUS_MODE=true."
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        task = proxmox_client.nodes(node_name).lxc(vmid).snapshot(snapname).delete()
        return f"Snapshot deletion task started for '{snapname}' of LXC container {vmid}. Task ID: {task}"
    except Exception as e:
        return f"Error deleting snapshot '{snapname}' for LXC container {vmid} on node '{node_name}': {str(e)}"

@mcp.tool()
async def rollback_lxc_snapshot(ctx: Context, node_name: str, vmid: int, snapname: str) -> str:
    """Rolls back an LXC container to a specific snapshot.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the LXC container.
        vmid: The VM ID of the LXC container.
        snapname: The name of the snapshot to roll back to.

    Returns:
        A string containing the task ID of the rollback operation.
        Returns an error message string if the API call fails.

    Note: This is a dangerous action and requires dangerous mode to be enabled (--dangerous-mode or PROXMOX_DANGEROUS_MODE=true).
    """
    try:
        if not DANGEROUS_ACTIONS_ENABLED:
            return "Error: This is a dangerous action and requires dangerous mode to be enabled. Use --dangerous-mode flag or set PROXMOX_DANGEROUS_MODE=true."
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        task = proxmox_client.nodes(node_name).lxc(vmid).snapshot(snapname).rollback.post()
        return f"Rollback task started to snapshot '{snapname}' for LXC container {vmid}. Task ID: {task}"
    except Exception as e:
        return f"Error rolling back to snapshot '{snapname}' for LXC container {vmid} on node '{node_name}': {str(e)}"

# 4. Storage and Backup-related tools
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
async def list_backups(ctx: Context, node: str = 'local', storage_id: Optional[str] = None, vmid: Optional[int] = None) -> str:
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
        
        # Filter for backup files by checking the content type
        backups = [item for item in content if item.get('content') == 'backup']
        
        # Filter by VMID if specified
        if vmid is not None:
            backups = [backup for backup in backups if backup.get('vmid') == str(vmid)]
        
        return json.dumps(backups, indent=2)
    except Exception as e:
        return f"Error listing backups: {str(e)}"

@mcp.tool()
async def create_backup(ctx: Context, node: str, vmid: int, storage_id: str, mode: str = 'snapshot', compress: str = 'lzo', remove: bool = False) -> str:
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
async def restore_backup(ctx: Context, node: str, storage_id: str, backup_file: str, vmid: int = None, force: bool = False) -> str:
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

    Note: This is a dangerous action and requires dangerous mode to be enabled (--dangerous-mode or PROXMOX_DANGEROUS_MODE=true).
    """
    try:
        if not DANGEROUS_ACTIONS_ENABLED:
            return "Error: This is a dangerous action and requires dangerous mode to be enabled. Use --dangerous-mode flag or set PROXMOX_DANGEROUS_MODE=true."
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

# 5. Firewall-related tools
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
        
        # Verify that this is a QEMU VM
        try:
            # Check if the VM exists
            vm_info = proxmox_client.nodes(node).qemu(vmid).status.current.get()
            # Get VM firewall rules
            rules = proxmox_client.nodes(node).qemu(vmid).firewall.rules.get()
            return json.dumps(rules, indent=2)
        except Exception as e:
            return f"Error: Could not find VM with ID {vmid} on node {node}: {str(e)}"
            
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

# 6. Cluster-wide tools
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

@mcp.tool()
async def is_dangerous_mode_enabled(ctx: Context) -> str:
    """Checks if dangerous actions mode is currently enabled.

    Returns:
        A JSON formatted string indicating whether dangerous mode is enabled.
        Example: {"dangerous_mode_enabled": true}
    """
    return json.dumps({"dangerous_mode_enabled": DANGEROUS_ACTIONS_ENABLED})

# 7. VM Agent tools (keep at bottom)
@mcp.tool()
async def vm_agent_exec(ctx: Context, node_name: str, vmid: int, command: str, username: Optional[str] = None) -> str:
    """Executes a command in a VM's console via QEMU Guest Agent.

    This tool allows execution of commands inside a virtual machine that has
    the QEMU Guest Agent installed and running. The Guest Agent must be properly
    configured in the VM for this to work.

    For long-running commands, the response will include a PID that can be used with 
    the vm_agent_exec_status tool to check for completion and retrieve output.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.
        command: The command to execute in the VM.
        username: Optional username to execute the command as (if omitted, uses the Guest Agent's default).

    Returns:
        A JSON formatted string containing the command execution results.
        Returns an error message string if the API call fails or Guest Agent is not available.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # First verify the VM exists and is running
        try:
            vm_status = proxmox_client.nodes(node_name).qemu(vmid).status.current.get()
            
            if vm_status.get('status') != 'running':
                return f"Error: VM {vmid} on node {node_name} is not running. Current status: {vm_status.get('status')}"
        except Exception as e:
            return f"Error: Could not verify VM {vmid} status on node {node_name}: {str(e)}"
        
        # Check if QEMU Guest Agent is running
        try:
            agent_info = proxmox_client.nodes(node_name).qemu(vmid).agent.get()
            if not agent_info:
                return f"Error: QEMU Guest Agent is not responding in VM {vmid}. Make sure it's installed and running."
        except Exception as e:
            return f"Error: QEMU Guest Agent not available for VM {vmid}: {str(e)}"
        
        # Prepare the command execution parameters
        # If the command contains spaces, split it into an array for the Proxmox API
        if ' ' in command:
            # Split the command into parts (respecting quoted strings)
            command_parts = shlex.split(command)
            params = {
                'command': command_parts
            }
        else:
            # For simple commands without spaces, pass as is
            params = {
                'command': command
            }
        
        # Add username if provided
        if username:
            params['username'] = username
        
        # Execute the command via Guest Agent
        try:
            print(f"Executing command in VM {vmid} on node {node_name}: {command}")
            print(f"Parameters being sent: {params}")
            result = proxmox_client.nodes(node_name).qemu(vmid).agent.exec.post(**params)
            print(f"Command execution response: {result}")
            return json.dumps(result, indent=2)
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                return f"Error: Command execution timed out. This may happen with long-running commands. Try using a shorter command or check if the guest agent is responsive."
            return f"Error executing command in VM {vmid} on node {node_name}: {error_msg}"
    except Exception as e:
        return f"Error executing command in VM {vmid} on node {node_name}: {str(e)}"

@mcp.tool()
async def vm_agent_exec_status(ctx: Context, node_name: str, vmid: int, pid: int) -> str:
    """Gets the status of a command executed in a VM via the QEMU Guest Agent.

    This tool retrieves the status of a process that was started by the guest agent
    using the vm_agent_exec tool. It allows checking if a long-running command
    has completed and obtaining its output.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.
        pid: The process ID returned from vm_agent_exec.

    Returns:
        A JSON formatted string containing the command execution status and results.
        Returns an error message string if the API call fails or Guest Agent is not available.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # Get the status of the process from the guest agent
        result = proxmox_client.nodes(node_name).qemu(vmid).agent("exec-status").get(pid=pid)
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error retrieving command status for PID {pid} in VM {vmid} on node {node_name}: {str(e)}"

@mcp.tool()
async def vm_agent_get_hostname(ctx: Context, node_name: str, vmid: int) -> str:
    """Gets the hostname of a VM via the QEMU Guest Agent.

    This tool retrieves the hostname of the virtual machine using the QEMU Guest Agent.
    The Guest Agent must be installed and running in the VM for this to work.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.

    Returns:
        A JSON formatted string containing the hostname information.
        Returns an error message string if the API call fails or Guest Agent is not available.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # First verify the VM exists and is running
        try:
            vm_status = proxmox_client.nodes(node_name).qemu(vmid).status.current.get()
            
            if vm_status.get('status') != 'running':
                return f"Error: VM {vmid} on node {node_name} is not running. Current status: {vm_status.get('status')}"
        except Exception as e:
            return f"Error: Could not verify VM {vmid} status on node {node_name}: {str(e)}"
        
        # Check if QEMU Guest Agent is running
        try:
            agent_info = proxmox_client.nodes(node_name).qemu(vmid).agent.get()
            if not agent_info:
                return f"Error: QEMU Guest Agent is not responding in VM {vmid}. Make sure it's installed and running."
        except Exception as e:
            return f"Error: QEMU Guest Agent not available for VM {vmid}: {str(e)}"
        
        # Get hostname via Guest Agent
        result = proxmox_client.nodes(node_name).qemu(vmid).agent("get-host-name").get()
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting hostname for VM {vmid} on node {node_name}: {str(e)}"

@mcp.tool()
async def vm_agent_get_osinfo(ctx: Context, node_name: str, vmid: int) -> str:
    """Gets the operating system information of a VM via the QEMU Guest Agent.

    This tool retrieves detailed information about the operating system running 
    inside the VM using the QEMU Guest Agent. The Guest Agent must be installed 
    and running in the VM for this to work.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.

    Returns:
        A JSON formatted string containing the OS information.
        Returns an error message string if the API call fails or Guest Agent is not available.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # First verify the VM exists and is running
        try:
            vm_status = proxmox_client.nodes(node_name).qemu(vmid).status.current.get()
            
            if vm_status.get('status') != 'running':
                return f"Error: VM {vmid} on node {node_name} is not running. Current status: {vm_status.get('status')}"
        except Exception as e:
            return f"Error: Could not verify VM {vmid} status on node {node_name}: {str(e)}"
        
        # Check if QEMU Guest Agent is running
        try:
            agent_info = proxmox_client.nodes(node_name).qemu(vmid).agent.get()
            if not agent_info:
                return f"Error: QEMU Guest Agent is not responding in VM {vmid}. Make sure it's installed and running."
        except Exception as e:
            return f"Error: QEMU Guest Agent not available for VM {vmid}: {str(e)}"
        
        # Get OS information via Guest Agent
        result = proxmox_client.nodes(node_name).qemu(vmid).agent("get-osinfo").get()
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting OS information for VM {vmid} on node {node_name}: {str(e)}"

@mcp.tool()
async def vm_agent_get_users(ctx: Context, node_name: str, vmid: int) -> str:
    """Gets the list of users currently logged in to a VM via the QEMU Guest Agent.

    This tool retrieves information about users currently logged in to the VM
    using the QEMU Guest Agent. The Guest Agent must be installed and running 
    in the VM for this to work.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.

    Returns:
        A JSON formatted string containing the list of logged-in users.
        Returns an error message string if the API call fails or Guest Agent is not available.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # First verify the VM exists and is running
        try:
            vm_status = proxmox_client.nodes(node_name).qemu(vmid).status.current.get()
            
            if vm_status.get('status') != 'running':
                return f"Error: VM {vmid} on node {node_name} is not running. Current status: {vm_status.get('status')}"
        except Exception as e:
            return f"Error: Could not verify VM {vmid} status on node {node_name}: {str(e)}"
        
        # Check if QEMU Guest Agent is running
        try:
            agent_info = proxmox_client.nodes(node_name).qemu(vmid).agent.get()
            if not agent_info:
                return f"Error: QEMU Guest Agent is not responding in VM {vmid}. Make sure it's installed and running."
        except Exception as e:
            return f"Error: QEMU Guest Agent not available for VM {vmid}: {str(e)}"
        
        # Get users via Guest Agent
        result = proxmox_client.nodes(node_name).qemu(vmid).agent("get-users").get()
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting users for VM {vmid} on node {node_name}: {str(e)}"

@mcp.tool()
async def vm_agent_ping(ctx: Context, node_name: str, vmid: int) -> str:
    """Pings the QEMU Guest Agent to check if it's responding.

    This tool sends a ping to the QEMU Guest Agent running in the VM to check if 
    it's responsive. This is a simple way to verify that the Guest Agent is running 
    and able to respond to requests.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.

    Returns:
        A JSON formatted string containing the ping response.
        Returns an error message string if the API call fails or Guest Agent is not available.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # First verify the VM exists and is running
        try:
            vm_status = proxmox_client.nodes(node_name).qemu(vmid).status.current.get()
            
            if vm_status.get('status') != 'running':
                return f"Error: VM {vmid} on node {node_name} is not running. Current status: {vm_status.get('status')}"
        except Exception as e:
            return f"Error: Could not verify VM {vmid} status on node {node_name}: {str(e)}"
        
        # Ping Guest Agent
        try:
            # The proper proxmoxer pattern for navigating the API structure
            result = proxmox_client.nodes(node_name).qemu(vmid).agent.ping.post()
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error: QEMU Guest Agent not responding for VM {vmid}: {str(e)}"
    except Exception as e:
        return f"Error pinging Guest Agent for VM {vmid} on node {node_name}: {str(e)}"
    
@mcp.tool()
async def vm_agent_get_network(ctx: Context, node_name: str, vmid: int) -> str:
    """Gets network interface information from a VM via the QEMU Guest Agent.

    This tool retrieves information about all network interfaces inside the VM
    using the QEMU Guest Agent. The Guest Agent must be installed and running
    in the VM for this to work.

    Args:
        ctx: The MCP server provided context.
        node_name: The name of the node containing the VM.
        vmid: The VM ID.

    Returns:
        A JSON formatted string containing the network interface information.
        Returns an error message string if the API call fails or Guest Agent is not available.
    """
    try:
        proxmox_client: ProxmoxAPI = ctx.request_context.lifespan_context.proxmox_client
        
        # First verify the VM exists and is running
        try:
            vm_status = proxmox_client.nodes(node_name).qemu(vmid).status.current.get()
            
            if vm_status.get('status') != 'running':
                return f"Error: VM {vmid} on node {node_name} is not running. Current status: {vm_status.get('status')}"
        except Exception as e:
            return f"Error: Could not verify VM {vmid} status on node {node_name}: {str(e)}"
        
        # Check if QEMU Guest Agent is running
        try:
            agent_info = proxmox_client.nodes(node_name).qemu(vmid).agent.get()
            if not agent_info:
                return f"Error: QEMU Guest Agent is not responding in VM {vmid}. Make sure it's installed and running."
        except Exception as e:
            return f"Error: QEMU Guest Agent not available for VM {vmid}: {str(e)}"
        
        # Get network interface information via Guest Agent
        result = proxmox_client.nodes(node_name).qemu(vmid).agent("network-get-interfaces").get()
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting network information for VM {vmid} on node {node_name}: {str(e)}"

# --- Main Execution ---
async def main():
    global DANGEROUS_ACTIONS_ENABLED # To modify the global variable

    parser = argparse.ArgumentParser(description="MCP server for Proxmox VE with optional dangerous mode.")
    parser.add_argument(
        '--dangerous-mode',
        action='store_true',
        help="Enable dangerous actions like delete and restore. Overrides PROXMOX_DANGEROUS_MODE env var."
    )
    # Parse only known arguments to allow MCP to handle its own if any are passed through uvx/etc.
    args, unknown = parser.parse_known_args()

    dangerous_mode_cli = args.dangerous_mode
    dangerous_mode_env = os.getenv("PROXMOX_DANGEROUS_MODE", "false").lower() in ('true', '1', 't')

    if dangerous_mode_cli:
        DANGEROUS_ACTIONS_ENABLED = True
        print("INFO: Dangerous actions ENABLED via command-line argument (--dangerous-mode).")
    elif dangerous_mode_env:
        DANGEROUS_ACTIONS_ENABLED = True
        print("INFO: Dangerous actions ENABLED via PROXMOX_DANGEROUS_MODE environment variable.")
    else:
        DANGEROUS_ACTIONS_ENABLED = False
        print("INFO: Dangerous actions DISABLED. Destructive tools will require the flag to operate.")

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
