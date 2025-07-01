"""
Native Python HTTP Server Implementation

This module implements a basic HTTP server using Python's built-in http.server module,
demonstrating low-level HTTP protocol handling without framework abstractions. The server
provides educational value by showing fundamental Python HTTP server concepts through
direct request/response cycle management.

Key Features:
- Native Python http.server.HTTPServer with custom BaseHTTPRequestHandler
- GET /hello endpoint returning "Hello world" response
- Configurable port binding (3000, 8000, 8080) via environment variables
- Zero external dependencies beyond Python standard library
- Cross-platform compatibility (Windows, macOS, Linux)
- Educational-friendly code structure with comprehensive documentation

Architecture:
- HTTPServer: Handles network binding and connection management
- CustomHTTPRequestHandler: Processes individual HTTP requests
- Manual routing through do_GET() method implementation
- Direct HTTP response generation using self.send_response() and self.wfile.write()

Performance Characteristics:
- Target response time: <100ms for GET /hello requests
- Memory footprint: ~15-20MB (Python runtime only)
- Concurrent connections: Limited by single-threaded processing model
- Startup time: <1 second (direct HTTPServer instantiation)

Usage:
    python server.py
    
    # With custom port via environment variable
    PORT=8080 python server.py
    
    # Test the server
    curl http://localhost:3000/hello

Dependencies:
- config.py: Centralized configuration management
- Python 3.8+: Required for modern syntax and performance optimizations
"""

import http.server
import socketserver
import sys
import os
import signal
import threading
import time
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, Tuple

# Import configuration management from config.py
try:
    from config import Config
except ImportError as e:
    print(f"Error: Unable to import configuration module: {e}")
    print("Please ensure config.py is available in the same directory")
    sys.exit(1)


class CustomHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    Custom HTTP request handler implementing the /hello endpoint.
    
    This class extends BaseHTTPRequestHandler to provide specific handling
    for the educational HTTP server requirements. It demonstrates manual
    HTTP request processing, routing logic, and response generation without
    framework abstractions.
    
    Key Methods:
    - do_GET(): Handles HTTP GET requests with manual routing
    - send_hello_response(): Generates "Hello world" response
    - send_not_found_response(): Handles 404 errors for undefined paths
    - send_error_response(): Manages server errors with appropriate HTTP codes
    
    Educational Value:
    - Direct manipulation of HTTP headers and response bodies
    - Manual URL parsing and routing logic
    - Explicit status code management
    - Raw socket writing through self.wfile
    """
    
    # Server information for response headers
    server_version = "Python-Native-HTTP-Server/1.0"
    sys_version = ""  # Suppress default Python version in Server header
    
    def log_message(self, format: str, *args) -> None:
        """
        Override default logging to provide more educational information.
        
        This method customizes the request logging to show educational details
        about HTTP request processing, including timestamps, request methods,
        and response status codes.
        
        Args:
            format (str): Log message format string
            *args: Variable arguments for format string
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        client_ip = self.address_string()
        
        # Extract method and path from the format string and args
        if args:
            request_info = args[0] if args else "Unknown request"
            status_info = args[1] if len(args) > 1 else "Unknown status"
            
            print(f"[{timestamp}] {client_ip} - {request_info} - Status: {status_info}")
        else:
            print(f"[{timestamp}] {client_ip} - {format}")
    
    def do_GET(self) -> None:
        """
        Handle HTTP GET requests with manual routing logic.
        
        This method demonstrates fundamental HTTP request processing by:
        1. Parsing the request URL and extracting the path
        2. Implementing manual routing logic for defined endpoints
        3. Generating appropriate responses based on the requested path
        4. Managing error conditions with proper HTTP status codes
        
        Supported Endpoints:
        - GET /hello: Returns "Hello world" with 200 status
        - All other paths: Returns 404 Not Found
        
        Educational Concepts Demonstrated:
        - URL parsing using urllib.parse.urlparse()
        - Manual routing through conditional logic
        - HTTP status code management
        - Response header configuration
        - Content-Type specification
        """
        try:
            # Parse the request URL to extract path and query parameters
            parsed_url = urlparse(self.path)
            request_path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # Log the incoming request for educational visibility
            print(f"Processing GET request: {request_path}")
            if query_params:
                print(f"Query parameters: {query_params}")
            
            # Manual routing logic - educational demonstration of endpoint handling
            if request_path == "/hello":
                self._handle_hello_endpoint(query_params)
            elif request_path == "/":
                self._handle_root_endpoint()
            elif request_path == "/health":
                self._handle_health_endpoint()
            else:
                self._handle_not_found(request_path)
                
        except Exception as e:
            # Comprehensive error handling with educational logging
            print(f"Error processing GET request: {e}")
            self._send_error_response(500, "Internal Server Error", str(e))
    
    def _handle_hello_endpoint(self, query_params: Dict[str, list]) -> None:
        """
        Handle the /hello endpoint - core educational demonstration.
        
        This method implements the primary requirement of returning "Hello world"
        response, demonstrating proper HTTP response construction including:
        - Status code setting (200 OK)
        - Content-Type header specification
        - Response body writing to socket
        - Proper connection termination
        
        Args:
            query_params (Dict[str, list]): Parsed query parameters from URL
            
        Educational Value:
        - Direct HTTP response construction
        - Socket-level writing operations
        - Header management and HTTP protocol compliance
        """
        try:
            # Prepare the response content
            response_content = "Hello world"
            
            # Optional: Demonstrate query parameter handling for educational purposes
            if query_params:
                name = query_params.get('name', ['world'])[0]
                response_content = f"Hello {name}"
                print(f"Personalized greeting requested: {name}")
            
            # Send HTTP status line and headers
            self.send_response(200)  # HTTP 200 OK status
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(response_content.encode('utf-8'))))
            self.send_header('Server', self.server_version)
            self.send_header('Connection', 'close')
            self.end_headers()
            
            # Write response body to socket
            self.wfile.write(response_content.encode('utf-8'))
            
            print(f"Successfully sent hello response: '{response_content}'")
            
        except Exception as e:
            print(f"Error in hello endpoint handler: {e}")
            self._send_error_response(500, "Internal Server Error", 
                                    "Failed to generate hello response")
    
    def _handle_root_endpoint(self) -> None:
        """
        Handle requests to the root path (/) - educational server information.
        
        This method provides helpful information about the educational server,
        including available endpoints and usage instructions. This demonstrates
        how to create informational endpoints in native Python HTTP servers.
        """
        try:
            response_content = """Python Native HTTP Server - Educational Implementation

Available Endpoints:
- GET /hello - Returns "Hello world" response (primary educational endpoint)
- GET /hello?name=YourName - Returns personalized greeting
- GET / - This information page
- GET /health - Server health check

Server Information:
- Implementation: Native Python http.server module
- Purpose: Educational demonstration of HTTP server concepts
- Features: Manual routing, direct socket operations, zero external dependencies

Usage Examples:
- curl http://localhost:{}/hello
- curl http://localhost:{}/hello?name=Student
- curl http://localhost:{}/health

Educational Focus:
This server demonstrates fundamental HTTP server concepts using Python's
built-in capabilities without framework abstractions.
""".format(self.server.server_port, self.server.server_port, self.server.server_port)
            
            # Send HTTP response
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(response_content.encode('utf-8'))))
            self.send_header('Server', self.server_version)
            self.end_headers()
            
            self.wfile.write(response_content.encode('utf-8'))
            print("Sent server information response")
            
        except Exception as e:
            print(f"Error in root endpoint handler: {e}")
            self._send_error_response(500, "Internal Server Error", 
                                    "Failed to generate server information")
    
    def _handle_health_endpoint(self) -> None:
        """
        Handle health check endpoint - demonstrates JSON response generation.
        
        This method shows how to generate JSON responses in native Python
        HTTP servers, providing server status and configuration information.
        """
        try:
            import json
            
            # Gather server health information
            health_data = {
                "status": "healthy",
                "server": "Python Native HTTP Server",
                "version": "1.0",
                "port": self.server.server_port,
                "endpoints": ["/hello", "/", "/health"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            }
            
            response_content = json.dumps(health_data, indent=2)
            
            # Send JSON response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(response_content.encode('utf-8'))))
            self.send_header('Server', self.server_version)
            self.end_headers()
            
            self.wfile.write(response_content.encode('utf-8'))
            print("Sent health check response")
            
        except Exception as e:
            print(f"Error in health endpoint handler: {e}")
            self._send_error_response(500, "Internal Server Error", 
                                    "Failed to generate health response")
    
    def _handle_not_found(self, request_path: str) -> None:
        """
        Handle requests to undefined endpoints with 404 Not Found.
        
        This method demonstrates proper error handling for undefined routes,
        showing how to generate appropriate HTTP error responses with helpful
        information for educational purposes.
        
        Args:
            request_path (str): The requested path that was not found
        """
        try:
            response_content = f"""404 - Not Found

The requested path '{request_path}' was not found on this server.

Available endpoints:
- GET /hello - Returns "Hello world" response
- GET / - Server information
- GET /health - Health check

Educational Note:
This 404 response is generated by the native Python HTTP server's
manual routing logic in the do_GET() method.
"""
            
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(response_content.encode('utf-8'))))
            self.send_header('Server', self.server_version)
            self.end_headers()
            
            self.wfile.write(response_content.encode('utf-8'))
            print(f"Sent 404 response for path: {request_path}")
            
        except Exception as e:
            print(f"Error generating 404 response: {e}")
            # Fallback to basic error response
            self._send_error_response(404, "Not Found", f"Path not found: {request_path}")
    
    def _send_error_response(self, status_code: int, status_message: str, 
                           error_details: str) -> None:
        """
        Send standardized error responses for server errors.
        
        This method centralizes error response generation, ensuring consistent
        error handling across all endpoints. It demonstrates proper HTTP error
        response formatting and logging for educational purposes.
        
        Args:
            status_code (int): HTTP status code (e.g., 500, 404)
            status_message (str): HTTP status message (e.g., "Internal Server Error")
            error_details (str): Detailed error information for debugging
        """
        try:
            response_content = f"""{status_code} - {status_message}

Error Details: {error_details}

Educational Note:
This error response is generated by the native Python HTTP server's
error handling system, demonstrating proper HTTP error response patterns.
"""
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(response_content.encode('utf-8'))))
            self.send_header('Server', self.server_version)
            self.end_headers()
            
            self.wfile.write(response_content.encode('utf-8'))
            print(f"Sent {status_code} error response: {error_details}")
            
        except Exception as e:
            print(f"Critical error: Unable to send error response: {e}")
            # Last resort - try to send minimal response
            try:
                self.send_response(status_code)
                self.end_headers()
                self.wfile.write(f"{status_code} {status_message}".encode('utf-8'))
            except:
                print("Critical failure: Unable to send any error response")


class EducationalHTTPServer(socketserver.TCPServer):
    """
    Enhanced HTTP server with educational features and improved error handling.
    
    This class extends the basic TCPServer to provide educational enhancements
    including graceful shutdown handling, configuration management, and
    comprehensive logging for learning purposes.
    
    Features:
    - Graceful shutdown with signal handling
    - Configuration integration with config.py
    - Enhanced error logging and recovery
    - Cross-platform compatibility
    - Educational status reporting
    """
    
    allow_reuse_address = True  # Allow immediate restart after shutdown
    
    def __init__(self, server_address: Tuple[str, int], 
                 RequestHandlerClass, bind_and_activate: bool = True):
        """
        Initialize the educational HTTP server.
        
        Args:
            server_address (Tuple[str, int]): Host and port tuple
            RequestHandlerClass: Request handler class to use
            bind_and_activate (bool): Whether to bind and activate immediately
        """
        self.startup_time = time.time()
        self.request_count = 0
        
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        
        print(f"Educational HTTP Server initialized on {server_address[0]}:{server_address[1]}")
    
    def handle_request(self) -> None:
        """
        Override to add request counting for educational statistics.
        """
        self.request_count += 1
        super().handle_request()
    
    def get_server_stats(self) -> Dict[str, Any]:
        """
        Get server statistics for educational purposes.
        
        Returns:
            Dict[str, Any]: Server statistics including uptime and request count
        """
        uptime = time.time() - self.startup_time
        return {
            "uptime_seconds": round(uptime, 2),
            "requests_handled": self.request_count,
            "server_address": f"{self.server_address[0]}:{self.server_address[1]}",
            "handler_class": self.RequestHandlerClass.__name__
        }


def create_http_server(host: str, port: int) -> EducationalHTTPServer:
    """
    Create and configure the native Python HTTP server.
    
    This function demonstrates server instantiation and configuration,
    showing how to combine Python's http.server components with custom
    request handlers for educational HTTP server implementation.
    
    Args:
        host (str): Host address to bind the server to (e.g., '127.0.0.1')
        port (int): Port number to bind the server to (e.g., 3000)
        
    Returns:
        EducationalHTTPServer: Configured HTTP server instance
        
    Raises:
        OSError: If the port is already in use or binding fails
        ValueError: If the host or port values are invalid
        
    Educational Value:
    - Demonstrates server instantiation patterns
    - Shows proper error handling for network binding
    - Illustrates configuration parameter validation
    """
    try:
        # Validate input parameters
        if not isinstance(host, str) or not host.strip():
            raise ValueError(f"Invalid host address: {host}")
        
        if not isinstance(port, int) or not (1024 <= port <= 65535):
            raise ValueError(f"Invalid port number: {port} (must be 1024-65535)")
        
        print(f"Creating HTTP server on {host}:{port}")
        
        # Create server instance with custom handler
        server = EducationalHTTPServer((host, port), CustomHTTPRequestHandler)
        
        print(f"Server created successfully on {host}:{port}")
        print(f"Handler class: {CustomHTTPRequestHandler.__name__}")
        
        return server
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {port} is already in use")
            print(f"Try using a different port or stop the process using port {port}")
        else:
            print(f"Network error creating server: {e}")
        raise
    
    except Exception as e:
        print(f"Unexpected error creating server: {e}")
        raise


def setup_signal_handlers(server: EducationalHTTPServer) -> None:
    """
    Setup signal handlers for graceful server shutdown.
    
    This function demonstrates proper signal handling for HTTP servers,
    enabling graceful shutdown on SIGINT (Ctrl+C) and SIGTERM signals.
    This is important for educational purposes to show proper server
    lifecycle management.
    
    Args:
        server (EducationalHTTPServer): Server instance to manage
        
    Educational Concepts:
    - Signal handling in Python applications
    - Graceful server shutdown patterns
    - Cross-platform compatibility considerations
    """
    def signal_handler(signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        signal_name = signal.Signals(signum).name
        print(f"\nReceived {signal_name} signal - shutting down gracefully...")
        
        # Display server statistics before shutdown
        stats = server.get_server_stats()
        print("\nServer Statistics:")
        print(f"  Uptime: {stats['uptime_seconds']} seconds")
        print(f"  Total requests handled: {stats['requests_handled']}")
        print(f"  Server address: {stats['server_address']}")
        
        print("Educational HTTP Server shutdown complete.")
        server.shutdown()
    
    # Register signal handlers (cross-platform compatibility)
    try:
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
        
        print("Signal handlers registered for graceful shutdown")
        print("Press Ctrl+C to stop the server")
        
    except Exception as e:
        print(f"Warning: Could not register signal handlers: {e}")
        print("Server will still run, but graceful shutdown may not work")


def print_server_startup_info(config: Config, server: EducationalHTTPServer) -> None:
    """
    Print comprehensive server startup information for educational purposes.
    
    This function displays detailed information about the server configuration,
    available endpoints, and usage instructions. This enhances the educational
    value by providing clear guidance on how to interact with the server.
    
    Args:
        config (Config): Configuration instance with server settings
        server (EducationalHTTPServer): Server instance
    """
    server_info = config.get_server_info()
    
    print("\n" + "="*60)
    print("PYTHON NATIVE HTTP SERVER - EDUCATIONAL IMPLEMENTATION")
    print("="*60)
    print(f"Server Address: http://{server_info['host']}:{server_info['port']}")
    print(f"Server Type: Native Python http.server implementation")
    print(f"Handler Class: {CustomHTTPRequestHandler.__name__}")
    print(f"Python Version: {server_info['python_version'].split()[0]}")
    print(f"Platform: {server_info['platform']}")
    print(f"Debug Mode: {server_info['debug']}")
    
    print("\nAVAILABLE ENDPOINTS:")
    print(f"  GET http://{server_info['host']}:{server_info['port']}/hello")
    print(f"      → Returns: 'Hello world' (primary educational endpoint)")
    print(f"  GET http://{server_info['host']}:{server_info['port']}/hello?name=YourName")
    print(f"      → Returns: 'Hello YourName' (personalized greeting)")
    print(f"  GET http://{server_info['host']}:{server_info['port']}/")
    print(f"      → Returns: Server information and usage guide")
    print(f"  GET http://{server_info['host']}:{server_info['port']}/health")
    print(f"      → Returns: JSON health check response")
    
    print("\nTEST COMMANDS:")
    print(f"  curl http://{server_info['host']}:{server_info['port']}/hello")
    print(f"  curl http://{server_info['host']}:{server_info['port']}/hello?name=Student")
    print(f"  curl http://{server_info['host']}:{server_info['port']}/health")
    
    print("\nEDUCATIONAL FEATURES:")
    print("  ✓ Manual HTTP request/response handling")
    print("  ✓ Direct socket operations (self.wfile.write)")
    print("  ✓ Custom routing logic in do_GET() method")
    print("  ✓ Comprehensive error handling and logging")
    print("  ✓ Zero external dependencies (Python standard library only)")
    print("  ✓ Cross-platform compatibility")
    
    print("\nARCHITECTURE HIGHLIGHTS:")
    print("  • BaseHTTPRequestHandler inheritance pattern")
    print("  • Manual URL parsing and routing")
    print("  • Direct HTTP protocol implementation")
    print("  • Signal-based graceful shutdown")
    
    print("\nCONFIGURATION:")
    print(f"  Supported Ports: {', '.join(map(str, server_info['supported_ports']))}")
    print(f"  Current Port: {server_info['port']}")
    print(f"  Host Binding: {server_info['host']}")
    print(f"  Environment Variables: PORT, HOST, DEBUG")
    
    print("="*60)
    print("Server is running... (Press Ctrl+C to stop)")
    print("="*60 + "\n")


def run_server() -> None:
    """
    Main server execution function with comprehensive setup and error handling.
    
    This function orchestrates the complete server lifecycle including:
    - Configuration loading and validation
    - Server creation and binding
    - Signal handler setup
    - Request serving loop
    - Graceful shutdown handling
    
    Educational Value:
    - Demonstrates complete server application structure
    - Shows proper error handling and recovery patterns
    - Illustrates configuration management integration
    - Provides comprehensive logging for learning purposes
    """
    server = None
    
    try:
        print("Starting Python Native HTTP Server...")
        print("Educational Implementation - http.server module demonstration")
        
        # Load configuration using config.py (native approach without dotenv)
        print("Loading server configuration...")
        config = Config(load_dotenv=False)  # Native Python implementation
        
        # Get server binding configuration
        host = config.get_host()
        port = config.get_port()
        
        print(f"Configuration loaded: {host}:{port}")
        
        # Create and configure the HTTP server
        server = create_http_server(host, port)
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(server)
        
        # Display comprehensive startup information
        print_server_startup_info(config, server)
        
        # Start the server in a separate thread to allow for signal handling
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        
        print("HTTP server started successfully!")
        print(f"Listening on http://{host}:{port}")
        print(f"Test the server: curl http://{host}:{port}/hello")
        
        # Keep the main thread alive to handle signals
        try:
            while server_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received - initiating shutdown...")
        
    except KeyboardInterrupt:
        print("\nKeyboard interrupt - shutting down server...")
    
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nError: Unable to bind to port {port if 'port' in locals() else 'unknown'}")
            print("The port is already in use. Try:")
            print(f"  1. Use a different port: PORT=8080 python server.py")
            print(f"  2. Stop the process using the port")
            print(f"  3. Wait a moment and try again")
        else:
            print(f"\nNetwork error: {e}")
            print("Check your network configuration and try again")
    
    except ImportError as e:
        print(f"\nConfiguration Error: {e}")
        print("Ensure config.py is available in the same directory")
    
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Check the error details above and ensure proper Python 3.8+ installation")
        import traceback
        traceback.print_exc()
    
    finally:
        # Ensure server is properly shut down
        if server:
            try:
                server.shutdown()
                server.server_close()
                print("Server resources cleaned up successfully")
            except Exception as e:
                print(f"Error during server cleanup: {e}")
        
        print("\nPython Native HTTP Server stopped.")
        print("Thank you for exploring native Python HTTP server implementation!")


def main() -> None:
    """
    Main entry point for the educational HTTP server application.
    
    This function serves as the primary entry point, providing a clean
    interface for server execution. It includes basic environment validation
    and delegates to the run_server() function for the main server logic.
    
    Educational Purpose:
    - Demonstrates proper Python application entry point patterns
    - Shows environment validation and error handling
    - Provides clear separation between main logic and execution control
    """
    print("Python Native HTTP Server - Educational Implementation")
    print("Using Python built-in http.server module")
    print(f"Python version: {sys.version}")
    print("-" * 50)
    
    # Basic environment validation
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    
    # Run the server
    run_server()


if __name__ == "__main__":
    main()