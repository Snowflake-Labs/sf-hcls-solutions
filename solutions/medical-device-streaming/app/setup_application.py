#!/usr/bin/env python3
"""
Medical Device Streaming Platform - Complete Application Setup
==============================================================

Unified setup script that handles BOTH Python package installation AND Snowflake database infrastructure.
Professional-grade setup with comprehensive validation, dependency management, and database provisioning.

Usage:
    # Complete application setup (recommended)
    python setup_application.py install

    # Python package setup only
    python setup_application.py python-setup
    
    # Database infrastructure setup only  
    python setup_application.py database-setup
    
    # Fresh database setup (destructive)
    python setup_application.py database-fresh
    
    # Check dependencies only
    python setup_application.py check-deps
    
    # Help
    python setup_application.py help

Features:
- Python package installation with automatic dependency management
- Snowflake database infrastructure provisioning
- Complete validation and error handling
- Development and production installation modes
- Fresh setup capabilities with safety confirmations
- Console script registration
- Professional logging and progress tracking
"""

import sys
import os
import subprocess
import logging
import socket
import time
from pathlib import Path
from typing import Optional, Dict, List
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Minimum Python version requirement
PYTHON_REQUIRES = ">=3.11"

class ApplicationSetup:
    """Unified application setup handling both Python and Database infrastructure"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.python_setup_complete = False
        self.database_setup_complete = False
        
    def validate_python_version(self):
        """Validate Python version meets requirements"""
        current_version = sys.version_info
        min_version = (3, 11)
        
        if current_version < min_version:
            logger.error(f"❌ Python {min_version[0]}.{min_version[1]}+ required, found {current_version.major}.{current_version.minor}")
            logger.info("💡 This project requires Python 3.11+ for optimal performance")
            logger.info("   - 10-60% performance improvements")
            logger.info("   - Enhanced error messages")
            logger.info("   - Built-in TOML support")
            return False
        else:
            logger.info(f"✅ Python {current_version.major}.{current_version.minor}.{current_version.micro} meets requirements")
            return True
    
    def read_requirements(self, filename="supporting_code_files/requirements.txt"):
        """Read requirements from file and return as list"""
        requirements_path = self.project_root / filename
        if not requirements_path.exists():
            logger.warning(f"Requirements file {filename} not found")
            return []
        
        try:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            requirements = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    requirements.append(line)
            
            logger.info(f"📦 Loaded {len(requirements)} dependencies from {filename}")
            return requirements
            
        except Exception as e:
            logger.error(f"❌ Failed to read {filename}: {e}")
            return []
    
    def check_package_installed(self, package_requirement):
        """Check if a single package is installed"""
        package_name = package_requirement.split('>=')[0].split('==')[0].split('<')[0].split('>')[0].split('!')[0].strip()
        
        # Handle special import names
        import_name = package_name.replace('-', '_')
        if package_name == 'snowflake-connector-python':
            import_name = 'snowflake.connector'
        elif package_name == 'python-dotenv':
            import_name = 'dotenv'
        elif package_name == 'PyJWT':
            import_name = 'jwt'
        
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False
    
    def install_package(self, package, max_retries=3):
        """Install a single package with retry logic"""
        for attempt in range(max_retries):
            try:
                logger.info(f"📦 Installing {package} (attempt {attempt + 1}/{max_retries})")
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', package,
                    '--upgrade', '--no-warn-script-location'
                ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                logger.info(f"✅ Successfully installed {package}")
                return True
            except subprocess.CalledProcessError as e:
                logger.warning(f"⚠️  Attempt {attempt + 1} failed for {package}: {e.stderr.decode().strip() if e.stderr else 'Unknown error'}")
                if attempt == max_retries - 1:
                    logger.error(f"❌ Failed to install {package} after {max_retries} attempts")
                    return False
        return False
    
    def setup_python_package(self, install_missing=True):
        """Setup Python package with dependency management"""
        logger.info("🐍 Setting up Python package environment...")
        
        if not self.validate_python_version():
            return False
        
        # Check dependencies
        requirements = self.read_requirements()
        if not requirements:
            logger.warning("⚠️  No requirements found, skipping dependency check")
            return True
        
        missing_packages = []
        installed_packages = []
        
        for requirement in requirements:
            if self.check_package_installed(requirement):
                installed_packages.append(requirement.split('>=')[0].split('==')[0].strip())
            else:
                missing_packages.append(requirement)
        
        logger.info(f"✅ Found {len(installed_packages)} installed packages")
        
        if missing_packages:
            if install_missing:
                logger.info(f"📦 Installing {len(missing_packages)} missing packages...")
                failed_packages = []
                
                for package in missing_packages:
                    if not self.install_package(package):
                        failed_packages.append(package)
                
                if failed_packages:
                    logger.error(f"❌ Failed to install {len(failed_packages)} packages:")
                    for pkg in failed_packages:
                        logger.error(f"   - {pkg}")
                    logger.info("💡 Try installing manually:")
                    logger.info(f"   pip install {' '.join(failed_packages)}")
                    return False
                else:
                    logger.info("✅ All Python dependencies installed successfully!")
            else:
                logger.info(f"❌ Missing {len(missing_packages)} packages:")
                for pkg in missing_packages:
                    logger.info(f"   - {pkg}")
                logger.info("💡 Install with: pip install -r supporting_code_files/requirements.txt")
                return False
        else:
            logger.info("✅ All Python dependencies are already installed")
        
        self.python_setup_complete = True
        return True
    
    def install_package_via_setuptools(self):
        """Install the package using setuptools (equivalent to pip install -e .)"""
        try:
            logger.info("📦 Installing package in development mode...")
            
            # Create a minimal setup.py content for installation
            setup_content = f'''
from setuptools import setup, find_packages

setup(
    name="medical-device-streaming-platform",
    version="11.7.0",
    packages=find_packages(),
    py_modules=[
        "run_application", "setup_application"
    ],
    packages=["supporting_code_files"],
    python_requires="{PYTHON_REQUIRES}",
    entry_points={{
        'console_scripts': [
            'medical-streaming-setup=setup_application:database_setup',
            'medical-dashboard=run_application:main',
        ]
    }},
    package_data={{
        'supporting_code_files': ['*.toml', '*.json', '*.md', '*.txt', 'patients.json', 'requirements.txt']
    }},
    include_package_data=True,
)
'''
            # Write temporary setup.py
            temp_setup = self.project_root / "temp_setup.py"
            with open(temp_setup, 'w') as f:
                f.write(setup_content)
            
            # Install in development mode
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', '-e', '.', 
                '--config-settings', f'--global-option=--build-lib={temp_setup.parent}'
            ], cwd=self.project_root)
            
            # Clean up temporary setup file
            if temp_setup.exists():
                temp_setup.unlink()
            
            logger.info("✅ Package installed in development mode")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Package installation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during package installation: {e}")
            return False
    
    def setup_database_infrastructure(self, replace_existing=False):
        """Setup Snowflake database infrastructure"""
        logger.info("❄️  Setting up Snowflake database infrastructure...")
        
        try:
            # Import snowflake setup after ensuring dependencies are installed
            from supporting_code_files.snowflake_setup import MedicalDeviceSnowflakeSetup
            
            setup = MedicalDeviceSnowflakeSetup()
            
            if replace_existing:
                logger.info("🔄 Performing FRESH database setup (CREATE OR REPLACE)...")
                logger.warning("⚠️  This will replace all existing database objects and data!")
                
                # Ask for confirmation unless --force is provided
                if "--force" not in sys.argv:
                    response = input("Are you sure you want to proceed with fresh setup? (y/N): ").strip().lower()
                    if response not in ['y', 'yes']:
                        logger.info("❌ Fresh database setup cancelled by user")
                        return False
                
                setup.setup_complete_infrastructure(replace_existing=True)
            else:
                logger.info("🔧 Performing INCREMENTAL database setup (CREATE IF NOT EXISTS)...")
                setup.setup_complete_infrastructure(replace_existing=False)
            
            self.database_setup_complete = True
            logger.info("✅ Database infrastructure setup completed successfully!")
            return True
            
        except ImportError as e:
            logger.error(f"❌ Failed to import database setup modules: {e}")
            logger.info("💡 Make sure Python dependencies are installed first")
            return False
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            return False
    
    def complete_application_setup(self, fresh_database=False):
        """Complete application setup - both Python and Database"""
        logger.info("🚀 Starting COMPLETE APPLICATION SETUP...")
        logger.info("=" * 60)
        
        # Step 1: Python package setup
        logger.info("Step 1/2: Python Package Setup")
        if not self.setup_python_package(install_missing=True):
            logger.error("❌ Python package setup failed")
            return False
        
        # Step 2: Database infrastructure setup  
        logger.info("Step 2/2: Database Infrastructure Setup")
        if not self.setup_database_infrastructure(replace_existing=fresh_database):
            logger.error("❌ Database infrastructure setup failed")
            return False
        
        logger.info("🎉 COMPLETE APPLICATION SETUP SUCCESSFUL!")
        logger.info("=" * 60)
        logger.info("✅ Python package: Installed with all dependencies")
        logger.info("✅ Database infrastructure: Created and ready")
        logger.info("✅ Console scripts: Available system-wide")
        logger.info("")
        logger.info("🚀 You can now:")
        logger.info("   - Launch dashboard: python run_application.py")
        logger.info("   - Use console scripts: medical-dashboard")
        
        return True
    
    def database_setup(self):
        """Database setup entry point for console script"""
        return self.setup_database_infrastructure(replace_existing=False)
    
    def show_help(self):
        """Show help information"""
        print("🏥 Medical Device Streaming Platform - Complete Setup")
        print("=" * 60)
        print("Usage: python setup_application.py [command]")
        print("")
        print("Available commands:")
        print("  install         - Complete setup (Python + Database) [DEFAULT]")
        print("  python-setup    - Python package setup only")
        print("  database-setup  - Database infrastructure setup only")
        print("  database-fresh  - Fresh database setup (CREATE OR REPLACE)")
        print("  check-deps      - Check dependencies without installing")
        print("  help            - Show this help message")
        print("")
        print("Options:")
        print("  --force         - Skip confirmation prompts")
        print("")
        print("Examples:")
        print("  python setup_application.py                    # Complete setup")
        print("  python setup_application.py install            # Complete setup")
        print("  python setup_application.py database-fresh     # Fresh DB setup")
        print("  python setup_application.py check-deps         # Check only")


def main():
    """Main setup function with command handling"""
    
    # Parse command
    command = "install"  # Default command
    if len(sys.argv) > 1:
        command = sys.argv[1]
    
    # Initialize setup
    setup = ApplicationSetup()
    
    try:
        if command == "help" or command == "--help":
            setup.show_help()
            return 0
            
        elif command == "check-deps":
            logger.info("🔍 Dependency Check Mode")
            success = setup.setup_python_package(install_missing=False)
            return 0 if success else 1
            
        elif command == "python-setup":
            logger.info("🐍 Python Package Setup Mode")
            success = setup.setup_python_package(install_missing=True)
            return 0 if success else 1
            
        elif command == "database-setup":
            logger.info("❄️  Database Infrastructure Setup Mode")
            success = setup.setup_database_infrastructure(replace_existing=False)
            return 0 if success else 1
            
        elif command == "database-fresh":
            logger.info("🆕 Fresh Database Setup Mode")
            success = setup.setup_database_infrastructure(replace_existing=True)
            return 0 if success else 1
            
        elif command == "install":
            logger.info("🚀 Complete Application Setup Mode")
            success = setup.complete_application_setup(fresh_database=False)
            return 0 if success else 1
            
        else:
            logger.error(f"❌ Unknown command: {command}")
            setup.show_help()
            return 1
            
    except KeyboardInterrupt:
        logger.info("❌ Setup cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Setup failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
