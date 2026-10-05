# agent_entry.py
import asyncio
from agent import mesh

async def run_agent_daemon():
    print("[BAND System Initialization] Connecting interface hooks to workspace platform...")
    # Listens continuously inside the BAND Desktop application pipeline
    await mesh.start()

if __name__ == "__main__":
    try:
        asyncio.run(run_agent_daemon())
    except KeyboardInterrupt:
        print("\n[BAND System Shutdown] Safely disconnected hooks.")
