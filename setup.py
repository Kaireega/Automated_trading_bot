#!/usr/bin/env python3
"""
Automated Trading Bot Setup Script

This script helps set up the virtual environment and install dependencies
for the Automated Trading Bot project.

Usage:
    python3 setup.py [option]

Options:
    minimal     - Install minimal dependencies only
    scraping    - Install scraping dependencies
    full        - Install full production dependencies
    dev         - Install development dependencies
    test        - Test the current setup
    help        - Show this help message
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


class TradingBotSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "trading_bot_env"
        self.is_windows = platform.system() == "Windows"
        
    def run_command(self, command, description=""):
        """Run a shell command and return success status"""
        print(f"🔧 {description}")
        try:
            result = subprocess.run(command, shell=True, check=True, 
                                  capture_output=True, text=True)
            print(f"✅ {description} - Success")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} - Failed")
            print(f"Error: {e.stderr}")
            return False
    
    def check_python_version(self):
        """Check if Python version is compatible"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"❌ Python {version.major}.{version.minor} detected")
            print("⚠️  Python 3.8 or higher is required")
            return False
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
        return True
    
    def create_venv(self):
        """Create virtual environment if it doesn't exist"""
        if self.venv_path.exists():
            print("✅ Virtual environment already exists")
            return True
        
        print("📋 Creating virtual environment...")
        return self.run_command(
            f"python3 -m venv {self.venv_path}",
            "Creating virtual environment"
        )
    
    def activate_venv(self):
        """Get activation command for virtual environment"""
        if self.is_windows:
            activate_script = self.venv_path / "Scripts" / "activate.bat"
            python_exe = self.venv_path / "Scripts" / "python.exe"
            pip_exe = self.venv_path / "Scripts" / "pip.exe"
        else:
            activate_script = self.venv_path / "bin" / "activate"
            python_exe = self.venv_path / "bin" / "python"
            pip_exe = self.venv_path / "bin" / "pip"
        
        return str(python_exe), str(pip_exe)
    
    def install_requirements(self, requirements_file):
        """Install requirements from specified file"""
        python_exe, pip_exe = self.activate_venv()
        
        # Upgrade pip first
        if not self.run_command(
            f'"{python_exe}" -m pip install --upgrade pip',
            "Upgrading pip"
        ):
            return False
        
        # Install requirements
        req_file = self.project_root / requirements_file
        if not req_file.exists():
            print(f"❌ Requirements file not found: {requirements_file}")
            return False
        
        return self.run_command(
            f'"{pip_exe}" install -r "{req_file}"',
            f"Installing {requirements_file}"
        )
    
    def test_setup(self):
        """Test the current setup"""
        python_exe, pip_exe = self.activate_venv()
        
        print("🧪 Testing setup...")
        
        # Test Python import
        test_commands = [
            (f'"{python_exe}" -c "import pandas, numpy, requests; print(\'✅ Core packages OK\')"', "Testing core packages"),
            (f'"{python_exe}" -c "import bs4, cloudscraper; print(\'✅ Scraping packages OK\')"', "Testing scraping packages"),
            (f'"{python_exe}" -c "import oandapyV20; print(\'✅ Trading packages OK\')"', "Testing trading packages"),
        ]
        
        success_count = 0
        for command, description in test_commands:
            if self.run_command(command, description):
                success_count += 1
        
        print(f"\n📊 Test Results: {success_count}/{len(test_commands)} tests passed")
        
        if success_count == len(test_commands):
            print("🎉 Setup is working perfectly!")
            return True
        else:
            print("⚠️  Some packages may be missing. Try installing requirements.")
            return False
    
    def show_help(self):
        """Show help information"""
        print(__doc__)
        print("\n📋 Available Requirements Files:")
        print("   requirements-minimal.txt  - Basic functionality only")
        print("   requirements-scraping.txt - Web scraping features")
        print("   requirements.txt          - Full production setup")
        print("   requirements-dev.txt      - Development and testing tools")
        
        print("\n🚀 Quick Start:")
        print("   1. python3 setup.py minimal")
        print("   2. python3 setup.py test")
        print("   3. source trading_bot_env/bin/activate  # On macOS/Linux")
        print("   4. python src/trading_bot/main.py")
    
    def run(self, option=None):
        """Main setup function"""
        print("🤖 Automated Trading Bot Setup")
        print("=" * 40)
        
        if not self.check_python_version():
            return False
        
        if option == "help" or option is None:
            self.show_help()
            return True
        
        if not self.create_venv():
            return False
        
        if option == "minimal":
            return self.install_requirements("requirements-minimal.txt")
        elif option == "scraping":
            return self.install_requirements("requirements-scraping.txt")
        elif option == "full":
            return self.install_requirements("requirements.txt")
        elif option == "dev":
            if not self.install_requirements("requirements.txt"):
                return False
            return self.install_requirements("requirements-dev.txt")
        elif option == "test":
            return self.test_setup()
        else:
            print(f"❌ Unknown option: {option}")
            self.show_help()
            return False


def main():
    """Main entry point"""
    setup = TradingBotSetup()
    option = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = setup.run(option)
    
    if success:
        print("\n🎯 Next Steps:")
        if platform.system() != "Windows":
            print("   source trading_bot_env/bin/activate")
        else:
            print("   trading_bot_env\\Scripts\\activate.bat")
        print("   python src/trading_bot/main.py")
    else:
        print("\n❌ Setup failed. Check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
