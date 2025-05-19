# ProxmoxAPI-MCP Goals

This document outlines potential features and enhancements for the `ProxmoxAPI-MCP` server. The aim is to create a comprehensive and powerful MCP server for interacting with Proxmox VE clusters, building upon existing functionality and leveraging the extensive Proxmox API.

## Context

This project aims to enhance the capabilities available for interacting with Proxmox via an MCP server. It builds upon:

* **Existing `canvrno/ProxmoxMCP` Features:**
    * ✅ `get_nodes` – Lists all nodes in the Proxmox cluster
    * ✅ `get_node_status` – Gets detailed status of a specific node
    * ✅ `get_vms` – Lists all virtual machines across the cluster
    * ✅ `get_storage` – Lists available storage pools
    * ❌ `get_cluster_status` – Provides overall Proxmox cluster status
    * ❌ `execute_vm_command` – Executes a command in a VM's console via Guest Agent
* **Initial `801labs/ProxmoxAPI-MCP` Feature:**
    * ✅ `get_lxc_containers` - Lists all LXC containers on a specific node

## Current Implementation Status

The following sections outline features that have been proposed, with their current implementation status indicated:

✅ = Implemented
⚠️ = Partially implemented or implemented differently
❌ = Not yet implemented

### I. VM & LXC Lifecycle Management (Actions)

These functions allow for direct control over the state of VMs and LXC containers.

* ✅ VM & LXC control actions implemented through:
  * `manage_vm(node_name, vmid, action)` - Supports: start, stop, reboot, shutdown, reset, suspend, resume
  * `manage_lxc_container(node_name, vmid, action)` - Supports: start, stop, reboot, shutdown, suspend, resume

### II. Deeper Resource Information

These functions provide more detailed insights into various Proxmox resources.

* ✅ `get_vm_info(node_name, vmid)` - Retrieves configuration, status, and snapshot information for a VM
* ✅ `get_lxc_container_info(node_name, vmid)` - Retrieves configuration and status information for an LXC container
* ✅ `get_vm_status(node_name, vmid)` - Gets current dynamic status of a VM, including runtime metrics
* ⚠️ LXC status available through `get_lxc_container_info`
* ✅ `get_storage_content(node, storage_id)` - Lists content available on a specific storage pool
* ✅ `get_storage_list(node)` - Gets storage locations on a node (storage status included)
* ⚠️ Network information available through `get_node_status`
* ❌ `get_node_services(node)` - Not yet implemented
* ❌ `get_node_time(node)` - Not yet implemented

### III. Cluster & Node Operations

Functions focused on cluster-wide information and node-level tasks.

* ✅ `get_cluster_log(limit, since)` - Retrieves recent cluster-wide log entries
* ✅ `get_cluster_tasks()` - Lists recent or currently running cluster-wide tasks
* ✅ `get_task_status(node, upid)` - Gets current status of a specific task
* ✅ `get_task_log(node, upid)` - Retrieves log output for a specific task
* ✅ `get_cluster_ha_status()` - Provides HA status information
* ✅ `get_cluster_firewall_rules()` - Retrieves datacenter firewall rules
* ✅ `get_node_firewall_rules(node)` - Retrieves node-level firewall rules
* ✅ `get_vm_firewall_rules(node, vmid)` - Retrieves VM firewall rules
* ✅ `get_lxc_firewall_rules(node, vmid)` - Retrieves LXC container firewall rules

### IV. Backup & Restore Related

Functions specifically for managing backups.

* ✅ `list_backups(node, storage_id, vmid)` - Lists available backups with filtering options
* ✅ `get_backup_storage_locations(node)` - Gets storage locations that can be used for backups
* ✅ `create_backup(node, vmid, storage_id, mode, compress, remove)` - Creates a backup of a VM or LXC container
* ✅ `get_backup_status(node, upid)` - Checks status of a backup task
* ✅ `restore_backup(node, storage_id, backup_file, vmid, force)` - Restores a VM or LXC container from backup

### V. Advanced/Potentially Risky Operations

These operations involve significant changes or resource allocation and should be implemented with extreme care and appropriate safeguards.

* ❌ `migrate_vm(node, vmid, target_node, online)` / `migrate_lxc(node, vmid, target_node, online)` - Not yet implemented
* ❌ `clone_vm(node, vmid, new_id, name, full)` / `clone_lxc(node, vmid, new_id, name)` - Not yet implemented
* ❌ `update_vm_config(node, vmid, config_changes)` / `update_lxc_config(node, vmid, config_changes)` - Not yet implemented
* ❌ `create_vm(...)` / `create_lxc(...)` - Not yet implemented
* ❌ `delete_vm(node, vmid)` / `delete_lxc(node, vmid)` - Not yet implemented

## Implementation Considerations

* **Granularity vs. Simplicity:** Decide on the level of detail for functions. Should `get_vm_status` return all metrics, or should there be separate functions like `get_vm_cpu_usage`? Start broader, refine if needed.
* **Safety & Permissions:**
    * Prioritize implementing read-only (`get_*`) functions first. ✅ Largely complete
    * Action functions (`start_*`, `stop_*`, `create_*`, `update_*`, `delete_*`) carry significant risk when exposed via an LLM. Implement strong input validation, confirmation steps, and potentially limit which actions are available. ✅ Basic lifecycle management implemented with validation
    * Consider leveraging Proxmox API tokens with restricted permissions tailored to the MCP server's intended capabilities.
* **Error Handling:** Implement robust error handling for API responses (e.g., resource not found, invalid parameters, authentication failure, permission denied) and provide informative error messages back through the MCP. ✅ Basic error handling in place
* **Authentication:** Ensure secure handling and storage/configuration of Proxmox API tokens or user credentials used by the server. ✅ Basic .env support implemented
* **API Endpoint Verification:** Always double-check the exact API endpoints, methods (GET/POST/PUT/DELETE), and required parameters against the official [Proxmox API Documentation](https://pve.proxmox.com/pve-docs/api-viewer/).
* **LLM Usability:** Design function names, parameters, and descriptions to be clear, unambiguous, and easily understood/used by a large language model.

## Future Priorities

1. **Complete Missing Basic Features:**
   * Implement `get_node_services` and `get_node_time`
   * Add `get_cluster_status` for overall cluster health monitoring
   * Implement `execute_vm_command` for guest agent interaction

2. **Quality Improvements:**
   * Add more comprehensive input validation and error handling
   * Improve documentation and examples
   * Add unit tests

3. **Advanced Operations:**
   * Implement migration, cloning, and configuration management features
   * Add VM and LXC creation and deletion capabilities (with appropriate safeguards)
   * Implement snapshot management functions