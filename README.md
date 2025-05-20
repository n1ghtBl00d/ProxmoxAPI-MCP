# ProxmoxAPI-MCP

A powerful Model Context Protocol (MCP) server implementation for interacting with Proxmox Virtual Environment API. This project provides a standardized interface to manage and control your Proxmox infrastructure programmatically, making it easier to automate and integrate with other systems.

## 🌟 Features

- Comprehensive management of Proxmox VE nodes, virtual machines (QEMU/KVM), and LXC containers.
- Detailed status monitoring for nodes, VMs, LXCs, and services.
- Lifecycle control for VMs and LXCs (start, stop, reboot, shutdown, suspend, resume).
- Snapshot management for VMs and LXCs (create, list, get config, delete, rollback).
- Cloning capabilities for VMs and LXCs, from both existing instances and templates, including cloning from snapshots.
- Template conversion for VMs and LXCs.
- Storage management: list pools, view content, identify backup-capable storage.
- Backup and restore operations for VMs and LXCs, including status tracking and backup deletion.
- Firewall rule management at cluster, node, VM, and LXC levels.
- Cluster-wide operations: view logs, tasks, HA status, and overall cluster health.
- QEMU Guest Agent interaction: execute commands, get OS info, hostname, users, network details, and ping agent.
- **Dangerous Mode**: A safety feature requiring explicit enablement for destructive operations like deletions, rollbacks, and restores.

## 📖 Tool Documentation

For a detailed list of all available tools, their parameters, and descriptions, please see the [**TOOLS.md**](TOOLS.md) file.

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

2. Edit `.env` with your Proxmox server details. 
   The following are the **minimum required** settings for connecting to your Proxmox server:
```env
PROXMOX_HOST=your-proxmox-host:8006
PROXMOX_USER=your-username@pam  # Or your specific realm, e.g., your-username@pve
PROXMOX_PASSWORD=your-secure-password
```

   Your `.env.example` file contains additional optional settings for:
    - **SSL/TLS verification**: Control how SSL certificates are handled (`PROXMOX_VERIFY_SSL`, `PROXMOX_SSL_WARN_ONLY`). It is strongly recommended to keep `PROXMOX_VERIFY_SSL=true` for security.
    - **API Timeout**: Adjust the timeout for Proxmox API calls (`PROXMOX_TIMEOUT`).
    - **Dangerous Actions Mode**: Enable or disable destructive tools (`PROXMOX_DANGEROUS_MODE`).
    - **MCP Server Settings**: Configure the MCP server transport, host, and port (`TRANSPORT`, `HOST`, `PORT`).

   Please refer to the comments in `.env.example` for more details on each setting.

### Dangerous Mode

Several tools perform actions that can lead to data loss or significant changes (e.g., deleting a VM, rolling back a snapshot, restoring a backup). To prevent accidental use, these "dangerous" tools are disabled by default.

To enable them, you can either:
1.  **Command-line argument**: Start the server with the `--dangerous-mode` flag:
    ```bash
    python proxmox_mcp.py --dangerous-mode
    ```
2.  **Environment variable**: Set the `PROXMOX_DANGEROUS_MODE` environment variable to `true`:
    ```env
    PROXMOX_DANGEROUS_MODE=true
    ```
The command-line flag takes precedence if both are set.

You can check if dangerous mode is currently active using the `is_dangerous_mode_enabled` tool.

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

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [proxmoxer](https://github.com/proxmoxer/proxmoxer) - Python wrapper for Proxmox API
- [mcp-mem0](https://github.com/coleam00/mcp-mem0) - MCP protocol reference implementation
- [fastmcp](https://github.com/jlowin/fastmcp) - Fast MCP server implementation
- Proxmox team for their excellent virtualization platform
