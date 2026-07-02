#!/usr/bin/env python3
"""
Application Launcher
====================

Professional launcher for the Medical Device Streaming Application with validation.
Includes comprehensive checks, environment validation, and configuration management.

Usage:
    python run_application.py                 # Run in foreground on port 8501
    python run_application.py --background    # Run in background mode on port 8501

Features:
- Locked to port 8501 (standard streamlit port)
- Automatic app.py directory detection
- Automatic port availability checking (finds next available if 8501 busy)
- Background/foreground mode support
- Graceful error handling and cleanup
- Environment and dependency validation
- Smart directory detection and validation
"""

import os
import sys
import subprocess
import logging
import socket
import time
import argparse
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'streamlit',
        'pandas', 
        'snowflake-connector-python',
        'cryptography'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'snowflake-connector-python':
                __import__('snowflake.connector')
            else:
                __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def find_app_directory():
    """Find the directory containing supporting_code_files/streamlit_app.py"""
    current_dir = Path.cwd()
    script_dir = Path(__file__).parent
    
    # Check current working directory first
    if (current_dir / 'supporting_code_files' / 'streamlit_app.py').exists():
        return current_dir
    
    # Check the script's directory
    if (script_dir / 'supporting_code_files' / 'streamlit_app.py').exists():
        return script_dir
    
    return None

def check_environment():
    """Check if environment is properly configured"""
    app_dir = find_app_directory()
    if not app_dir:
        return ['supporting_code_files/streamlit_app.py not found']
    
    # Check if required files exist in the same directory
    required_files = ['supporting_code_files/config.py', 'supporting_code_files/streamlit_app.py', '.env']
    
    missing_files = []
    for file_name in required_files:
        if not (app_dir / file_name).exists():
            missing_files.append(file_name)
    
    return missing_files

def check_port_available(port):
    """Check if a port is available for use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            return result != 0  # Port is available if connection fails
    except Exception:
        return False

def find_available_port(preferred_port=8501, max_attempts=10):
    """Find an available port starting from preferred_port"""
    for port in range(preferred_port, preferred_port + max_attempts):
        if check_port_available(port):
            return port
    return None

def main():
    """Main launcher function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Launch Medical Device Streaming Dashboard')
    parser.add_argument('--background', '-b', action='store_true', 
                       help='Run in background mode (daemon)')
    args = parser.parse_args()
    
    # Lock to port 8501 only
    args.port = 8501
    
    print("🏥 Medical Device Streaming Dashboard Launcher")
    print("=" * 50)
    
    # Check requirements
    print("🔍 Checking requirements...")
    missing_packages = check_requirements()
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print("   pip install -r supporting_code_files/requirements.txt")
        return 1
    
    print("✅ All required packages found")
    
    # Check environment
    print("🔍 Checking environment...")
    missing_files = check_environment()
    
    if missing_files:
        print("❌ Missing required files in parent directory:")
        for file_name in missing_files:
            print(f"   - {file_name}")
        print("\n💡 Make sure you're running from the correct directory")
        print("   and that the parent system is properly set up.")
        return 1
    
    print("✅ Environment check passed")
    
    # Find the app directory
    print("🔍 Finding streamlit_app.py location...")
    streamlit_dir = find_app_directory()
    
    if not streamlit_dir:
        print("❌ Could not find streamlit_app.py!")
        print("💡 Make sure you're running from the project root directory")
        print("💡 Or that streamlit_app.py exists in your project")
        return 1
    
    print(f"✅ Found streamlit_app.py in: {streamlit_dir}")
    
    # Find an available port (starting from 8501)
    print("🔍 Checking port 8501 availability...")
    preferred_port = 8501
    available_port = find_available_port(preferred_port)
    
    if not available_port:
        print("❌ No available ports found starting from 8501")
        print("💡 Try stopping any running streamlit apps or reboot your system")
        return 1
    
    if available_port != preferred_port:
        print(f"⚠️  Port 8501 is in use, using port {available_port} instead")
    else:
        print("✅ Port 8501 is available")
    
    print("\n🚀 Starting Streamlit dashboard...")
    print(f"📂 Running from: {streamlit_dir}")
    print(f"📱 Dashboard will open at: http://localhost:{available_port}")
    
    if args.background:
        print("🔄 Running in background mode...")
    else:
        print("⏹️  Press Ctrl+C to stop the dashboard")
    print("=" * 50)
    
    try:
        # Prepare streamlit command
        cmd = [
            sys.executable, '-m', 'streamlit', 'run', 'supporting_code_files/streamlit_app.py',
            '--server.port', str(available_port),
            '--server.address', 'localhost',
            '--browser.gatherUsageStats', 'false'
        ]
        
        if args.background:
            # Launch in background (detached process)
            process = subprocess.Popen(
                cmd, 
                cwd=streamlit_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            print(f"✅ Streamlit started in background with PID {process.pid}")
            print(f"📱 Access dashboard at: http://localhost:{available_port}")
            print(f"🛑 To stop: kill {process.pid}")
            return 0
        else:
            # Launch in foreground
            process = subprocess.Popen(cmd, cwd=streamlit_dir)
            # Wait for process to complete
            process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
        return 0
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 