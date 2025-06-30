"""
Flask Framework HTTP Server Implementation

This module provides a production-ready Flask web application that replaces the
Node.js/Express.js HTTP server functionality while maintaining identical external
API behavior and response characteristics.

Key Features:
- Industry-standard Flask framework patterns with decorator-based routing
- Application factory pattern using create_app() for production-ready deployment
- WSGI compliance for scalable production deployment options
- Comprehensive error handling and logging capabilities
- Environment-based configuration management with python-dotenv support
- Development server with debug mode and hot-reload capabilities
- Performance optimized to meet <100ms response time requirements
- Educational-friendly code structure with comprehensive documentation

Educational Purpose:
This implementation demonstrates modern Python web development practices using
the Flask framework, serving as a high-level comparison to the native Python
HTTP server implementation. It showcases industry-standard patterns including
route decorators, application factories, and WSGI compliance.

Dependencies:
- Flask==2.3.2: Core web framework providing WSGI application and routing
- python-dotenv==1.0.0: Environment variable management for configuration
- config.py: Centralized configuration management module

Usage:
    # Development server (recommended for learning)
    python app.py
    
    # Flask CLI (alternative development approach)
    flask run
    
    # Production deployment (with gunicorn)
    gunicorn app:app

Architecture:
    HTTP Request → Flask Router → View Function → Response Generation → HTTP Response
    
    The Flask application follows WSGI (Web Server Gateway Interface) standards,
    enabling deployment flexibility across various production environments.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Flask framework imports
from flask import Flask, Response, request, jsonify, g
from werkzeug.exceptions import NotFound, InternalServerError, BadRequest

# Import our centralized configuration management
from config import Config


def create_app(config_instance: Optional[Config] = None) -> Flask:
    """
    Application factory function for creating Flask application instances.
    
    This function implements the Flask application factory pattern, which is
    considered best practice for production deployments. It allows for:
    - Multiple application instances with different configurations
    - Testing with isolated application contexts
    - Deferred configuration loading
    - Production deployment flexibility
    
    Args:
        config_instance (Optional[Config]): Pre-configured Config instance.
                                          If None, creates new instance with dotenv loading.
    
    Returns:
        Flask: Configured Flask application instance ready for deployment.
        
    Educational Note:
        The application factory pattern separates application creation from
        configuration, following the principle of separation of concerns.
        This enables better testing, deployment flexibility, and maintainability.
    """
    # Create Flask application instance
    app = Flask(__name__)
    
    # Initialize configuration
    if config_instance is None:
        config_instance = Config(load_dotenv=True)
    
    # Store configuration in Flask app config for access throughout the application
    app.config['HTTP_SERVER_CONFIG'] = config_instance
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Configure Flask-specific settings
    app.config['DEBUG'] = config_instance.get_debug_mode()
    app.config['TESTING'] = False
    app.config['DEVELOPMENT'] = config_instance.get_debug_mode()
    
    # Configure logging based on debug mode
    _configure_logging(app, config_instance)
    
    # Register request/response middleware for performance monitoring
    _register_middleware(app)
    
    # Register application routes
    _register_routes(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Log application startup information
    app.logger.info(f"Flask application created successfully")
    app.logger.info(f"Debug mode: {app.config['DEBUG']}")
    app.logger.info(f"Configuration: {config_instance.get_server_info()}")
    
    return app


def _configure_logging(app: Flask, config: Config) -> None:
    """
    Configure application logging based on debug mode and environment.
    
    Args:
        app (Flask): Flask application instance
        config (Config): Configuration instance
        
    Educational Note:
        Proper logging configuration is essential for production applications.
        This setup provides different logging levels for development vs production.
    """
    if config.get_debug_mode():
        # Development logging: verbose output to console
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        app.logger.setLevel(logging.DEBUG)
    else:
        # Production logging: structured logging with rotation
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        app.logger.setLevel(logging.INFO)


def _register_middleware(app: Flask) -> None:
    """
    Register Flask middleware for request/response processing.
    
    This middleware provides:
    - Request timing for performance monitoring
    - Request ID generation for tracing
    - Response header standardization
    
    Args:
        app (Flask): Flask application instance
        
    Educational Note:
        Middleware functions execute before and after each request,
        providing cross-cutting concerns like logging, authentication, etc.
    """
    
    @app.before_request
    def before_request():
        """
        Execute before each request to set up request context.
        
        This function runs before every request and sets up:
        - Request start time for performance measurement
        - Request ID for debugging and tracing
        - Request logging for development debugging
        """
        # Start performance timer
        g.start_time = time.time()
        
        # Generate request ID for tracing
        g.request_id = f"req_{int(time.time() * 1000)}"
        
        # Log incoming request (debug mode only)
        if app.config.get('DEBUG'):
            app.logger.debug(f"[{g.request_id}] {request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def after_request(response: Response) -> Response:
        """
        Execute after each request to finalize response.
        
        Args:
            response (Response): Flask response object
            
        Returns:
            Response: Modified response with additional headers
            
        Educational Note:
            This middleware adds standard HTTP headers and logs response information.
            It's executed after the view function but before sending to client.
        """
        # Calculate request processing time
        if hasattr(g, 'start_time'):
            processing_time = (time.time() - g.start_time) * 1000  # Convert to milliseconds
            
            # Add performance header for monitoring
            response.headers['X-Response-Time'] = f"{processing_time:.2f}ms"
            
            # Log performance metrics
            if app.config.get('DEBUG'):
                app.logger.debug(f"[{getattr(g, 'request_id', 'unknown')}] "
                               f"Response: {response.status_code} in {processing_time:.2f}ms")
            
            # Performance warning if response time exceeds target
            if processing_time > 100:
                app.logger.warning(f"Slow response: {processing_time:.2f}ms (target: <100ms)")
        
        # Add standard security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Add server identification
        response.headers['Server'] = 'Flask-Python-Educational-Server'
        
        return response


def _register_routes(app: Flask) -> None:
    """
    Register all application routes using Flask's decorator-based routing.
    
    Args:
        app (Flask): Flask application instance
        
    Educational Note:
        Flask uses decorator-based routing (@app.route) which provides clean,
        readable URL-to-function mapping. This is more elegant than manual
        URL parsing in native implementations.
    """
    
    @app.route('/hello', methods=['GET'])
    def hello_endpoint() -> Response:
        """
        Handle GET requests to /hello endpoint.
        
        This endpoint implements the core functionality requirement:
        - Responds to GET requests on /hello path
        - Returns "Hello world" message with 200 status code
        - Maintains response time under 100ms
        - Provides proper HTTP headers and content type
        
        Returns:
            Response: Flask Response object with "Hello world" content
            
        Educational Note:
            Flask view functions return various types (str, dict, Response objects).
            This implementation returns a Response object for explicit control
            over headers and status codes.
        """
        app.logger.debug("Processing /hello endpoint request")
        
        # Create response with explicit content type and status
        response_data = "Hello world"
        
        # Create Flask Response object with explicit configuration
        response = Response(
            response=response_data,
            status=200,
            mimetype='text/plain',
            headers={
                'Content-Type': 'text/plain; charset=utf-8',
                'Cache-Control': 'no-cache',
                'Access-Control-Allow-Origin': '*',  # For educational/testing purposes
            }
        )
        
        app.logger.info(f"Successfully responded to /hello request")
        return response
    
    @app.route('/', methods=['GET'])
    def root_endpoint() -> Response:
        """
        Handle GET requests to root endpoint for basic server information.
        
        This endpoint provides server information and usage instructions,
        useful for development and educational purposes.
        
        Returns:
            Response: JSON response with server information
        """
        config = app.config.get('HTTP_SERVER_CONFIG')
        server_info = {
            'message': 'Flask HTTP Server - Educational Implementation',
            'status': 'running',
            'endpoints': {
                '/hello': 'Returns "Hello world" message',
                '/': 'Server information and usage guide'
            },
            'usage': {
                'hello_endpoint': 'GET /hello',
                'example_curl': 'curl http://localhost:3000/hello'
            },
            'server_info': config.get_server_info() if config else {},
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return jsonify(server_info)
    
    @app.route('/health', methods=['GET'])
    def health_check() -> Response:
        """
        Health check endpoint for monitoring and deployment verification.
        
        Returns:
            Response: JSON response indicating server health status
            
        Educational Note:
            Health check endpoints are standard practice in production applications
            for load balancer health checks and monitoring systems.
        """
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'python_version': sys.version.split()[0],
            'flask_version': Flask.__version__
        })


def _register_error_handlers(app: Flask) -> None:
    """
    Register custom error handlers for various HTTP error conditions.
    
    Args:
        app (Flask): Flask application instance
        
    Educational Note:
        Custom error handlers provide consistent error responses and
        improve user experience by providing meaningful error messages.
    """
    
    @app.errorhandler(404)
    def not_found_error(error) -> Tuple[Response, int]:
        """
        Handle 404 Not Found errors.
        
        Args:
            error: Werkzeug NotFound exception
            
        Returns:
            Tuple[Response, int]: JSON error response with 404 status code
        """
        app.logger.warning(f"404 error: {request.path} not found")
        
        error_response = {
            'error': 'Not Found',
            'message': 'The requested endpoint does not exist',
            'status_code': 404,
            'path': request.path,
            'available_endpoints': ['/hello', '/', '/health'],
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return jsonify(error_response), 404
    
    @app.errorhandler(500)
    def internal_error(error) -> Tuple[Response, int]:
        """
        Handle 500 Internal Server Error conditions.
        
        Args:
            error: Exception that caused the internal server error
            
        Returns:
            Tuple[Response, int]: JSON error response with 500 status code
        """
        app.logger.error(f"Internal server error: {str(error)}")
        
        error_response = {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred while processing your request',
            'status_code': 500,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Only include error details in debug mode
        if app.config.get('DEBUG'):
            error_response['debug_info'] = str(error)
        
        return jsonify(error_response), 500
    
    @app.errorhandler(400)
    def bad_request_error(error) -> Tuple[Response, int]:
        """
        Handle 400 Bad Request errors.
        
        Args:
            error: Werkzeug BadRequest exception
            
        Returns:
            Tuple[Response, int]: JSON error response with 400 status code
        """
        app.logger.warning(f"Bad request: {str(error)}")
        
        error_response = {
            'error': 'Bad Request',
            'message': 'The request could not be understood by the server',
            'status_code': 400,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return jsonify(error_response), 400


def run_development_server(app: Flask, config: Config) -> None:
    """
    Run the Flask development server with proper configuration.
    
    Args:
        app (Flask): Flask application instance
        config (Config): Configuration instance
        
    Educational Note:
        The Flask development server is perfect for learning and development,
        but should not be used in production. Use WSGI servers like Gunicorn
        for production deployment.
    """
    host = config.get_host()
    port = config.get_port()
    debug = config.get_debug_mode()
    
    print("\n" + "="*60)
    print("Flask HTTP Server - Educational Implementation")
    print("="*60)
    print(f"Server running on: http://{host}:{port}")
    print(f"Debug mode: {'Enabled' if debug else 'Disabled'}")
    print(f"Available endpoints:")
    print(f"  GET /hello    - Returns 'Hello world' message")
    print(f"  GET /         - Server information")
    print(f"  GET /health   - Health check endpoint")
    print(f"\nExample usage:")
    print(f"  curl http://{host}:{port}/hello")
    print(f"  curl http://{host}:{port}/")
    print(f"\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    try:
        # Run Flask development server
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,  # Enable auto-reload in debug mode
            use_debugger=debug,  # Enable debugger in debug mode
            threaded=True,       # Enable threading for better performance
            load_dotenv=True     # Load .env files automatically
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nError: Port {port} is already in use.")
            print(f"Please try a different port or stop the service using port {port}.")
            print(f"Available ports: {', '.join(map(str, config.SUPPORTED_PORTS))}")
        else:
            print(f"\nError starting server: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        app.logger.error(f"Server startup error: {e}")


# Create Flask application instance using application factory pattern
app = create_app()


def main():
    """
    Main entry point for the Flask HTTP server application.
    
    This function demonstrates proper Flask application initialization
    and development server execution patterns.
    
    Educational Note:
        This main() function shows how to properly initialize and run
        a Flask application, including configuration management and
        error handling for common startup issues.
    """
    try:
        # Create configuration instance with .env file support
        config = Config(load_dotenv=True)
        
        # Print configuration summary for educational purposes
        if config.get_debug_mode():
            config.print_config_summary()
        
        # Create Flask application using application factory pattern
        flask_app = create_app(config)
        
        # Run development server
        run_development_server(flask_app, config)
        
    except ImportError as e:
        print(f"Import Error: {e}")
        print("Please ensure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting Flask application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()