# proxmox_mcp.py
import asyncio
import json
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

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
        # Decide how to handle connection errors - here we prevent startup
        raise RuntimeError(f"Failed to connect to Proxmox: {e}") from e
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
        rules = proxmox_client.nodes(node).qemu(vmid).firewall.rules.get()
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
