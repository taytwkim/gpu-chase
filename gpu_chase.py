"""
Cloud and Machine Learning Assignment 2: GPU Chase

Author: Tai Wan Kim
Date: October 10th, 2025

Deliverables:
1. Iterate through all regions and zones of Google Cloud
    - list_all_regions method iterates all regions
    - list_all_zones method iterate all zones

2. Attempt to create a VM with the selected GPU type
    - gpu_chase method attempts to create VMs in TEST_ZONES
"""

from google.cloud import compute_v1
from google.api_core import exceptions as gax
from pathlib import Path
from tabulate import tabulate
from datetime import datetime
from zoneinfo import ZoneInfo

PROJECT_ID = "cloud-and-ml-472514"
GPU_TYPE = "nvidia-tesla-t4"
VM_TYPE = "n1-standard-4"
IMAGE_FAM = "projects/debian-cloud/global/images/family/debian-12"

"""
To increase our chances of obtaining GPUs, we first find zones where the selected GPU_TYPE is actually available.
We find such zones during list_all_zones, and save it in TEST_ZONES.
In gpu_chase, we test the first NUM_ZONES zones in TEST_ZONES.
"""
TEST_ZONES = []
NUM_ZONES = 10

def pretty_print(filename, rows):
    """
    Pretty print rows in tabular format. Write to a file.
    """
    tz = "America/New_York"
    ts = datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S %Z%z")
    header = f"Timestamp: {ts}\n"
    
    txt = tabulate(rows, headers="keys", tablefmt="simple")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(txt + "\n")

def list_all_regions():
    """
    Iterate all regions of Google Cloud
    """
    client = compute_v1.RegionsClient()
    rows = []

    for region in client.list(project=PROJECT_ID):
        zones = []

        for zone in region.zones:
            zones.append(zone.rsplit("/", 1)[-1])
            
        row = {
            "region" : region.name,
            "status" : region.status,
            "zones" : zones
        }
        
        rows.append(row)

    return rows

def list_all_zones():
    """
    Iterate all zones of Google Cloud
    For each zone, chech whether GPU_TYPE is available.
    If available, add zone to TEST_ZONES so that it can be tested in gpu_chase
    """
    client = compute_v1.ZonesClient()
    acc_client = compute_v1.AcceleratorTypesClient()
    
    rows = []

    for zone in client.list(project=PROJECT_ID):
        region_name = zone.region.rsplit("/", 1)[-1]
        gpu_available = any(a.name == GPU_TYPE for a in acc_client.list(project=PROJECT_ID, zone=zone.name))

        rows.append({
            "region": region_name,
            "zone": zone.name,
            "status": zone.status,
            "gpu_type": GPU_TYPE,
            "gpu_available": gpu_available
        })

        if zone.status == "UP" and gpu_available:
            TEST_ZONES.append(zone.name)
    
    rows.sort(key=lambda r: (r["region"], r["zone"]))
    return rows

def build_instance_profile(zone, instance_name):
    """
    Build a VM profile
    """

    # 1) Specify disk image to boot from
    disk_init = compute_v1.AttachedDiskInitializeParams(
        source_image=IMAGE_FAM
    )

    # 2) Boot disk object from the image specified above
    boot_disk = compute_v1.AttachedDisk()
    boot_disk.auto_delete = True    # delete disk when the VM is deleted
    boot_disk.boot = True
    boot_disk.type_ = "PERSISTENT"
    boot_disk.initialize_params = disk_init

    # 3) Network interface
    nic = compute_v1.NetworkInterface(network="global/networks/default")

    # 4) Specify scheduling policy
    sched = compute_v1.Scheduling(on_host_maintenance="TERMINATE")  # terminate if host needs maintenance 

    # 5) Attach GPU
    accel = compute_v1.AcceleratorConfig(
        accelerator_type=f"projects/{PROJECT_ID}/zones/{zone}/acceleratorTypes/{GPU_TYPE}",
        accelerator_count=1,
    )

    inst = compute_v1.Instance(
        name=instance_name,
        machine_type=f"zones/{zone}/machineTypes/{VM_TYPE}",
        disks=[boot_disk],
        network_interfaces=[nic],
        scheduling=sched,
        guest_accelerators=[accel],
        labels={"purpose": "gpu-chase"},
    )

    return inst

def launch_instance(i, zone):
    """
    Attempt to launch instance in the specified zone.
    If launch succeeds, recored success and delete the VM.
    If laucn fails, record error code.
    """

    inst_client = compute_v1.InstancesClient()
    ops_client = compute_v1.ZoneOperationsClient()
    acc_client = compute_v1.AcceleratorTypesClient()

    name = f"gpu-chase-{zone}-{datetime.now().strftime('%H%M%S')}"
    gpu_is_available = any(a.name == GPU_TYPE for a in acc_client.list(project=PROJECT_ID, zone=zone))
    created = False

    row = {
        "id": i,
        "zone": zone,
        "vm_type": VM_TYPE,
        "gpu_type": GPU_TYPE,
        "gpu_available": "Y" if gpu_is_available else "N",
        "gpu_allocated": "N",
        "success": "N",
        "error_status": "-",
    }

    try:
        op = inst_client.insert(
            project = PROJECT_ID,
            zone = zone,
            instance_resource = build_instance_profile(zone, name),
        )

        op = ops_client.wait(project=PROJECT_ID, zone=zone, operation=op.name)

        if op.error and getattr(op.error, "errors", None):
            e = op.error.errors[0]
            print(f"❌ Create failed: code={e.code}")
            row["error_status"] = e.code
            return row

        created = True
        print(f"✅ VM created: name={name}, zone={zone}, vm_type={VM_TYPE}")
        row["gpu_allocated"] = "Y"
        row["success"] = "Y"
        return row

    except gax.GoogleAPICallError as e:
        print("❌ API error during create:", str(e))
        row["error_status"] = "ZONE_GPU_NOT_AVAILABLE"
        return row
    
    finally:
        # Clean up if VM creation was successful!
        if created:
            try:
                delop = inst_client.delete(project=PROJECT_ID, zone=zone, instance=name)
                ops_client.wait(project=PROJECT_ID, zone=zone, operation=delop.name)
                print("🧹 VM deleted.")

            except gax.GoogleAPICallError as cleanup_err:
                print("⚠️ Cleanup warning:", cleanup_err)

            except Exception as cleanup_err:
                print("⚠️ Cleanup error (manual delete may be needed):", cleanup_err)

def gpu_chase():
    rows = []
    zones = TEST_ZONES[:NUM_ZONES]
    success = []
    
    for i, zone in enumerate(zones):
        print(f"Attempt {i}: Creating VM in {zone}...")
        row = launch_instance(i, zone)
        rows.append(row)

        if row["success"] == "Y":
            success.append(zone)
        
        print("\n")
    
    print(f"GPU allocated in {len(success)} zones: {success}\n")
    return rows

def main():
    # Uncomment to check whether the output directory exists
    # OUTPUT_DIR = Path("output")
    # OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Iterating all regions...")
    region_rows = list_all_regions()
    regions_output_path = "output/regions.txt"
    print(f"Writing result to {regions_output_path}...")
    pretty_print(regions_output_path, region_rows)
    print("\n")

    print("Iterating all zones...")
    zone_rows = list_all_zones()
    print(f"{GPU_TYPE} currently available in {len(TEST_ZONES)} zones.")
    zones_output_path = "output/zones.txt" 
    pretty_print(zones_output_path, zone_rows)
    print(f"Writing result to {zones_output_path}...")
    print("\n")

    print("Chasing GPUs...")
    print(f"GPU_TYPE: {GPU_TYPE}, VM_TYPE: {VM_TYPE}\n")
    gpu_chase_rows = gpu_chase()
    gpus_output_path = "output/gpu_chase.txt"
    print(f"Writing result to {gpus_output_path}...") 
    pretty_print(gpus_output_path, gpu_chase_rows)

if __name__ == "__main__":
    main()