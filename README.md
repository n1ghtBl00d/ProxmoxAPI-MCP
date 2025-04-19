# ProxmoxAPI-MCP

A powerful Model Context Protocol (MCP) server implementation for interacting with Proxmox Virtual Environment API. This project provides a standardized interface to manage and control your Proxmox infrastructure programmatically, making it easier to automate and integrate with other systems.

## 🌟 Features

### Node Management
- List all nodes in the cluster
- Get detailed node status (CPU, memory, disk, network)
- Monitor node services and health
- Execute commands on nodes via SSH

### Virtual Machine Management
- List all VMs across the cluster
- Get detailed VM configuration and status
- Control VM lifecycle (start, stop, reboot, shutdown)
- Execute commands in VM consoles
- Monitor VM resource usage

### LXC Container Management
- List all LXC containers
- Get detailed container configuration and status
- Control container lifecycle (start, stop, reboot, shutdown)
- Monitor container resource usage

### Storage Management
- List available storage pools
- Monitor storage usage and status
- Manage backups and restores
- Handle storage content

### Cluster Operations
- Monitor cluster health
- Track cluster tasks and logs
- Manage High Availability (HA) resources
- Handle cluster-wide operations

## 🚀 Getting Started

### Prerequisites
- Python 3.x
- Access to a Proxmox VE server
- Required Python packages (see requirements.txt)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ProxmoxAPI-MCP.git
cd ProxmoxAPI-MCP
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and set your Proxmox credentials:
```env
PROXMOX_HOST=your-proxmox-host
PROXMOX_USER=your-username
PROXMOX_PASSWORD=your-password
PROXMOX_VERIFY_SSL=true
```

### Running the Server

Start the MCP server:
```bash
python proxmox_mcp.py
```

The server will start on `0.0.0.0:8051` by default. You can modify the host and port using environment variables:
```env
HOST=0.0.0.0
PORT=8051
```

## 🛠️ Available Tools

### Node Operations
- `get_nodes()`: List all nodes in the cluster
- `get_node_status(node_name)`: Get detailed status for a specific node
- `execute_command(node_name, command)`: Execute a command on a node

### VM Operations
- `get_vms()`: List all VMs across the cluster
- `get_vm_config(node_name, vmid)`: Get VM configuration
- `get_vm_status(node_name, vmid)`: Get VM status
- `manage_vm(node_name, vmid, action)`: Control VM lifecycle

### LXC Operations
- `get_lxc_containers()`: List all LXC containers
- `get_lxc_container_info(node_name, vmid)`: Get container details
- `manage_lxc_container(node_name, vmid, action)`: Control container lifecycle

### Storage Operations
- `get_storage()`: List storage pools
- `create_backup(node, vmid, storage_id, mode)`: Create VM/LXC backups
- `restore_backup(node, storage_id, backup_file, vmid)`: Restore from backup

### Cluster Operations
- `get_cluster_status()`: Get cluster health status
- `get_cluster_ha_status()`: Get HA resource status
- `get_cluster_tasks()`: List cluster tasks

## 🔒 Security Considerations

- Store credentials securely using environment variables
- Use SSL verification for API connections
- Implement proper access controls
- Follow the principle of least privilege
- Regularly update dependencies

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [proxmoxer](https://github.com/proxmoxer/proxmoxer) - Python wrapper for Proxmox API
- [mcp-mem0](https://github.com/coleam00/mcp-mem0) - MCP protocol reference implementation
- [fastmcp](https://github.com/jlowin/fastmcp) - Fast MCP server implementation
- Proxmox team for their excellent virtualization platform
