"""
OmniDoc AI - Launcher Script
Runs the Streamlit dual-pane application with the current Python environment.
"""

import sys
import subprocess
from pathlib import Path

def main():
    root = Path(__file__).parent.resolve()
    app_path = root / "omnidoc" / "app.py"
    
    print("=" * 60)
    print("🚀 Launching OmniDoc AI - Multimodal Document QA")
    print("   Visual Source Attribution • Zero-Hallucination Guardrails")
    print("=" * 60)
    
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=false",
        "--theme.base=dark"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nOmniDoc AI stopped.")

if __name__ == "__main__":
    main()
