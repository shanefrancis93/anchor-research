#!/usr/bin/env python3
"""
Launch the web dashboard for anchor research tool.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import and run the dashboard
from dashboard.app import app, socketio

if __name__ == '__main__':
    print("🔗 Starting Anchor Research Dashboard...")
    print("📊 Dashboard will be available at: http://127.0.0.1:5000")
    print("🔄 Press Ctrl+C to stop")
    print()
    
    try:
        socketio.run(app, debug=True, host='127.0.0.1', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)
