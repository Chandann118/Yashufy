import subprocess
import time
import sys
import os

def start_vortex_backend():
    print("🚀 Starting Vortex Music Backend...")
    
    # Check if we are in the backend directory
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found. Please run this script from the 'backend' directory.")
        return

    # Start FastAPI server in the background
    backend_process = subprocess.Popen([sys.executable, "main.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    print("📡 Starting Tunnel (localtunnel)...")
    try:
        # Start localtunnel on port 8000
        # Installing localtunnel globally if not present: npm install -g localtunnel
        tunnel_process = subprocess.Popen(["lt", "--port", "8000"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        for line in tunnel_process.stdout:
            if "your url is:" in line.lower():
                url = line.split("is:")[1].strip()
                print("\n" + "="*50)
                print(f"✅ TUNNEL ACTIVE: {url}")
                print("="*50)
                print("\n👉 ACTION REQUIRED:")
                print(f"1. Open your GitHub Gist (or discovery file)")
                print(f"2. Paste the URL above: {url}")
                print(f"3. All your friends' apps will sync automatically!")
                print("\nPress Ctrl+C to stop everything.")
                print("="*50 + "\n")
            
    except FileNotFoundError:
        print("❌ Error: 'lt' (localtunnel) command not found.")
        print("Please install it using: npm install -g localtunnel")
        backend_process.terminate()
        return
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        tunnel_process.terminate()
        backend_process.terminate()

if __name__ == "__main__":
    start_vortex_backend()
