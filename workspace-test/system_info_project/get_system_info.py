import platform
import subprocess

def get_os_info():
    return platform.platform()

def get_cpu_info():
    try:
        # For Linux
        cpu_info = subprocess.check_output("lscpu | grep 'Model name' | cut -d ':' -f 2 | xargs", shell=True, text=True).strip()
        if not cpu_info:
            cpu_info = subprocess.check_output("cat /proc/cpuinfo | grep 'model name' | head -n 1 | cut -d ':' -f 2 | xargs", shell=True, text=True).strip()
        return cpu_info
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Could not retrieve CPU info."

def get_ram_info():
    try:
        # For Linux
        ram_info = subprocess.check_output("free -h | grep 'Mem:' | awk '{print $2}'", shell=True, text=True).strip()
        return ram_info
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Could not retrieve RAM info."

def get_gpu_info():
    try:
        # For Linux - common for integrated/dedicated GPUs
        gpu_info = subprocess.check_output("lspci | grep -i vga", shell=True, text=True).strip()
        if not gpu_info:
            # Try for NVIDIA specific
            gpu_info = subprocess.check_output("nvidia-smi --query-gpu=name --format=csv,noheader", shell=True, text=True).strip()
        return gpu_info
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Could not retrieve GPU info (or no dedicated GPU found)."

if __name__ == "__main__":
    print("--- System Information ---")
    print(f"Operating System: {get_os_info()}")
    print(f"CPU: {get_cpu_info()}")
    print(f"RAM: {get_ram_info()}")
    print(f"GPU: {get_gpu_info()}")
