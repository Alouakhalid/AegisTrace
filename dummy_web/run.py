import os
import sys
import threading
import time
import uvicorn

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

workspace_root = os.path.dirname(current_dir)
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

def start_target_server():
    try:
        from target_app import app as target_app
        uvicorn.run(target_app, host="127.0.0.1", port=5050, log_level="warning")
    except Exception:
        pass

if __name__ == "__main__":
    target_thread = threading.Thread(target=start_target_server, daemon=True)
    target_thread.start()
    time.sleep(0.3)
    print("=" * 70)
    print("AEGISTRACE — MULTI-AGENT TESTING LAB & LIVE TARGET")
    print("Dashboard UI:        http://127.0.0.1:8080")
    print("Live Target API:     http://127.0.0.1:5050 (ShopLite Vulnerable API)")
    print("======================================================================")
    uvicorn.run("app:app", host="127.0.0.1", port=8080, app_dir=current_dir)
