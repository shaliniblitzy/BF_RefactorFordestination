"""
Configuration Management Module for Python HTTP Server Project

This module provides centralized configuration management for both native Python
and Flask HTTP server implementations, enabling consistent configuration patterns
across the dual implementation approach.

Key Features:
- Environment variable handling with sensible defaults
- Support for .env file loading via python-dotenv
- Cross-platform compatibility (Windows, macOS, Linux)
- Educational-friendly code structure with comprehensive documentation
- Unified configuration interface for both implementations

Dependencies:
- python-dotenv (optional): For .env file support in Flask implementation
- os (built-in): For environment variable access in native implementation

Usage:
    from config import Config
    
    # For Flask implementation
    app_config = Config()
    port = app_config.get_port()
    
    # For native Python implementation
    port = Config.get_port_from_env()
"""

import os
import sys
from typing import Union, Optional, Dict, Any


class Config:
    """
    Centralized configuration management class for HTTP server implementations.
    
    This class provides a unified interface for configuration management across
    both native Python and Flask implementations, handling environment variables,
    default values, and cross-platform compatibility.
    
    Attributes:
        DEFAULT_PORT (int): Default port number if no environment variable is set
        SUPPORTED_PORTS (list): List of supported port numbers for validation
    """
    
    # Default configuration values
    DEFAULT_PORT: int = 3000
    SUPPORTED_PORTS: list = [3000, 8000, 8080]
    
    # Environment variable names
    ENV_PORT: str = "PORT"
    ENV_FLASK_PORT: str = "FLASK_RUN_PORT"
    ENV_DEBUG: str = "DEBUG"
    ENV_HOST: str = "HOST"
    
    # Default values
    DEFAULT_HOST: str = "127.0.0.1"  # localhost for development
    DEFAULT_DEBUG: bool = True
    
    def __init__(self, load_dotenv: bool = True):
        """
        Initialize configuration instance.
        
        Args:
            load_dotenv (bool): Whether to attempt loading .env file.
                                Set to True for Flask implementation,
                                False for native Python implementation.
        """
        self.load_dotenv = load_dotenv
        self._config_cache: Dict[str, Any] = {}
        
        # Attempt to load .env file if requested and python-dotenv is available
        if load_dotenv:
            self._load_environment_file()
    
    def _load_environment_file(self) -> None:
        """
        Load environment variables from .env file using python-dotenv.
        
        This method attempts to import and use python-dotenv to load environment
        variables from a .env file. If python-dotenv is not available, it falls
        back to using only os.environ.
        
        Note:
            This is primarily used by the Flask implementation. The native Python
            implementation can work without python-dotenv dependency.
        """
        try:
            from dotenv import load_dotenv
            
            # Look for .env file in current directory and parent directories
            env_path = self._find_env_file()
            if env_path:
                load_dotenv(env_path)
                print(f"Configuration: Loaded environment variables from {env_path}")
            else:
                # Try to load from default .env location
                load_dotenv()
                print("Configuration: Attempted to load .env file from current directory")
                
        except ImportError:
            print("Configuration: python-dotenv not available, using os.environ only")
            print("Configuration: For Flask implementation, install with: pip install python-dotenv")
    
    def _find_env_file(self) -> Optional[str]:
        """
        Find .env file in current directory or parent directories.
        
        Returns:
            str: Path to .env file if found, None otherwise.
        """
        current_dir = os.getcwd()
        
        # Check current directory and up to 3 parent directories
        for _ in range(4):
            env_path = os.path.join(current_dir, '.env')
            if os.path.isfile(env_path):
                return env_path
            
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # Reached root directory
                break
            current_dir = parent_dir
        
        return None
    
    def get_port(self) -> int:
        """
        Get the configured port number for the HTTP server.
        
        Port resolution priority:
        1. FLASK_RUN_PORT environment variable (Flask-specific)
        2. PORT environment variable (general)
        3. DEFAULT_PORT constant (3000)
        
        Returns:
            int: Port number to bind the HTTP server to.
            
        Raises:
            ValueError: If the configured port is not in SUPPORTED_PORTS list.
        """
        # Check cache first
        if 'port' in self._config_cache:
            return self._config_cache['port']
        
        # Try Flask-specific port first
        port_str = os.getenv(self.ENV_FLASK_PORT)
        if not port_str:
            # Fall back to general PORT environment variable
            port_str = os.getenv(self.ENV_PORT)
        
        if port_str:
            try:
                port = int(port_str)
                if port not in self.SUPPORTED_PORTS:
                    print(f"Warning: Port {port} not in supported ports {self.SUPPORTED_PORTS}")
                    print(f"Supported ports are: {', '.join(map(str, self.SUPPORTED_PORTS))}")
                    print(f"Using port {port} anyway (ensure it's available)")
                
                # Validate port range
                if not (1024 <= port <= 65535):
                    raise ValueError(f"Port {port} is outside valid range (1024-65535)")
                
                self._config_cache['port'] = port
                return port
                
            except ValueError as e:
                print(f"Error: Invalid port value '{port_str}': {e}")
                print(f"Using default port {self.DEFAULT_PORT}")
        
        # Use default port
        self._config_cache['port'] = self.DEFAULT_PORT
        return self.DEFAULT_PORT
    
    def get_host(self) -> str:
        """
        Get the configured host address for the HTTP server.
        
        Returns:
            str: Host address to bind the HTTP server to (default: 127.0.0.1).
        """
        if 'host' in self._config_cache:
            return self._config_cache['host']
        
        host = os.getenv(self.ENV_HOST, self.DEFAULT_HOST)
        self._config_cache['host'] = host
        return host
    
    def get_debug_mode(self) -> bool:
        """
        Get the debug mode setting.
        
        Returns:
            bool: True if debug mode is enabled, False otherwise.
        """
        if 'debug' in self._config_cache:
            return self._config_cache['debug']
        
        debug_str = os.getenv(self.ENV_DEBUG, str(self.DEFAULT_DEBUG)).lower()
        debug = debug_str in ('true', '1', 'yes', 'on', 'enable', 'enabled')
        
        self._config_cache['debug'] = debug
        return debug
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get complete server configuration information.
        
        Returns:
            dict: Dictionary containing all server configuration values.
        """
        return {
            'host': self.get_host(),
            'port': self.get_port(),
            'debug': self.get_debug_mode(),
            'supported_ports': self.SUPPORTED_PORTS,
            'python_version': sys.version,
            'platform': sys.platform
        }
    
    def print_config_summary(self) -> None:
        """
        Print a summary of the current configuration settings.
        
        This method is useful for debugging and educational purposes,
        showing what configuration values are being used.
        """
        config = self.get_server_info()
        
        print("\n" + "="*50)
        print("HTTP Server Configuration Summary")
        print("="*50)
        print(f"Host: {config['host']}")
        print(f"Port: {config['port']}")
        print(f"Debug Mode: {config['debug']}")
        print(f"Supported Ports: {', '.join(map(str, config['supported_ports']))}")
        print(f"Python Version: {config['python_version'].split()[0]}")
        print(f"Platform: {config['platform']}")
        print("="*50 + "\n")
    
    @classmethod
    def get_port_from_env(cls) -> int:
        """
        Static method to get port from environment variables without instantiation.
        
        This method is particularly useful for the native Python implementation
        where you may not want to create a Config instance.
        
        Returns:
            int: Port number from environment variables or default port.
        """
        # Try Flask-specific port first
        port_str = os.getenv(cls.ENV_FLASK_PORT)
        if not port_str:
            # Fall back to general PORT environment variable
            port_str = os.getenv(cls.ENV_PORT)
        
        if port_str:
            try:
                port = int(port_str)
                # Basic validation
                if 1024 <= port <= 65535:
                    return port
                else:
                    print(f"Warning: Port {port} outside valid range, using default")
            except ValueError:
                print(f"Warning: Invalid port value '{port_str}', using default")
        
        return cls.DEFAULT_PORT
    
    @classmethod
    def get_host_from_env(cls) -> str:
        """
        Static method to get host from environment variables without instantiation.
        
        Returns:
            str: Host address from environment variables or default host.
        """
        return os.getenv(cls.ENV_HOST, cls.DEFAULT_HOST)
    
    @classmethod
    def validate_port(cls, port: Union[int, str]) -> bool:
        """
        Validate if a port number is acceptable.
        
        Args:
            port (Union[int, str]): Port number to validate.
            
        Returns:
            bool: True if port is valid, False otherwise.
        """
        try:
            port_int = int(port)
            return 1024 <= port_int <= 65535
        except (ValueError, TypeError):
            return False


def create_env_example() -> str:
    """
    Generate example .env file content.
    
    This function creates an example .env file content string that demonstrates
    how to configure the HTTP server using environment variables.
    
    Returns:
        str: Example .env file content.
    """
    return """# HTTP Server Configuration
# This file contains environment variables for the Python HTTP server project

# Server Port Configuration
# Choose one of the supported ports: 3000, 8000, 8080
PORT=3000

# Flask-specific port (takes precedence over PORT if set)
# FLASK_RUN_PORT=3000

# Host Configuration
# Use 127.0.0.1 for localhost, 0.0.0.0 for all interfaces
HOST=127.0.0.1

# Debug Mode
# Set to true/false, 1/0, yes/no, on/off, enable/disable
DEBUG=true

# Development vs Production
# ENVIRONMENT=development

# Optional: Flask-specific configuration
# FLASK_APP=app.py
# FLASK_DEBUG=1
"""


def main():
    """
    Demonstration and testing function for the configuration module.
    
    This function demonstrates how to use the Config class and prints
    configuration information. It's useful for testing and educational purposes.
    """
    print("Python HTTP Server - Configuration Module Demo")
    print("=" * 60)
    
    # Test native Python approach (without python-dotenv)
    print("\n1. Native Python Configuration (without python-dotenv):")
    port_native = Config.get_port_from_env()
    host_native = Config.get_host_from_env()
    print(f"   Port: {port_native}")
    print(f"   Host: {host_native}")
    
    # Test Flask approach (with python-dotenv)
    print("\n2. Flask Configuration (with python-dotenv support):")
    config_flask = Config(load_dotenv=True)
    config_flask.print_config_summary()
    
    # Test configuration without dotenv loading
    print("3. Configuration without .env file loading:")
    config_minimal = Config(load_dotenv=False)
    minimal_info = config_minimal.get_server_info()
    print(f"   Host: {minimal_info['host']}")
    print(f"   Port: {minimal_info['port']}")
    print(f"   Debug: {minimal_info['debug']}")
    
    # Test port validation
    print("\n4. Port Validation Examples:")
    test_ports = [3000, 8080, 80, 65536, "invalid", 99999]
    for test_port in test_ports:
        is_valid = Config.validate_port(test_port)
        print(f"   Port {test_port}: {'Valid' if is_valid else 'Invalid'}")
    
    # Generate example .env file content
    print("\n5. Example .env file content:")
    print("-" * 40)
    print(create_env_example())


if __name__ == "__main__":
    main()