# Proxmox MCP Server Tools

This document provides a detailed overview of all available tools in the Proxmox MCP server.

**Quick Navigation:**
- [Node-related Tools](#node-related-tools)
- [VM-related Tools](#vm-related-tools)
- [LXC-related Tools](#lxc-related-tools)
- [Storage and Backup-related Tools](#storage-and-backup-related-tools)
- [Firewall-related Tools](#firewall-related-tools)
- [Cluster-wide Tools](#cluster-wide-tools)
- [VM Agent Tools](#vm-agent-tools)
- [Utility Tools](#utility-tools)

---

## Node-related Tools

### 1. `get_nodes`
Lists all nodes in the Proxmox cluster.
Retrieves information about each node, such as its name, status, CPU usage, memory usage, and disk space.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
- **Returns:**
    - `str`: A JSON formatted string containing a list of nodes and their details. Returns an error message string if the API call fails.

### 2. `get_node_status`
Retrieves detailed status information for a specific node in the Proxmox cluster.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node to get status for.
- **Returns:**
    - `str`: A JSON formatted string containing detailed status information for the specified node. Returns an error message string if the API call fails.

### 3. `get_node_services`
List the status of various Proxmox-related services running on a specific node.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node to get service status for.
- **Returns:**
    - `str`: A JSON formatted string containing service status information. Returns an error message string if the API call fails.

### 4. `get_node_time`
Get the current system time on the specified node. This is useful for checking time synchronization across the cluster.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node to get time information for.
- **Returns:**
    - `str`: A JSON formatted string containing time information. Returns an error message string if the API call fails.

---

## VM-related Tools

### 1. `get_vms`
Lists all virtual machines across the cluster.
This tool retrieves information about all QEMU/KVM virtual machines across all nodes in the Proxmox cluster.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
- **Returns:**
    - `str`: A JSON formatted string containing information about all VMs across the cluster. Returns an error message string if the API call fails.

### 2. `get_vm_info`
Retrieves detailed information about a specific virtual machine.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
- **Returns:**
    - `str`: A JSON formatted string containing detailed information about the specified VM. Returns an error message string if the API call fails.

### 3. `get_vm_status`
Retrieves the current dynamic status of a specific virtual machine.
Gets current status information such as running state, uptime, CPU usage, memory usage, disk I/O, and network I/O for a specific VM.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
- **Returns:**
    - `str`: A JSON formatted string containing current status information for the specified VM. Returns an error message string if the API call fails.

### 4. `manage_vm`
Manages a virtual machine by performing actions like start, stop, or reboot.
This tool allows you to control the lifecycle of a VM by performing various actions such as starting, stopping, rebooting, shutting down, resetting, suspending, or resuming the VM.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
    - `action`: `str` - The action to perform on the VM. Valid values are: 'start', 'stop', 'reboot', 'shutdown', 'reset', 'suspend', 'resume'.
- **Returns:**
    - `str`: A string indicating the result of the action. Returns an error message string if the API call fails.

### 5. `create_vm_snapshot`
Creates a snapshot of a virtual machine.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
    - `snapname`: `str` - The name of the snapshot.
    - `description`: `Optional[str]` (Default: `None`) - An optional description for the snapshot.
    - `vmstate`: `bool` (Default: `False`) - Optionally save the VM state (RAM). False if left blank.
- **Returns:**
    - `str`: A string containing the task ID of the snapshot creation. Returns an error message string if the API call fails.
- **Note:** The task may return success even if the snapshot creation ultimately fails. Always check the task log for the final status.

### 6. `list_vm_snapshots`
Lists all snapshots for a specific virtual machine.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
- **Returns:**
    - `str`: A JSON formatted string containing the list of snapshots. Returns an error message string if the API call fails.

### 7. `get_vm_snapshot_config`
Retrieves the configuration of a specific VM snapshot.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
    - `snapname`: `str` - The name of the snapshot.
- **Returns:**
    - `str`: A JSON formatted string containing the snapshot configuration. Returns an error message string if the API call fails.

### 8. `delete_vm_snapshot`
Deletes a specific snapshot of a virtual machine.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
    - `snapname`: `str` - The name of the snapshot to delete.
- **Returns:**
    - `str`: A string containing the task ID of the snapshot deletion. Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

### 9. `rollback_vm_snapshot`
Rolls back a virtual machine to a specific snapshot.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
    - `snapname`: `str` - The name of the snapshot to roll back to.
- **Returns:**
    - `str`: A string containing the task ID of the rollback operation. Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

### 10. `clone_vm`
Clones a new virtual machine from an existing VM or template.
This tool is best used for cloning from templates. The 'full_clone' argument primarily affects cloning from templates; linked clones are typically only possible from templates.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The Proxmox node where the source VM/template resides.
    - `source_vmid`: `int` - The ID of the source VM or template.
    - `new_vmid`: `int` - The ID for the new VM.
    - `new_name`: `str` - The name for the new VM.
    - `target_storage`: `Optional[str]` (Default: `None`) - Optional storage ID for the new VM's disks. If not provided, the system may choose a default or linked clone behavior might be different.
    - `full_clone`: `bool` (Default: `True`) - Optional. If `True`, forces a full copy of all disks. If `False` (default): - When cloning from a template, a linked clone is attempted. - When cloning a normal (non-template) CT, a full clone is performed. Defaults to False.
    - `description`: `Optional[str]` (Default: `None`) - Optional description for the new VM.
    - `target_node`: `Optional[str]` (Default: `None`) - Optional target node for the new VM (if different from source node, requires shared storage).
    - `resource_pool`: `Optional[str]` (Default: `None`) - Optional resource pool to add the new VM to.
    - `snapname`: `Optional[str]` (Default: `None`) - Optional snapshot name to clone from. If not provided, clones the current state.
- **Returns:**
    - `str`: A string containing the task ID of the clone operation. Returns an error message string if the API call fails.
- **Note:** This action requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

### 11. `convert_vm_to_template`
Converts an existing virtual machine into a template.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The ID of the VM to convert to a template.
- **Returns:**
    - `str`: A string indicating the result of the conversion, usually a task ID. Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`). Converting a VM to a template makes it unusable as a regular VM; it can only be cloned.

### 12. `delete_vm`
Deletes a virtual machine.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The ID of the VM to delete.
- **Returns:**
    - `str`: A string containing the task ID of the VM deletion. Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

---

## LXC-related Tools

### 1. `get_lxcs`
Lists all LXC containers across the cluster.
This tool retrieves information about all LXC containers across all nodes in the Proxmox cluster.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
- **Returns:**
    - `str`: A JSON formatted string containing information about all LXC containers across the cluster. Returns an error message string if the API call fails.

### 2. `get_lxc_info`
Retrieves detailed information about a specific LXC container.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The VM ID of the LXC container.
- **Returns:**
    - `str`: A JSON formatted string containing detailed information about the specified LXC container. Returns an error message string if the API call fails.

### 3. `get_lxc_status`
Retrieves the current dynamic status of a specific LXC container.
Gets current status information such as running state, uptime, CPU usage, memory usage, disk I/O, and network I/O for a specific LXC container.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The VM ID of the LXC container.
- **Returns:**
    - `str`: A JSON formatted string containing current status information for the specified LXC container. Returns an error message string if the API call fails.

### 4. `manage_lxc`
Manages an LXC container by performing actions like start, stop, or reboot.
This tool allows you to control the lifecycle of an LXC container by performing various actions such as starting, stopping, rebooting, shutting down, suspending, or resuming the container.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The VM ID of the LXC container.
    - `action`: `str` - The action to perform on the container. Valid values are: 'start', 'stop', 'reboot', 'shutdown', 'suspend' (EXPERIMENTAL), 'resume' (EXPERIMENTAL).
- **Returns:**
    - `str`: A string indicating the result of the action. Returns an error message string if the API call fails.

### 5. `create_lxc_snapshot`
Creates a snapshot of an LXC container.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The VM ID of the LXC container.
    - `snapname`: `str` - The name of the snapshot.
    - `description`: `Optional[str]` (Default: `None`) - An optional description for the snapshot.
- **Returns:**
    - `str`: A string containing the task ID of the snapshot creation. Returns an error message string if the API call fails.
- **Note:** The task may return success even if the snapshot creation ultimately fails. Always check the task log for the final status.

### 6. `list_lxc_snapshots`
Lists all snapshots for a specific LXC container.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The VM ID of the LXC container.
- **Returns:**
    - `str`: A JSON formatted string containing the list of snapshots. Returns an error message string if the API call fails.

### 7. `get_lxc_snapshot_config`
Retrieves the configuration of a specific LXC snapshot.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The VM ID of the LXC container.
    - `snapname`: `str` - The name of the snapshot.
- **Returns:**
    - `str`: A JSON formatted string containing the snapshot configuration. Returns an error message string if the API call fails.

### 8. `delete_lxc_snapshot`
Deletes a specific snapshot of an LXC container.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The VM ID of the LXC container.
    - `snapname`: `str` - The name of the snapshot to delete.
- **Returns:**
    - `str`: A string containing the task ID of the snapshot deletion. Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

### 9. `rollback_lxc_snapshot`
Rolls back an LXC container to a specific snapshot.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The VM ID of the LXC container.
    - `snapname`: `str` - The name of the snapshot to roll back to.
- **Returns:**
    - `str`: A string containing the task ID of the rollback operation. Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

### 10. `clone_lxc`
Clones a new LXC container from an existing LXC or template.
This tool can clone any LXC container.
- When cloning from a template, a linked clone is attempted by default unless 'full_clone' is true.
- Cloning a regular (non-template) CT always results in a full clone, regardless of the 'full_clone' flag.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The Proxmox node where the source LXC/template resides.
    - `source_vmid`: `int` - The ID of the source LXC or template.
    - `new_vmid`: `int` - The ID for the new LXC container.
    - `new_name`: `str` - The hostname for the new LXC container.
    - `target_storage`: `Optional[str]` (Default: `None`) - Optional. Target storage for the new LXC's root disk (rootfs). For full clones, this explicitly sets the target storage. For linked clones (from templates), behavior might depend on the source template's storage if not set.
    - `full_clone`: `bool` (Default: `True`) - Optional. If `True`, forces a full copy of all disks. If `False` (default): - When cloning from a template, a linked clone is attempted. - When cloning a normal (non-template) CT, a full clone is performed. Defaults to False.
    - `description`: `Optional[str]` (Default: `None`) - Optional description for the new LXC.
    - `target_node`: `Optional[str]` (Default: `None`) - Optional target node for the new LXC (if different from source node, requires appropriate storage setup).
    - `resource_pool`: `Optional[str]` (Default: `None`) - Optional resource pool to add the new LXC to.
    - `snapname`: `Optional[str]` (Default: `None`) - Optional. The name of the snapshot to clone from. If not provided, clones the current state.
- **Returns:**
    - `str`: A string containing the task ID of the clone operation. Returns an error message string if the API call fails.
- **Note:** This action requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

### 11. `convert_lxc_to_template`
Converts an existing LXC container into a template.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The ID of the LXC container to convert to a template.
- **Returns:**
    - `str`: A string indicating the result of the conversion (usually empty on success for LXC template creation, or a task ID). Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`). Converting an LXC to a template makes it unusable as a regular container; it can only be cloned.

### 12. `delete_lxc`
Deletes an LXC container.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the LXC container.
    - `vmid`: `int` - The ID of the LXC container to delete.
- **Returns:**
    - `str`: A string containing the task ID of the LXC container deletion. Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

---

## Storage and Backup-related Tools

### 1. `get_storage`
Lists available storage pools across the cluster.
This tool retrieves information about all storage pools across all nodes in the Proxmox cluster.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
- **Returns:**
    - `str`: A JSON formatted string containing information about all storage pools across the cluster. Returns an error message string if the API call fails.

### 2. `get_storage_list`
Get a list of all available storage locations on a node.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node to get storage information from.
- **Returns:**
    - `str`: A JSON formatted string containing storage information. Returns an error message string if the API call fails.

### 3. `get_storage_content`
Get the content of a specific storage location.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node where the storage is located.
    - `storage_id`: `str` - The ID of the storage to check.
- **Returns:**
    - `str`: A JSON formatted string containing storage content. Returns an error message string if the API call fails.

### 4. `get_backup_storage_locations`
Get a list of storage locations that can be used for backups.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node to check for backup-capable storage.
- **Returns:**
    - `str`: A JSON formatted string containing backup-capable storage locations. Returns an error message string if the API call fails.

### 5. `list_backups`
List available backups, optionally filtered by storage location or VM/LXC ID.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node to check for backups.
    - `storage_id`: `Optional[str]` (Default: `None`) - Optional storage ID to filter backups by location.
    - `vmid`: `Optional[int]` (Default: `None`) - Optional VM/LXC ID to filter backups by.
- **Returns:**
    - `str`: A JSON formatted string containing backup information. Returns an error message string if the API call fails.

### 6. `create_backup`
Create a backup of a VM or LXC container.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node where the VM/LXC is located.
    - `vmid`: `int` - The ID of the VM/LXC to backup.
    - `storage_id`: `str` - The storage ID where the backup should be stored.
    - `mode`: `str` (Default: `'snapshot'`) - Backup mode ('snapshot', 'suspend', or 'stop').
    - `compress`: `str` (Default: `'lzo'`) - Compression type ('lzo', 'gzip', or 'zstd').
    - `remove`: `bool` (Default: `False`) - Whether to remove old backups after successful backup.
- **Returns:**
    - `str`: A string containing the task ID (UPID) of the backup operation. Returns an error message string if the API call fails.

### 7. `get_backup_status`
Get the status of a backup task.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node where the backup task is running.
    - `upid`: `str` - The Unique Process ID of the backup task.
- **Returns:**
    - `str`: A JSON formatted string containing backup task status and log. Returns an error message string if the API call fails.

### 8. `restore_backup`
Restore a VM or LXC container from a backup.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node where the backup should be restored.
    - `storage_id`: `str` - The storage ID where the backup is located.
    - `backup_file`: `str` - The name of the backup file to restore.
    - `vmid`: `Optional[int]` (Default: `None`) - Optional new VMID for the restored VM/LXC.
    - `force`: `bool` (Default: `False`) - Whether to force the restore operation.
- **Returns:**
    - `str`: A string containing the task ID of the restore operation. Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

### 9. `delete_backup`
Deletes a specific backup file from a storage location.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node where the storage is located.
    - `storage_id`: `str` - The ID of the storage containing the backup.
    - `backup_file`: `str` - The volume ID of the backup file to delete (e.g., 'local:backup/vzdump-qemu-100-2023_10_26-10_00_00.vma.zst').
- **Returns:**
    - `str`: A string indicating the result of the deletion (Task ID). Returns an error message string if the API call fails.
- **Note:** This is a dangerous action and requires dangerous mode to be enabled (`--dangerous-mode` or `PROXMOX_DANGEROUS_MODE=true`).

---

## Firewall-related Tools

### 1. `get_cluster_firewall_rules`
Retrieve firewall rules configured at the datacenter level.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
- **Returns:**
    - `str`: A JSON formatted string containing cluster firewall rules. Returns an error message string if the API call fails.

### 2. `get_node_firewall_rules`
Retrieve firewall rules configured at the node level.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node to get firewall rules for.
- **Returns:**
    - `str`: A JSON formatted string containing node firewall rules. Returns an error message string if the API call fails.

### 3. `get_vm_firewall_rules`
Retrieve firewall rules configured for a specific VM.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node hosting the VM.
    - `vmid`: `int` - The ID of the VM.
- **Returns:**
    - `str`: A JSON formatted string containing VM firewall rules. Returns an error message string if the API call fails or if the VM is not found.

### 4. `get_lxc_firewall_rules`
Retrieve firewall rules configured for a specific LXC container.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node hosting the LXC container.
    - `vmid`: `int` - The ID of the LXC container.
- **Returns:**
    - `str`: A JSON formatted string containing LXC firewall rules. Returns an error message string if the API call fails.

---

## Cluster-wide Tools

### 1. `get_cluster_log`
Retrieve recent cluster-wide log entries.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `limit`: `int` (Default: `50`) - Maximum number of log entries to return.
    - `since`: `Optional[str]` (Default: `None`) - Optional timestamp to filter logs from a specific time.
- **Returns:**
    - `str`: A JSON formatted string containing cluster log entries. Returns an error message string if the API call fails.

### 2. `get_cluster_tasks`
List recent or currently running cluster-wide tasks.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
- **Returns:**
    - `str`: A JSON formatted string containing cluster tasks. Returns an error message string if the API call fails.

### 3. `get_task_status`
Get the current status of a specific task.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node where the task is running.
    - `upid`: `str` - The Unique Process ID of the task.
- **Returns:**
    - `str`: A JSON formatted string containing task status. Returns an error message string if the API call fails.

### 4. `get_task_log`
Retrieve the full log output for a specific task.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node`: `str` - The node where the task is running.
    - `upid`: `str` - The Unique Process ID of the task.
- **Returns:**
    - `str`: A JSON formatted string containing task log. Returns an error message string if the API call fails.

### 5. `get_cluster_ha_status`
Get High Availability status information.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
- **Returns:**
    - `str`: A JSON formatted string containing HA status information. Returns an error message string if the API call fails.

### 6. `get_cluster_status`
Provides overall Proxmox cluster status information.
This tool aggregates information about the cluster, including nodes, quorum status, cluster resources, and high availability status.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
- **Returns:**
    - `str`: A JSON formatted string containing cluster status information. Returns an error message string if the API call fails.

---

## VM Agent Tools
These tools require the QEMU Guest Agent to be installed, running, and properly configured within the target Virtual Machine.

### 1. `vm_agent_exec`
Executes a command in a VM's console via QEMU Guest Agent.
For long-running commands, the response will include a PID that can be used with the `vm_agent_exec_status` tool to check for completion and retrieve output.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
    - `command`: `str` - The command to execute in the VM.
    - `username`: `Optional[str]` (Default: `None`) - Optional username to execute the command as (if omitted, uses the Guest Agent's default).
- **Returns:**
    - `str`: A JSON formatted string containing the command execution results (may include a PID for the command). Returns an error message string if the API call fails or Guest Agent is not available/responsive.

### 2. `vm_agent_exec_status`
Gets the status of a command executed in a VM via the QEMU Guest Agent.
This tool retrieves the status of a process that was started by the guest agent using the `vm_agent_exec` tool.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
    - `pid`: `int` - The process ID returned from `vm_agent_exec`.
- **Returns:**
    - `str`: A JSON formatted string containing the command execution status and results (e.g., stdout, stderr, exit code). Returns an error message string if the API call fails or Guest Agent is not available.

### 3. `vm_agent_get_hostname`
Gets the hostname of a VM via the QEMU Guest Agent.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
- **Returns:**
    - `str`: A JSON formatted string containing the hostname information. Returns an error message string if the API call fails or Guest Agent is not available.

### 4. `vm_agent_get_osinfo`
Gets the operating system information of a VM via the QEMU Guest Agent.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
- **Returns:**
    - `str`: A JSON formatted string containing the OS information. Returns an error message string if the API call fails or Guest Agent is not available.

### 5. `vm_agent_get_users`
Gets the list of users currently logged in to a VM via the QEMU Guest Agent.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
- **Returns:**
    - `str`: A JSON formatted string containing the list of logged-in users. Returns an error message string if the API call fails or Guest Agent is not available.

### 6. `vm_agent_ping`
Pings the QEMU Guest Agent to check if it's responding.
This is a simple way to verify that the Guest Agent is running and able to respond to requests.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
- **Returns:**
    - `str`: A JSON formatted string containing the ping response (usually a success indicator). Returns an error message string if the API call fails or Guest Agent is not available/responsive.

### 7. `vm_agent_get_network`
Gets network interface information from a VM via the QEMU Guest Agent.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
    - `node_name`: `str` - The name of the node containing the VM.
    - `vmid`: `int` - The VM ID.
- **Returns:**
    - `str`: A JSON formatted string containing the network interface information. Returns an error message string if the API call fails or Guest Agent is not available.

---

## Utility Tools

### 1. `is_dangerous_mode_enabled`
Checks if dangerous actions mode is currently enabled.

- **Parameters:**
    - `ctx`: `Context` (Implicitly passed) - The MCP server provided context.
- **Returns:**
    - `str`: A JSON formatted string indicating whether dangerous mode is enabled. Example: `{"dangerous_mode_enabled": true}` 