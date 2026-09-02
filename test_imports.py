#!/usr/bin/env python
"""Quick import test to verify enhancements"""
import sys

try:
    print("[TEST] Importing jarvis_hud...")
    import jarvis_hud
    print("  ✓ jarvis_hud imported successfully")
    print(f"  ✓ JarvisHUD class available: {hasattr(jarvis_hud, 'JarvisHUD')}")
    
    print("[TEST] Importing sync client...")
    import jarvis_sync_client_tk
    print("  ✓ jarvis_sync_client_tk imported")
    
    print("[TEST] Checking optional modules...")
    try:
        from jarvis2.core.router import JarvisRouter
        print("  ✓ jarvis2 router available")
    except ImportError:
        print("  ⚠ jarvis2 router not available (expected for local-only mode)")
    
    try:
        import websockets
        print("  ✓ websockets available")
    except ImportError:
        print("  ⚠ websockets not installed (needed for sync server)")
    
    try:
        import streamlit
        print("  ✓ streamlit available")
    except ImportError:
        print("  ⚠ streamlit not installed (needed for hologram dashboard)")
    
    print("\n[SUCCESS] All core imports working!")
    print("[INFO] System ready for launch")
    
except Exception as e:
    print(f"[ERROR] Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
