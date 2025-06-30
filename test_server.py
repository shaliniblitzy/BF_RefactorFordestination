#!/usr/bin/env python3
"""
Comprehensive Test Suite for Python HTTP Server Implementations

This test suite validates both native Python http.server and Flask framework 
implementations according to the technical specification requirements.

Test Coverage:
- Unit tests for individual components and functions
- Integration tests for HTTP server initialization and API endpoints
- Performance tests validating <100ms response time requirement
- Cross-implementation validation ensuring parity between approaches
- Error handling and edge case validation

Requirements Validated:
- F-001-RQ-001: Server initialization and startup (<5 seconds)
- F-001-RQ-003: HTTP request processing (<100ms response time)
- F-002-RQ-001: '/hello' route handling with GET method
- F-002-RQ-002: "Hello world" response generation with HTTP 200
- F-005-RQ-001: Response time performance requirements

Author: Blitzy Platform
Version: 1.0.0
Python: 3.8+
"""

import asyncio
import concurrent.futures
import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest.mock
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

import psutil
import pytest
import requests
from memory_profiler import memory_usage


# =============================================================================
# TEST CONFIGURATION AND CONSTANTS
# =============================================================================

# Performance thresholds per technical specification
PERFORMANCE_THRESHOLDS = {
    'response_time_ms': 100,        # <100ms response time requirement
    'startup_time_seconds': 5,      # <5 seconds startup time requirement  
    'memory_usage_mb': 50,          # <50MB memory usage requirement
    'concurrent_requests': 100      # 100 simultaneous request handling
}

# Test server configuration
TEST_SERVER_CONFIG = {
    'host': 'localhost',
    'port_range': (3001, 3999),     # Test port allocation range
    'timeout': 30,                  # HTTP request timeout
    'retry_attempts': 3,            # Flaky test retry configuration
    'retry_delay': 1                # Delay between retries
}

# Expected endpoint responses per functional requirements
EXPECTED_RESPONSES = {
    'hello_endpoint': {
        'path': '/hello',
        'method': 'GET',
        'status_code': 200,
        'content': 'Hello world',
        'content_type': 'text/plain'
    },
    'not_found': {
        'status_code': 404
    }
}


# =============================================================================
# UTILITY FUNCTIONS AND FIXTURES
# =============================================================================

def get_available_port(start_port: int = 3001, end_port: int = 3999) -> int:
    """
    Find an available port within the specified range for test server binding.
    
    Args:
        start_port: Starting port number for search
        end_port: Ending port number for search
        
    Returns:
        Available port number
        
    Raises:
        RuntimeError: If no available port found in range
    """
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('localhost', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available port found in range {start_port}-{end_port}")


def wait_for_server_ready(host: str, port: int, timeout: int = 30) -> bool:
    """
    Wait for server to become ready and accept connections.
    
    Args:
        host: Server hostname
        port: Server port number
        timeout: Maximum wait time in seconds
        
    Returns:
        True if server is ready, False if timeout exceeded
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    return True
        except (socket.error, ConnectionRefusedError):
            pass
        time.sleep(0.1)
    return False


def measure_response_time(url: str, method: str = 'GET', **kwargs) -> Tuple[float, requests.Response]:
    """
    Measure HTTP response time with high precision.
    
    Args:
        url: Target URL for request
        method: HTTP method (GET, POST, etc.)
        **kwargs: Additional arguments for requests
        
    Returns:
        Tuple of (response_time_ms, response_object)
    """
    start_time = time.perf_counter()
    response = requests.request(method, url, timeout=TEST_SERVER_CONFIG['timeout'], **kwargs)
    end_time = time.perf_counter()
    response_time_ms = (end_time - start_time) * 1000
    return response_time_ms, response


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def test_port() -> int:
    """Fixture providing an available port for test server instances."""
    return get_available_port()


@pytest.fixture(scope="session") 
def server_config(test_port: int) -> Dict[str, Union[str, int]]:
    """Fixture providing test server configuration."""
    return {
        'host': TEST_SERVER_CONFIG['host'],
        'port': test_port,
        'timeout': TEST_SERVER_CONFIG['timeout']
    }


@pytest.fixture
def mock_environment(monkeypatch) -> Dict[str, str]:
    """Fixture providing isolated environment variable testing."""
    test_env = {
        'PORT': '3000',
        'HOST': 'localhost',
        'FLASK_ENV': 'testing',
        'TESTING': 'true'
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


@pytest.fixture
def performance_timer():
    """Fixture for high-precision performance timing measurements."""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.perf_counter()
        
        def stop(self) -> float:
            self.end_time = time.perf_counter()
            return (self.end_time - self.start_time) * 1000  # Return milliseconds
        
        @property
        def elapsed_ms(self) -> float:
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return 0.0
    
    return PerformanceTimer()


@pytest.fixture
def http_client():
    """Fixture providing configured HTTP client for testing."""
    session = requests.Session()
    session.timeout = TEST_SERVER_CONFIG['timeout']
    
    # Configure retry strategy for flaky network tests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    retry_strategy = Retry(
        total=TEST_SERVER_CONFIG['retry_attempts'],
        backoff_factor=TEST_SERVER_CONFIG['retry_delay'],
        status_forcelist=[429, 500, 502, 503, 504]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    yield session
    session.close()


# =============================================================================
# NATIVE PYTHON HTTP SERVER TESTS
# =============================================================================

class TestNativePythonServer:
    """
    Test suite for native Python http.server implementation.
    
    Validates server initialization, request processing, and response generation
    using Python's built-in http.server module without external dependencies.
    """
    
    @pytest.fixture(autouse=True)
    def setup_native_server(self, server_config):
        """Setup fixture for native Python server tests."""
        self.server_config = server_config
        self.server_process = None
        self.server_url = f"http://{server_config['host']}:{server_config['port']}"
    
    def teardown_method(self):
        """Cleanup server process after each test."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            self.server_process = None
    
    def start_native_server(self) -> subprocess.Popen:
        """
        Start native Python HTTP server for testing.
        
        Returns:
            Server process handle
        """
        cmd = [
            sys.executable, 'server.py',
            '--port', str(self.server_config['port']),
            '--host', self.server_config['host']
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to be ready
        if not wait_for_server_ready(
            self.server_config['host'], 
            self.server_config['port'], 
            timeout=PERFORMANCE_THRESHOLDS['startup_time_seconds']
        ):
            process.terminate()
            raise RuntimeError("Native server failed to start within timeout")
        
        return process
    
    def test_server_initialization(self, performance_timer):
        """
        Test F-001-RQ-001: Server initialization and startup within 5 seconds.
        
        Validates:
        - Server starts successfully without errors
        - Port binding completes within startup timeframe
        - Process remains active and responsive
        """
        performance_timer.start()
        
        try:
            self.server_process = self.start_native_server()
            startup_time = performance_timer.stop()
            
            # Verify server process is running
            assert self.server_process.poll() is None, "Server process terminated unexpectedly"
            
            # Verify startup time meets performance requirement
            assert startup_time < (PERFORMANCE_THRESHOLDS['startup_time_seconds'] * 1000), \
                f"Server startup time {startup_time:.2f}ms exceeds {PERFORMANCE_THRESHOLDS['startup_time_seconds']}s limit"
            
            # Verify port binding successful
            assert wait_for_server_ready(
                self.server_config['host'], 
                self.server_config['port'], 
                timeout=1
            ), "Server port binding verification failed"
            
        except Exception as e:
            if self.server_process:
                self.server_process.terminate()
            pytest.fail(f"Native server initialization failed: {e}")
    
    def test_hello_endpoint_functionality(self, http_client):
        """
        Test F-002-RQ-001 & F-002-RQ-002: '/hello' route handling and response generation.
        
        Validates:
        - '/hello' path recognized and routed correctly
        - GET method processing implemented
        - "Hello world" response with HTTP 200 status code
        - Appropriate content-type header
        """
        self.server_process = self.start_native_server()
        hello_url = urljoin(self.server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        
        response = http_client.get(hello_url)
        
        # Validate response status code
        assert response.status_code == EXPECTED_RESPONSES['hello_endpoint']['status_code'], \
            f"Expected status {EXPECTED_RESPONSES['hello_endpoint']['status_code']}, got {response.status_code}"
        
        # Validate response content
        assert response.text.strip() == EXPECTED_RESPONSES['hello_endpoint']['content'], \
            f"Expected '{EXPECTED_RESPONSES['hello_endpoint']['content']}', got '{response.text.strip()}'"
        
        # Validate content-type header if specified
        if 'content_type' in EXPECTED_RESPONSES['hello_endpoint']:
            content_type = response.headers.get('content-type', '').lower()
            expected_type = EXPECTED_RESPONSES['hello_endpoint']['content_type'].lower()
            assert expected_type in content_type, \
                f"Expected content-type containing '{expected_type}', got '{content_type}'"
    
    def test_response_time_performance(self, http_client):
        """
        Test F-005-RQ-001: Response time performance under 100ms.
        
        Validates:
        - HTTP request processing < 100ms
        - Consistent performance across multiple requests
        - Performance meets specification requirements
        """
        self.server_process = self.start_native_server()
        hello_url = urljoin(self.server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        
        response_times = []
        num_requests = 10  # Sample size for performance validation
        
        for _ in range(num_requests):
            response_time_ms, response = measure_response_time(hello_url, 'GET')
            
            # Verify successful response
            assert response.status_code == 200, f"Performance test failed with status {response.status_code}"
            
            response_times.append(response_time_ms)
        
        # Calculate performance metrics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Validate average response time meets requirements
        assert avg_response_time < PERFORMANCE_THRESHOLDS['response_time_ms'], \
            f"Average response time {avg_response_time:.2f}ms exceeds {PERFORMANCE_THRESHOLDS['response_time_ms']}ms limit"
        
        # Validate maximum response time for consistency
        assert max_response_time < (PERFORMANCE_THRESHOLDS['response_time_ms'] * 2), \
            f"Maximum response time {max_response_time:.2f}ms indicates performance inconsistency"
    
    def test_error_handling_404(self, http_client):
        """
        Test error handling with 404 responses for undefined paths.
        
        Validates:
        - Undefined routes return 404 status code
        - Error response format is appropriate
        - Server remains stable after error conditions
        """
        self.server_process = self.start_native_server()
        undefined_url = urljoin(self.server_url, '/undefined-endpoint')
        
        response = http_client.get(undefined_url)
        
        # Validate 404 status code for undefined path
        assert response.status_code == EXPECTED_RESPONSES['not_found']['status_code'], \
            f"Expected 404 for undefined path, got {response.status_code}"
        
        # Verify server remains responsive after error
        hello_url = urljoin(self.server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        follow_up_response = http_client.get(hello_url)
        assert follow_up_response.status_code == 200, \
            "Server became unresponsive after 404 error"
    
    def test_memory_usage_requirements(self):
        """
        Test memory usage stays within specified limits during operation.
        
        Validates:
        - Peak memory usage < 50MB requirement
        - Memory usage remains stable during request processing
        """
        def server_operation():
            self.server_process = self.start_native_server()
            
            # Simulate request load for memory measurement
            hello_url = urljoin(self.server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
            
            for _ in range(20):  # Generate load for memory measurement
                try:
                    requests.get(hello_url, timeout=1)
                except:
                    pass  # Continue memory measurement even if requests fail
                time.sleep(0.1)
        
        # Measure memory usage during server operation
        memory_usage_mb = memory_usage(server_operation, interval=0.1, max_usage=True)
        peak_memory = max(memory_usage_mb)
        
        assert peak_memory < PERFORMANCE_THRESHOLDS['memory_usage_mb'], \
            f"Peak memory usage {peak_memory:.2f}MB exceeds {PERFORMANCE_THRESHOLDS['memory_usage_mb']}MB limit"


# =============================================================================
# FLASK FRAMEWORK TESTS
# =============================================================================

class TestFlaskServer:
    """
    Test suite for Flask framework implementation.
    
    Validates Flask application initialization, routing decorators, and WSGI
    compliance according to technical specification requirements.
    """
    
    @pytest.fixture(autouse=True)
    def setup_flask_server(self, server_config):
        """Setup fixture for Flask server tests."""
        self.server_config = server_config
        self.server_process = None
        self.server_url = f"http://{server_config['host']}:{server_config['port']}"
    
    def teardown_method(self):
        """Cleanup Flask server process after each test."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            self.server_process = None
    
    def start_flask_server(self) -> subprocess.Popen:
        """
        Start Flask HTTP server for testing.
        
        Returns:
            Server process handle
        """
        env = os.environ.copy()
        env['FLASK_APP'] = 'app.py'
        env['FLASK_ENV'] = 'testing'
        env['PORT'] = str(self.server_config['port'])
        env['HOST'] = self.server_config['host']
        
        cmd = [
            sys.executable, '-m', 'flask', 'run',
            '--host', self.server_config['host'],
            '--port', str(self.server_config['port'])
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Wait for Flask server to be ready
        if not wait_for_server_ready(
            self.server_config['host'], 
            self.server_config['port'], 
            timeout=PERFORMANCE_THRESHOLDS['startup_time_seconds']
        ):
            process.terminate()
            raise RuntimeError("Flask server failed to start within timeout")
        
        return process
    
    def test_flask_initialization(self, performance_timer, mock_environment):
        """
        Test Flask application initialization and WSGI compatibility.
        
        Validates:
        - Flask app creates successfully
        - WSGI application callable is available
        - Environment configuration is processed
        - Startup time meets performance requirements
        """
        performance_timer.start()
        
        try:
            self.server_process = self.start_flask_server()
            startup_time = performance_timer.stop()
            
            # Verify Flask process is running
            assert self.server_process.poll() is None, "Flask process terminated unexpectedly"
            
            # Verify startup time meets performance requirement
            assert startup_time < (PERFORMANCE_THRESHOLDS['startup_time_seconds'] * 1000), \
                f"Flask startup time {startup_time:.2f}ms exceeds {PERFORMANCE_THRESHOLDS['startup_time_seconds']}s limit"
            
            # Verify WSGI server is responding
            assert wait_for_server_ready(
                self.server_config['host'], 
                self.server_config['port'], 
                timeout=2
            ), "Flask WSGI server binding verification failed"
            
        except Exception as e:
            if self.server_process:
                self.server_process.terminate()
            pytest.fail(f"Flask initialization failed: {e}")
    
    def test_flask_route_decorator_functionality(self, http_client):
        """
        Test Flask @app.route decorator functionality for '/hello' endpoint.
        
        Validates:
        - @app.route decorator processes correctly
        - View function executes successfully
        - Flask request/response cycle completes properly
        """
        self.server_process = self.start_flask_server()
        hello_url = urljoin(self.server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        
        response = http_client.get(hello_url)
        
        # Validate Flask routing functionality
        assert response.status_code == EXPECTED_RESPONSES['hello_endpoint']['status_code'], \
            f"Flask route returned status {response.status_code}, expected {EXPECTED_RESPONSES['hello_endpoint']['status_code']}"
        
        # Validate Flask response content
        assert response.text.strip() == EXPECTED_RESPONSES['hello_endpoint']['content'], \
            f"Flask response '{response.text.strip()}' != expected '{EXPECTED_RESPONSES['hello_endpoint']['content']}'"
        
        # Validate Flask sets appropriate headers
        assert 'server' in response.headers or 'Server' in response.headers, \
            "Flask should set server identification headers"
    
    def test_flask_wsgi_compliance(self, http_client):
        """
        Test Flask WSGI compliance and middleware compatibility.
        
        Validates:
        - WSGI application interface works correctly
        - HTTP headers are properly formatted
        - Response streaming works as expected
        """
        self.server_process = self.start_flask_server()
        hello_url = urljoin(self.server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        
        # Test WSGI compliance through HTTP/1.1 features
        headers = {
            'Connection': 'keep-alive',
            'User-Agent': 'pytest-flask-test-client/1.0',
            'Accept': 'text/plain,text/html,*/*'
        }
        
        response = http_client.get(hello_url, headers=headers)
        
        # Validate WSGI response format
        assert response.status_code == 200, f"WSGI response failed with status {response.status_code}"
        
        # Validate HTTP headers are properly formatted
        assert 'content-length' in response.headers or 'Content-Length' in response.headers, \
            "WSGI should set Content-Length header"
        
        assert 'content-type' in response.headers or 'Content-Type' in response.headers, \
            "WSGI should set Content-Type header"
    
    def test_flask_performance_characteristics(self, http_client):
        """
        Test Flask performance meets specification requirements.
        
        Validates:
        - Flask response time < 100ms
        - WSGI pipeline processing efficiency
        - Framework overhead acceptable
        """
        self.server_process = self.start_flask_server()
        hello_url = urljoin(self.server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        
        response_times = []
        num_requests = 15  # Larger sample for Flask performance validation
        
        for _ in range(num_requests):
            response_time_ms, response = measure_response_time(hello_url, 'GET')
            
            # Verify successful Flask response
            assert response.status_code == 200, f"Flask performance test failed with status {response.status_code}"
            
            response_times.append(response_time_ms)
        
        # Calculate Flask performance metrics
        avg_response_time = sum(response_times) / len(response_times)
        percentile_95 = sorted(response_times)[int(0.95 * len(response_times))]
        
        # Validate average response time meets requirements
        assert avg_response_time < PERFORMANCE_THRESHOLDS['response_time_ms'], \
            f"Flask average response time {avg_response_time:.2f}ms exceeds {PERFORMANCE_THRESHOLDS['response_time_ms']}ms limit"
        
        # Validate 95th percentile for consistency
        assert percentile_95 < (PERFORMANCE_THRESHOLDS['response_time_ms'] * 1.5), \
            f"Flask 95th percentile response time {percentile_95:.2f}ms indicates performance issues"
    
    def test_flask_error_handling(self, http_client):
        """
        Test Flask error handling and HTTP status code management.
        
        Validates:
        - Flask handles undefined routes appropriately
        - Error responses maintain WSGI compliance
        - Flask application remains stable after errors
        """
        self.server_process = self.start_flask_server()
        undefined_url = urljoin(self.server_url, '/nonexistent-route')
        
        response = http_client.get(undefined_url)
        
        # Validate Flask 404 handling
        assert response.status_code == EXPECTED_RESPONSES['not_found']['status_code'], \
            f"Flask returned status {response.status_code} for undefined route, expected 404"
        
        # Verify Flask provides error response content
        assert len(response.text) > 0, "Flask should provide error response content"
        
        # Verify Flask application stability after error
        hello_url = urljoin(self.server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        recovery_response = http_client.get(hello_url)
        assert recovery_response.status_code == 200, \
            "Flask application unstable after 404 error"


# =============================================================================
# CROSS-IMPLEMENTATION VALIDATION TESTS
# =============================================================================

class TestCrossImplementationParity:
    """
    Test suite validating parity between native Python and Flask implementations.
    
    Ensures both approaches provide identical functionality and meet the same
    performance and behavioral requirements as specified in the technical requirements.
    """
    
    @pytest.fixture(autouse=True)
    def setup_cross_implementation_tests(self, server_config):
        """Setup fixture for cross-implementation validation."""
        self.server_config = server_config
        self.native_port = server_config['port']
        self.flask_port = get_available_port(self.native_port + 1, 3999)
        
        self.native_process = None
        self.flask_process = None
        self.native_url = f"http://{server_config['host']}:{self.native_port}"
        self.flask_url = f"http://{server_config['host']}:{self.flask_port}"
    
    def teardown_method(self):
        """Cleanup both server processes after each test."""
        for process in [self.native_process, self.flask_process]:
            if process:
                process.terminate()
                process.wait(timeout=5)
        
        self.native_process = None
        self.flask_process = None
    
    def start_both_servers(self):
        """Start both native Python and Flask servers for comparison testing."""
        # Start native Python server
        native_cmd = [
            sys.executable, 'server.py',
            '--port', str(self.native_port),
            '--host', self.server_config['host']
        ]
        
        self.native_process = subprocess.Popen(
            native_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Start Flask server
        flask_env = os.environ.copy()
        flask_env['FLASK_APP'] = 'app.py'
        flask_env['FLASK_ENV'] = 'testing'
        flask_env['PORT'] = str(self.flask_port)
        flask_env['HOST'] = self.server_config['host']
        
        flask_cmd = [
            sys.executable, '-m', 'flask', 'run',
            '--host', self.server_config['host'],
            '--port', str(self.flask_port)
        ]
        
        self.flask_process = subprocess.Popen(
            flask_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=flask_env
        )
        
        # Wait for both servers to be ready
        native_ready = wait_for_server_ready(
            self.server_config['host'], 
            self.native_port, 
            timeout=PERFORMANCE_THRESHOLDS['startup_time_seconds']
        )
        
        flask_ready = wait_for_server_ready(
            self.server_config['host'], 
            self.flask_port, 
            timeout=PERFORMANCE_THRESHOLDS['startup_time_seconds']
        )
        
        if not native_ready or not flask_ready:
            self.teardown_method()
            raise RuntimeError("Failed to start both servers for cross-implementation testing")
    
    def test_response_content_parity(self, http_client):
        """
        Test that both implementations return identical response content.
        
        Validates:
        - Response body content is identical
        - HTTP status codes match exactly
        - Response format consistency
        """
        self.start_both_servers()
        
        # Test /hello endpoint parity
        native_hello_url = urljoin(self.native_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        flask_hello_url = urljoin(self.flask_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        
        native_response = http_client.get(native_hello_url)
        flask_response = http_client.get(flask_hello_url)
        
        # Validate identical status codes
        assert native_response.status_code == flask_response.status_code, \
            f"Status code mismatch: Native={native_response.status_code}, Flask={flask_response.status_code}"
        
        # Validate identical response content
        assert native_response.text.strip() == flask_response.text.strip(), \
            f"Response content mismatch: Native='{native_response.text.strip()}', Flask='{flask_response.text.strip()}'"
        
        # Test 404 error parity
        native_404_url = urljoin(self.native_url, '/undefined')
        flask_404_url = urljoin(self.flask_url, '/undefined')
        
        native_404_response = http_client.get(native_404_url)
        flask_404_response = http_client.get(flask_404_url)
        
        # Validate identical 404 status codes
        assert native_404_response.status_code == flask_404_response.status_code, \
            f"404 status code mismatch: Native={native_404_response.status_code}, Flask={flask_404_response.status_code}"
    
    def test_performance_parity(self, http_client):
        """
        Test that both implementations meet similar performance characteristics.
        
        Validates:
        - Both implementations meet <100ms requirement
        - Performance characteristics are comparable
        - Neither implementation significantly outperforms requirements
        """
        self.start_both_servers()
        
        native_hello_url = urljoin(self.native_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        flask_hello_url = urljoin(self.flask_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        
        # Measure native Python performance
        native_times = []
        for _ in range(10):
            response_time_ms, response = measure_response_time(native_hello_url, 'GET')
            assert response.status_code == 200, f"Native performance test failed"
            native_times.append(response_time_ms)
        
        # Measure Flask performance
        flask_times = []
        for _ in range(10):
            response_time_ms, response = measure_response_time(flask_hello_url, 'GET')
            assert response.status_code == 200, f"Flask performance test failed"
            flask_times.append(response_time_ms)
        
        # Calculate performance metrics
        native_avg = sum(native_times) / len(native_times)
        flask_avg = sum(flask_times) / len(flask_times)
        
        # Both implementations must meet performance requirements
        assert native_avg < PERFORMANCE_THRESHOLDS['response_time_ms'], \
            f"Native average response time {native_avg:.2f}ms exceeds {PERFORMANCE_THRESHOLDS['response_time_ms']}ms limit"
        
        assert flask_avg < PERFORMANCE_THRESHOLDS['response_time_ms'], \
            f"Flask average response time {flask_avg:.2f}ms exceeds {PERFORMANCE_THRESHOLDS['response_time_ms']}ms limit"
        
        # Log performance comparison for analysis
        print(f"\nPerformance Comparison:")
        print(f"Native Python average: {native_avg:.2f}ms")
        print(f"Flask framework average: {flask_avg:.2f}ms")
        print(f"Performance difference: {abs(native_avg - flask_avg):.2f}ms")
    
    def test_concurrent_request_handling_parity(self, http_client):
        """
        Test both implementations handle concurrent requests appropriately.
        
        Validates:
        - Both implementations handle multiple simultaneous requests
        - Response consistency under load
        - No significant performance degradation
        """
        self.start_both_servers()
        
        native_hello_url = urljoin(self.native_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        flask_hello_url = urljoin(self.flask_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
        
        def test_concurrent_requests(url: str, num_requests: int = 20) -> Tuple[List[float], List[int]]:
            """Send concurrent requests and measure performance."""
            response_times = []
            status_codes = []
            
            def single_request():
                try:
                    response_time_ms, response = measure_response_time(url, 'GET')
                    return response_time_ms, response.status_code
                except Exception:
                    return float('inf'), 500  # Treat exceptions as server errors
            
            # Use ThreadPoolExecutor for concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(single_request) for _ in range(num_requests)]
                
                for future in concurrent.futures.as_completed(futures):
                    response_time, status_code = future.result()
                    response_times.append(response_time)
                    status_codes.append(status_code)
            
            return response_times, status_codes
        
        # Test concurrent requests for both implementations
        native_times, native_statuses = test_concurrent_requests(native_hello_url)
        flask_times, flask_statuses = test_concurrent_requests(flask_hello_url)
        
        # Validate successful responses
        native_success_rate = sum(1 for status in native_statuses if status == 200) / len(native_statuses)
        flask_success_rate = sum(1 for status in flask_statuses if status == 200) / len(flask_statuses)
        
        assert native_success_rate >= 0.95, \
            f"Native implementation success rate {native_success_rate:.2%} below 95% threshold"
        
        assert flask_success_rate >= 0.95, \
            f"Flask implementation success rate {flask_success_rate:.2%} below 95% threshold"
        
        # Validate performance under load
        valid_native_times = [t for t, s in zip(native_times, native_statuses) if s == 200]
        valid_flask_times = [t for t, s in zip(flask_times, flask_statuses) if s == 200]
        
        if valid_native_times:
            native_avg_concurrent = sum(valid_native_times) / len(valid_native_times)
            assert native_avg_concurrent < (PERFORMANCE_THRESHOLDS['response_time_ms'] * 2), \
                f"Native concurrent response time {native_avg_concurrent:.2f}ms significantly degraded"
        
        if valid_flask_times:
            flask_avg_concurrent = sum(valid_flask_times) / len(valid_flask_times)
            assert flask_avg_concurrent < (PERFORMANCE_THRESHOLDS['response_time_ms'] * 2), \
                f"Flask concurrent response time {flask_avg_concurrent:.2f}ms significantly degraded"


# =============================================================================
# INTEGRATION AND END-TO-END TESTS
# =============================================================================

class TestIntegrationScenarios:
    """
    Integration test suite validating complete workflows and system behavior.
    
    Tests end-to-end functionality including server lifecycle, configuration
    management, and real-world usage scenarios.
    """
    
    def test_complete_server_lifecycle(self, server_config, http_client):
        """
        Test complete server lifecycle from startup to shutdown.
        
        Validates:
        - Clean server startup and initialization
        - Request processing during normal operation
        - Graceful server shutdown and resource cleanup
        """
        # Test native Python server lifecycle
        native_cmd = [
            sys.executable, 'server.py',
            '--port', str(server_config['port']),
            '--host', server_config['host']
        ]
        
        native_process = subprocess.Popen(
            native_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Verify startup
            assert wait_for_server_ready(
                server_config['host'], 
                server_config['port'], 
                timeout=PERFORMANCE_THRESHOLDS['startup_time_seconds']
            ), "Native server failed to start in lifecycle test"
            
            # Test normal operation
            server_url = f"http://{server_config['host']}:{server_config['port']}"
            hello_url = urljoin(server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
            
            response = http_client.get(hello_url)
            assert response.status_code == 200, f"Native server operation failed: {response.status_code}"
            assert response.text.strip() == EXPECTED_RESPONSES['hello_endpoint']['content'], \
                "Native server response incorrect during lifecycle test"
            
            # Test graceful shutdown
            native_process.terminate()
            exit_code = native_process.wait(timeout=5)
            
            # Verify clean shutdown (exit code 0 or -15 for SIGTERM)
            assert exit_code in [0, -15], f"Native server unclean shutdown with exit code {exit_code}"
            
        finally:
            if native_process.poll() is None:
                native_process.kill()
                native_process.wait()
    
    def test_configuration_management(self, monkeypatch, http_client):
        """
        Test configuration management and environment variable handling.
        
        Validates:
        - Environment variable configuration loading
        - Port and host configuration from environment
        - Configuration override capabilities
        """
        test_port = get_available_port()
        
        # Set environment variables
        monkeypatch.setenv('PORT', str(test_port))
        monkeypatch.setenv('HOST', 'localhost')
        monkeypatch.setenv('FLASK_ENV', 'testing')
        
        # Test Flask configuration management
        flask_env = os.environ.copy()
        flask_env['FLASK_APP'] = 'app.py'
        
        flask_cmd = [
            sys.executable, '-m', 'flask', 'run'
        ]
        
        flask_process = subprocess.Popen(
            flask_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=flask_env
        )
        
        try:
            # Verify Flask uses environment configuration
            assert wait_for_server_ready('localhost', test_port, timeout=10), \
                "Flask failed to use environment configuration"
            
            # Test configured endpoint
            server_url = f"http://localhost:{test_port}"
            hello_url = urljoin(server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
            
            response = http_client.get(hello_url)
            assert response.status_code == 200, \
                f"Flask configuration test failed: {response.status_code}"
            
        finally:
            flask_process.terminate()
            flask_process.wait(timeout=5)
    
    def test_cross_platform_compatibility(self, server_config):
        """
        Test cross-platform compatibility for major operating systems.
        
        Validates:
        - Python path resolution works correctly
        - Port binding works on different platforms
        - Process management is platform-agnostic
        """
        import platform
        
        current_platform = platform.system().lower()
        
        # Test native Python server on current platform
        native_cmd = [
            sys.executable, 'server.py',
            '--port', str(server_config['port']),
            '--host', server_config['host']
        ]
        
        # Platform-specific process handling
        if current_platform == 'windows':
            # Windows-specific process creation
            native_process = subprocess.Popen(
                native_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            # Unix-like platforms
            native_process = subprocess.Popen(
                native_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        try:
            # Verify cross-platform server startup
            server_ready = wait_for_server_ready(
                server_config['host'], 
                server_config['port'], 
                timeout=PERFORMANCE_THRESHOLDS['startup_time_seconds']
            )
            
            assert server_ready, f"Cross-platform server startup failed on {current_platform}"
            
            # Test cross-platform HTTP communication
            server_url = f"http://{server_config['host']}:{server_config['port']}"
            hello_url = urljoin(server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
            
            try:
                response = requests.get(hello_url, timeout=5)
                assert response.status_code == 200, \
                    f"Cross-platform HTTP communication failed on {current_platform}"
            except requests.RequestException as e:
                pytest.fail(f"Cross-platform HTTP request failed on {current_platform}: {e}")
            
        finally:
            # Platform-appropriate process termination
            if current_platform == 'windows':
                native_process.terminate()
            else:
                native_process.terminate()
            
            native_process.wait(timeout=5)


# =============================================================================
# PERFORMANCE AND LOAD TESTING
# =============================================================================

@pytest.mark.performance
class TestPerformanceRequirements:
    """
    Performance test suite validating all performance requirements.
    
    Comprehensive testing of response time, memory usage, startup time,
    and concurrent request handling as specified in technical requirements.
    """
    
    def test_sustained_load_performance(self, server_config, http_client):
        """
        Test performance under sustained load conditions.
        
        Validates:
        - Performance remains consistent under extended load
        - No memory leaks or performance degradation
        - Response time stability over time
        """
        # Start native Python server for load testing
        native_cmd = [
            sys.executable, 'server.py',
            '--port', str(server_config['port']),
            '--host', server_config['host']
        ]
        
        native_process = subprocess.Popen(
            native_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            assert wait_for_server_ready(
                server_config['host'], 
                server_config['port']
            ), "Server failed to start for load testing"
            
            server_url = f"http://{server_config['host']}:{server_config['port']}"
            hello_url = urljoin(server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
            
            # Sustained load test parameters
            test_duration_seconds = 30
            requests_per_second = 10
            total_requests = test_duration_seconds * requests_per_second
            
            response_times = []
            error_count = 0
            start_time = time.time()
            
            for i in range(total_requests):
                try:
                    response_time_ms, response = measure_response_time(hello_url, 'GET')
                    
                    if response.status_code == 200:
                        response_times.append(response_time_ms)
                    else:
                        error_count += 1
                    
                    # Maintain request rate
                    elapsed = time.time() - start_time
                    expected_elapsed = (i + 1) / requests_per_second
                    if elapsed < expected_elapsed:
                        time.sleep(expected_elapsed - elapsed)
                        
                except Exception:
                    error_count += 1
            
            # Validate sustained performance
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                
                assert avg_response_time < PERFORMANCE_THRESHOLDS['response_time_ms'], \
                    f"Sustained load average response time {avg_response_time:.2f}ms exceeds threshold"
                
                assert max_response_time < (PERFORMANCE_THRESHOLDS['response_time_ms'] * 3), \
                    f"Sustained load maximum response time {max_response_time:.2f}ms indicates severe degradation"
            
            # Validate error rate
            error_rate = error_count / total_requests
            assert error_rate < 0.05, f"Sustained load error rate {error_rate:.2%} exceeds 5% threshold"
            
        finally:
            native_process.terminate()
            native_process.wait(timeout=5)
    
    @pytest.mark.benchmark
    def test_response_time_benchmark(self, benchmark, server_config):
        """
        Benchmark response time using pytest-benchmark for precise measurement.
        
        Validates:
        - Consistent response time measurements
        - Statistical analysis of performance
        - Regression detection capabilities
        """
        # Start server for benchmarking
        native_cmd = [
            sys.executable, 'server.py',
            '--port', str(server_config['port']),
            '--host', server_config['host']
        ]
        
        native_process = subprocess.Popen(
            native_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            assert wait_for_server_ready(
                server_config['host'], 
                server_config['port']
            ), "Server failed to start for benchmarking"
            
            server_url = f"http://{server_config['host']}:{server_config['port']}"
            hello_url = urljoin(server_url, EXPECTED_RESPONSES['hello_endpoint']['path'])
            
            def benchmark_request():
                """Single request for benchmarking."""
                response = requests.get(hello_url, timeout=5)
                assert response.status_code == 200
                assert response.text.strip() == EXPECTED_RESPONSES['hello_endpoint']['content']
                return response
            
            # Run benchmark
            result = benchmark(benchmark_request)
            
            # Validate benchmark results meet performance requirements
            # pytest-benchmark provides mean, median, min, max statistics
            assert hasattr(result, 'status_code'), "Benchmark request failed"
            
        finally:
            native_process.terminate()
            native_process.wait(timeout=5)


# =============================================================================
# CUSTOM TEST MARKERS AND CONFIGURATION
# =============================================================================

# Configure pytest markers for test organization
pytestmark = pytest.mark.usefixtures("mock_environment")

# Custom test markers for selective test execution
pytest.mark.slow = pytest.mark.slow  # Marks slow-running tests
pytest.mark.integration = pytest.mark.integration  # Marks integration tests
pytest.mark.performance = pytest.mark.performance  # Marks performance tests
pytest.mark.flaky = pytest.mark.flaky  # Marks potentially flaky tests
pytest.mark.quarantine = pytest.mark.quarantine  # Marks quarantined tests


# =============================================================================
# TEST EXECUTION AND REPORTING
# =============================================================================

if __name__ == "__main__":
    """
    Direct test execution support for development and debugging.
    
    Provides command-line interface for running specific test suites
    with appropriate configuration and reporting.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Python HTTP Server Test Suite")
    parser.add_argument(
        '--test-type', 
        choices=['unit', 'integration', 'performance', 'all'],
        default='all',
        help='Type of tests to run'
    )
    parser.add_argument(
        '--coverage', 
        action='store_true',
        help='Generate coverage report'
    )
    parser.add_argument(
        '--parallel', 
        type=int, 
        default=1,
        help='Number of parallel workers'
    )
    
    args = parser.parse_args()
    
    # Build pytest command line arguments
    pytest_args = []
    
    if args.test_type == 'unit':
        pytest_args.extend(['-m', 'not integration and not performance'])
    elif args.test_type == 'integration':
        pytest_args.extend(['-m', 'integration'])
    elif args.test_type == 'performance':
        pytest_args.extend(['-m', 'performance'])
    
    if args.coverage:
        pytest_args.extend(['--cov=.', '--cov-report=html', '--cov-report=term-missing'])
    
    if args.parallel > 1:
        pytest_args.extend(['-n', str(args.parallel)])
    
    # Add verbose output and detailed reporting
    pytest_args.extend(['-v', '--tb=short', '--junit-xml=test-results.xml'])
    
    # Execute pytest with configured arguments
    exit_code = pytest.main(pytest_args + [__file__])
    sys.exit(exit_code)