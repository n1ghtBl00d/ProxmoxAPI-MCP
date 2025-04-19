# ProxmoxAPI-MCP Goals

This document outlines potential features and enhancements for the `ProxmoxAPI-MCP` server. The aim is to create a comprehensive and powerful MCP server for interacting with Proxmox VE clusters, building upon existing functionality and leveraging the extensive Proxmox API.

## Context

This project aims to enhance the capabilities available for interacting with Proxmox via an MCP server. It builds upon:

* **Existing `canvrno/ProxmoxMCP` Features:**
    * `get_nodes` – Lists all nodes in the Proxmox cluster
    * `get_node_status` – Gets detailed status of a specific node
    * `get_vms` – Lists all virtual machines across the cluster
    * `get_storage` – Lists available storage pools
    * `get_cluster_status` – Provides overall Proxmox cluster status
    * `execute_vm_command` – Executes a command in a VM's console via Guest Agent
* **Initial `801labs/ProxmoxAPI-MCP` Feature:**
    * `get_lxcs` - Lists all LXC containers across the cluster.

## Proposed Feature Enhancements

The following features are proposed additions, categorized for clarity. API endpoints are suggestions based on the Proxmox API structure and should be verified during implementation.

### I. VM & LXC Lifecycle Management (Actions)

These functions allow for direct control over the state of VMs and LXC containers.

* `start_vm(node, vmid)` / `start_lxc(node, vmid)`: Start a specific VM or container. (API: `POST /nodes/{node}/qemu/{vmid}/status/start`, `POST /nodes/{node}/lxc/{vmid}/status/start`)
* `stop_vm(node, vmid)` / `stop_lxc(node, vmid)`: Initiate a clean stop of a specific VM or container (may require guest agent). (API: `POST /nodes/{node}/qemu/{vmid}/status/stop`, `POST /nodes/{node}/lxc/{vmid}/status/stop`)
* `shutdown_vm(node, vmid)` / `shutdown_lxc(node, vmid)`: Send ACPI shutdown signal (VMs) or container shutdown command; often preferred over stop. (API: `POST /nodes/{node}/qemu/{vmid}/status/shutdown`, `POST /nodes/{node}/lxc/{vmid}/status/shutdown`)
* `reboot_vm(node, vmid)` / `reboot_lxc(node, vmid)`: Initiate a reboot sequence for a VM or container. (API: `POST /nodes/{node}/qemu/{vmid}/status/reboot`, `POST /nodes/{node}/lxc/{vmid}/status/reboot`)
* `reset_vm(node, vmid)`: Perform a hard reset on a VM (equivalent to pressing the reset button). Use with caution. (API: `POST /nodes/{node}/qemu/{vmid}/status/reset`)
* `suspend_vm(node, vmid)`: Suspend a VM to RAM (save state). (API: `POST /nodes/{node}/qemu/{vmid}/status/suspend`)
* `resume_vm(node, vmid)`: Resume a previously suspended VM. (API: `POST /nodes/{node}/qemu/{vmid}/status/resume`)

### II. Deeper Resource Information

These functions provide more detailed insights into various Proxmox resources.

* `get_vm_config(node, vmid)` / `get_lxc_config(node, vmid)`: Retrieve the full configuration details (memory, CPU, disks, network, options, etc.) for a specific VM or container. (API: `GET /nodes/{node}/qemu/{vmid}/config`, `GET /nodes/{node}/lxc/{vmid}/config`)
* `get_vm_status(node, vmid)` / `get_lxc_status(node, vmid)`: Get the *current* dynamic status (running, stopped), uptime, CPU usage, memory usage, disk I/O, network I/O for a specific VM or container. (API: `GET /nodes/{node}/qemu/{vmid}/status/current`, `GET /nodes/{node}/lxc/{vmid}/status/current`)
* `get_storage_content(node, storage_id)`: List the content (ISOs, templates, backups, disk images) available on a specific storage pool, optionally filtered by node. (API: `GET /nodes/{node}/storage/{storage}/content`, `GET /storage/{storage}/content`)
* `get_storage_status(node, storage_id)`: Get detailed status (usage, free space, availability, type) for a specific storage pool, optionally filtered by node. (API: `GET /nodes/{node}/storage/{storage}/status`, `GET /storage/{storage}/status`)
* `get_node_network(node)`: List network interfaces (bridges, bonds, VLANs) and their configuration on a specific node. (API: `GET /nodes/{node}/network`)
* `get_node_services(node)`: List the status of various Proxmox-related services running on a specific node (e.g., pveproxy, pvedaemon, corosync). (API: `GET /nodes/{node}/services/{service}/state`, `GET /nodes/{node}/services`)
* `get_node_time(node)`: Get the current system time on the specified node. Useful for checking time synchronization across the cluster. (API: `GET /nodes/{node}/time`)

### III. Cluster & Node Operations

Functions focused on cluster-wide information and node-level tasks.

* `get_cluster_log(limit, since)`: Retrieve recent cluster-wide log entries, with optional filtering. (API: `GET /cluster/log`)
* `get_cluster_tasks()`: List recent or currently running cluster-wide tasks (e.g., backups, migrations, HA actions). (API: `GET /cluster/tasks`)
* `get_task_status(node, upid)`: Get the current status and exit state of a specific task identified by its UPID (Unique Process ID). (API: `GET /nodes/{node}/tasks/{upid}/status`)
* `get_task_log(node, upid)`: Retrieve the full log output for a specific task. (API: `GET /nodes/{node}/tasks/{upid}/log`)
* `get_cluster_ha_status()`: Provide status information about High Availability groups, resources, and overall HA state, if configured. (API: `GET /cluster/ha/status`, `/cluster/ha/groups`, `/cluster/ha/resources`)
* `get_cluster_firewall_rules()` / `get_node_firewall_rules(node)` / `get_vm_firewall_rules(node, vmid)` / `get_lxc_firewall_rules(node, vmid)`: Retrieve firewall rules configured at the datacenter, node, VM, or container level. (API: `/cluster/firewall/rules`, `/nodes/{node}/firewall/rules`, `/nodes/{node}/qemu/{vmid}/firewall/rules`, `/nodes/{node}/lxc/{vmid}/firewall/rules`)

### IV. Backup & Restore Related

Functions specifically for managing backups.

* `list_backups(storage_id, vmid)`: Provide a more focused way to list available backups, potentially filtering by storage location or specific VM/LXC ID. (Likely requires parsing `get_storage_content` results).
* `create_backup(node, vmid, storage_id, mode)`: Trigger a new backup job (`vzdump`) for a specific VM or LXC container. Parameters would include node, VMID, target storage, backup mode (snapshot, suspend, stop), compression, etc. (API: `POST /nodes/{node}/vzdump`)
* `get_backup_status(node, job_id)`: Check the status of a running or completed backup job (likely relates to `get_task_status` using the backup task's UPID).

### V. Advanced/Potentially Risky Operations

These operations involve significant changes or resource allocation and should be implemented with extreme care and appropriate safeguards.

* `migrate_vm(node, vmid, target_node, online)` / `migrate_lxc(node, vmid, target_node, online)`: Initiate live or offline migration of a VM or container to another node in the cluster. (API: `POST /nodes/{node}/qemu/{vmid}/migrate`, `POST /nodes/{node}/lxc/{vmid}/migrate`)
* `clone_vm(node, vmid, new_id, name, full)` / `clone_lxc(node, vmid, new_id, name)`: Create a full clone or a linked clone (VMs only) of an existing VM or container. (API: `POST /nodes/{node}/qemu/{vmid}/clone`, `POST /nodes/{node}/lxc/{vmid}/clone`)
* `update_vm_config(node, vmid, config_changes)` / `update_lxc_config(node, vmid, config_changes)`: Modify the configuration of an existing VM or container (e.g., adjust RAM, CPU cores, disk size). **Warning:** This is a high-risk operation if not carefully implemented and validated, as incorrect parameters can break the guest. (API: `PUT /nodes/{node}/qemu/{vmid}/config`, `PUT /nodes/{node}/lxc/{vmid}/config`)
* `create_vm(...)` / `create_lxc(...)`: Functions to provision new VMs or containers based on provided parameters (template, ISO, resources). Very complex and high-risk. (API: `POST /nodes/{node}/qemu`, `POST /nodes/{node}/lxc`)
* `delete_vm(node, vmid)` / `delete_lxc(node, vmid)`: Permanently delete a VM or container and its associated data. **Warning: Irreversible and extremely high-risk.** (API: `DELETE /nodes/{node}/qemu/{vmid}`, `DELETE /nodes/{node}/lxc/{vmid}`)

## Implementation Considerations

* **Granularity vs. Simplicity:** Decide on the level of detail for functions. Should `get_vm_status` return all metrics, or should there be separate functions like `get_vm_cpu_usage`? Start broader, refine if needed.
* **Safety & Permissions:**
    * Prioritize implementing read-only (`get_*`) functions first.
    * Action functions (`start_*`, `stop_*`, `create_*`, `update_*`, `delete_*`) carry significant risk when exposed via an LLM. Implement strong input validation, confirmation steps, and potentially limit which actions are available.
    * Consider leveraging Proxmox API tokens with restricted permissions tailored to the MCP server's intended capabilities.
* **Error Handling:** Implement robust error handling for API responses (e.g., resource not found, invalid parameters, authentication failure, permission denied) and provide informative error messages back through the MCP.
* **Authentication:** Ensure secure handling and storage/configuration of Proxmox API tokens or user credentials used by the server.
* **API Endpoint Verification:** Always double-check the exact API endpoints, methods (GET/POST/PUT/DELETE), and required parameters against the official [Proxmox API Documentation](https://pve.proxmox.com/pve-docs/api-viewer/).
* **LLM Usability:** Design function names, parameters, and descriptions to be clear, unambiguous, and easily understood/used by a large language model.

## Suggested Priorities (Roadmap)

1.  **Foundation (Read-Only):** Implement core read-only functions providing detailed status and configuration:
    * `get_vm_config`, `get_lxc_config`
    * `get_vm_status`, `get_lxc_status`
    * `get_storage_content`, `get_storage_status`
    * `get_task_status`, `get_task_log`
2.  **Basic Lifecycle Actions:** Implement common VM/LXC state changes with necessary safety checks:
    * `start_vm`/`start_lxc`
    * `stop_vm`/`stop_lxc`
    * `shutdown_vm`/`shutdown_lxc`
    * `reboot_vm`/`reboot_lxc`
3.  **Expanded Information:** Add functions for broader context:
    * `get_node_network`, `get_node_services`, `get_cluster_log`, `get_cluster_tasks`
    * Firewall rule retrieval functions.
4.  **Advanced Actions (Use Case Driven):** Implement more complex or risky actions based on specific needs, prioritizing safety:
    * Backup creation/listing.
    * Migration, cloning (if required).
    * Configuration updates, creation, deletion (implement with extreme caution).