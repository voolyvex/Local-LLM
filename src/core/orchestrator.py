"""System orchestrator for Local LLM initialization."""

import os
import sys
import time
import asyncio
import logging
import platform
import subprocess
import requests
import aiohttp
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler
import json

from core.dependencies import DependencyManager
from core.launcher import SystemInit
from ollama_server import OllamaServer
from core.ollama import OllamaClient

# Configure rich logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)
console = Console()

class SystemOrchestrator:
    """Orchestrates the initialization and management of all system components."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the orchestrator.
        
        Args:
            project_root: Path to project root. If None, will be auto-detected.
        """
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.dependency_manager = DependencyManager(self.project_root)
        self.system_init = SystemInit()
        self.ollama_server = OllamaServer()
        self.ollama_client = None
        
    async def _check_port(self, port: int, retries: int = 5, delay: float = 1.0) -> bool:
        """Check if a port is available.
        
        Args:
            port: Port number to check
            retries: Number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            bool: True if port is available, False if in use
        """
        import socket
        
        # First try to kill any existing process on the port
        process_info = self._get_process_on_port(port)
        
        # Retry getting process info a few times to mitigate race conditions
        for retry_get_process in range(3):
            if process_info:
                break # Found process info, proceed
            else:
                await asyncio.sleep(0.2) # Small delay before retry
                process_info = self._get_process_on_port(port) # Retry get process info
                
        if process_info: # Process info found (either initially or after retries)
            pid, name = process_info
            logger.warning(f"Port {port} is in use by {name} (PID: {pid})") # Log process name from tasklist
            if name.lower() in ['python.exe', 'pythonw.exe', 'python3.exe', 'python3.13.exe']: # Check process name
                logger.info(f"Attempting to kill process on port {port}") # Log before kill attempt
                if await self._kill_process_on_port(port): # Await kill process
                    # Wait for the process to fully terminate
                    for _ in range(3): # Wait up to 3 times
                        await asyncio.sleep(delay) # Wait delay
                        if not self._get_process_on_port(port): # Check if process is gone
                            break # Process gone, break wait loop
        
        # Now check if the port is available after (potentially) killing process
        for i in range(retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return True
            except OSError:
                if i < retries - 1:
                    await asyncio.sleep(delay)
                continue
        return False
        
    async def ensure_dependencies(self) -> bool:
        """Ensure all dependencies are installed and up to date."""
        with console.status("[bold blue]Checking dependencies...") as status:
            try:
                if not self.dependency_manager.ensure_dependencies():
                    logger.error("Failed to install dependencies")
                    return False
                    
                logger.info("Dependencies verified")
                return True
                
            except Exception as e:
                logger.error(f"Dependency check failed: {e}")
                return False
                
    async def ensure_ollama(self) -> bool:
        """Ensure Ollama is installed, running, and has required models."""
        with console.status("[bold blue]Checking Ollama...") as status:
            try:
                # Create Ollama client and use as context manager
                async with OllamaClient() as client:
                    # Check if Ollama is already running
                    if await client.health_check():
                        logger.info("Using existing Ollama server")
                    else:
                        # Start Ollama server if not running
                        if not self.ollama_server.start():
                            logger.error("Failed to start Ollama server")
                            return False
                        
                        # Wait for server to be ready
                        for _ in range(5):
                            if await client.health_check():
                                break
                            await asyncio.sleep(2)
                        else:
                            logger.error("Ollama server failed to respond")
                            return False
                        
                    # Check for default model
                    models = await client.list_models()
                    default_model = self.system_init.config.get("models", {}).get("default", "mistral")
                    
                    if default_model not in models:
                        logger.info(f"Pulling default model: {default_model}")
                        try:
                            async for progress in client.pull_model(default_model):
                                if "status" in progress and "completed" in progress and "total" in progress:
                                    status_msg = f"Pulling {default_model}: {progress['completed']}/{progress['total']} MB"
                                    status.update(f"[bold blue]{status_msg}")
                        except Exception as e:
                            logger.error(f"Failed to pull model: {e}")
                            return False
                                
                    # Test model with simple inference
                    try:
                        response = await client.generate(
                            model=default_model,
                            prompt="Hello",
                            max_tokens=10
                        )
                        if not response:
                            logger.error("Model test failed")
                            return False
                    except Exception as e:
                        logger.error(f"Model test failed: {e}")
                        return False
                        
                logger.info("Ollama verified")
                return True
                
            except Exception as e:
                logger.error(f"Ollama check failed: {e}")
                return False
                
    async def _save_config(self) -> bool:
        """Save the current configuration to file."""
        try:
            config_path = Path(self.project_root) / "config.json"
            with open(config_path, 'w') as f:
                json.dump(self.system_init.config, f, indent=4)
            logger.info("Configuration updated and saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    async def ensure_api_server(self) -> bool:
        """Ensure API server is running and healthy."""
        with console.status("[bold blue]Starting API server...") as status:
            try:
                # Get default port and fallback ports
                default_port = self.system_init.config.get("ports", {}).get("api", 8000)
                fallback_ports = [8001, 8002, 8003, 8004, 8005]  # List of fallback ports to try
                
                # Try default port first
                port_to_use = default_port
                port_available = await self._check_port(port_to_use)
                
                # If default port is not available, try fallback ports
                if not port_available:
                    logger.warning(f"Default port {default_port} is unavailable, trying fallback ports...")
                    for port in fallback_ports:
                        if await self._check_port(port):
                            port_to_use = port
                            port_available = True
                            logger.info(f"Using fallback port {port}")
                            break
                            
                if not port_available:
                    logger.error("No available ports found")
                    return False
                    
                # Update config with the port we're using
                if "ports" not in self.system_init.config:
                    self.system_init.config["ports"] = {}
                self.system_init.config["ports"]["api"] = port_to_use
                
                # Save the updated configuration
                await self._save_config()
                
                # Initialize API server if not already initialized
                if not hasattr(self.system_init, 'api_server') or not self.system_init.api_server:
                    api_host = self.system_init.config.get("hosts", {}).get("api", "localhost")
                    from core.api import APIServer
                    self.system_init.api_server = APIServer(host=api_host, port=port_to_use)
                
                # Start API server with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # Start the server in a background process
                        process = await asyncio.create_subprocess_exec(
                            'uvicorn',
                            'api.main:app',
                            '--host', '0.0.0.0',
                            '--port', str(port_to_use),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            # Don't create a new console window
                            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
                        )
                        
                        # Store the process
                        self.system_init.api_server.process = process
                        logger.info(f"API server process started with PID: {process.pid}")
                        
                        # Wait for server to be healthy
                        for _ in range(10):  # Increased timeout
                            try:
                                # Check if process is still running
                                if process.returncode is not None:
                                    stdout, stderr = await process.communicate()
                                    logger.error(f"API server process exited with code {process.returncode}")
                                    logger.error(f"stdout: {stdout.decode()}")
                                    logger.error(f"stderr: {stderr.decode()}")
                                    break
                                    
                                # Check server health
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(f"http://localhost:{port_to_use}/health", timeout=2) as response:
                                        if response.status == 200:
                                            logger.info(f"API server started on port {port_to_use}")
                                            return True
                            except (aiohttp.ClientError, asyncio.TimeoutError):
                                await asyncio.sleep(1)
                                continue
                            
                        # If we get here, server didn't start properly
                        if attempt < max_retries - 1:
                            logger.warning(f"API server health check failed, retrying... (attempt {attempt + 1}/{max_retries})")
                            if process and process.returncode is None:
                                process.terminate()
                                await process.wait()
                            await asyncio.sleep(2)
                        else:
                            logger.error("API server failed to start after retries")
                            return False
                            
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Failed to start API server, retrying... (attempt {attempt + 1}/{max_retries}): {e}")
                            await asyncio.sleep(2)
                        else:
                            logger.error(f"API server start failed: {e}")
                            return False
                            
                return False
                
            except Exception as e:
                logger.error(f"API server initialization failed: {e}")
                return False
                
    async def ensure_ui_server(self) -> bool:
        """Ensure Streamlit UI server is running."""
        with console.status("[bold blue]Starting UI server...") as status:
            try:
                # Check if port is available
                ui_port = self.system_init.config.get("ports", {}).get("ui", 8501)
                if not await self._check_port(ui_port):
                    # Try fallback ports
                    fallback_ports = [8502, 8503, 8504, 8505]
                    for port in fallback_ports:
                        if await self._check_port(port):
                            ui_port = port
                            # Update config with new port
                            if "ports" not in self.system_init.config:
                                self.system_init.config["ports"] = {}
                            self.system_init.config["ports"]["ui"] = port
                            # Save the updated configuration
                            await self._save_config()
                            logger.info(f"Using fallback port {port} for UI server")
                            break
                    else:
                        logger.error(f"No available ports found for UI server")
                        return False

                # Initialize UI server if not already initialized
                if not hasattr(self.system_init, 'ui_server') or not self.system_init.ui_server:
                    api_host = self.system_init.config.get("hosts", {}).get("api", "localhost")
                    api_port = self.system_init.config.get("ports", {}).get("api", 8000)
                    from core.ui import UIServer
                    self.system_init.ui_server = UIServer(api_host=api_host, api_port=api_port)
                
                # Start UI server with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await self.system_init.ui_server.start()
                        
                        # Wait for server to be healthy
                        for _ in range(30):  # Longer timeout for UI server
                            try:
                                if await self.system_init.ui_server.health_check():
                                    # Open browser if configured
                                    if self.system_init.config.get("auto_open_browser", True):
                                        import webbrowser
                                        webbrowser.open(f"http://localhost:{ui_port}")
                                    logger.info("UI server started")
                                    return True
                            except Exception:
                                pass
                            await asyncio.sleep(2)
                            
                        if attempt < max_retries - 1:
                            logger.warning(f"UI server health check failed, retrying... (attempt {attempt + 1}/{max_retries})")
                            await self.system_init.ui_server.stop()
                            await asyncio.sleep(2)
                        else:
                            logger.error("UI server failed to start after retries")
                            return False
                            
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Failed to start UI server, retrying... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(2)
                        else:
                            logger.error(f"UI server start failed: {e}")
                            return False
                            
                return False
                
            except Exception as e:
                logger.error(f"UI server initialization failed: {e}")
                return False
                
    async def initialize(self) -> bool:
        """Initialize all system components in the correct order."""
        console.rule("[bold blue]Local LLM Chat Interface - System Initialization")
        
        try:
            # Load configuration
            self.system_init.config = await self.system_init._track(
                "Loading configuration...",
                self.system_init._load_config
            )
            
            # Initialize components in order
            steps = [
                ("Dependencies", self.ensure_dependencies),
                ("Ollama", self.ensure_ollama),
                ("API Server", self.ensure_api_server),
                ("UI Server", self.ensure_ui_server)
            ]
            
            for name, step in steps:
                if not await step():
                    logger.error(f"{name} initialization failed")
                    await self.cleanup()
                    return False
                    
            console.rule("[bold green]Initialization Complete")
            logger.info("System is ready!")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            await self.cleanup()
            return False
            
    async def cleanup(self):
        """Clean up all system resources."""
        try:
            # Stop servers in reverse order
            if hasattr(self.system_init, 'ui_server') and self.system_init.ui_server:
                try:
                    await self.system_init.ui_server.stop()
                except Exception as e:
                    logger.error(f"Failed to stop UI server: {e}")
                    
            if hasattr(self.system_init, 'api_server') and self.system_init.api_server:
                try:
                    # Properly terminate the API server process
                    if hasattr(self.system_init.api_server, 'process'):
                        process = self.system_init.api_server.process
                        if process and process.returncode is None:
                            process.terminate()
                            try:
                                await asyncio.wait_for(process.wait(), timeout=5.0)
                            except asyncio.TimeoutError:
                                process.kill()  # Force kill if graceful termination fails
                    await self.system_init.api_server.stop()
                except Exception as e:
                    logger.error(f"Failed to stop API server: {e}")
                    
            if self.ollama_server:
                try:
                    self.ollama_server.stop()
                except Exception as e:
                    logger.error(f"Failed to stop Ollama server: {e}")
                    
            # Kill any remaining processes on our ports
            ports = [
                self.system_init.config.get("ports", {}).get("api", 8000),
                self.system_init.config.get("ports", {}).get("ui", 8501)
            ]
            for port in ports:
                if self._get_process_on_port(port):
                    await self._kill_process_on_port(port)
                    
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            # Don't re-raise - we want to attempt all cleanup steps
            
    def _get_process_on_port(self, port: int) -> Optional[Tuple[int, str]]:
        """Get process ID and name using port on Windows."""
        try:
            # Use more specific netstat filter to only get listening or established connections
            cmd = f'netstat -ano | findstr ":{port}" | findstr /i "listening established"'
            logger.debug(f"Running netstat command: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            logger.debug(f"Raw netstat output: {result.stdout}")
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse the line to get PID - split and get last item
                lines = result.stdout.strip().split('\n')
                logger.debug(f"Found {len(lines)} potential connections on port {port}")
                
                for line in lines:
                    logger.debug(f"Processing netstat line: {line}")
                    parts = line.strip().split()
                    if len(parts) >= 5:  # Ensure we have enough parts
                        try:
                            pid = int(parts[-1])  # Last part should be PID
                            logger.debug(f"Found PID {pid} on port {port}")
                            
                            # Get process name with error handling
                            cmd = f'tasklist /FI "PID eq {pid}" /FO CSV /NH'
                            logger.debug(f"Running tasklist command: {cmd}")
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                            logger.debug(f"Tasklist output: {result.stdout}")
                            
                            if result.returncode == 0:
                                output = result.stdout.strip()
                                if output.startswith("INFO: No tasks"):
                                    # This is a zombie process - return special marker
                                    logger.warning(f"Found zombie process with PID {pid} on port {port}")
                                    return pid, "ZOMBIE"
                                elif output and not output.startswith("INFO:"):
                                    # Parse CSV format properly
                                    import csv
                                    from io import StringIO
                                    reader = csv.reader(StringIO(output))
                                    row = next(reader, None)
                                    if row and len(row) > 0:
                                        logger.debug(f"Found process name: {row[0]} for PID {pid}")
                                        return pid, row[0]  # First column is process name
                                    else:
                                        logger.debug(f"No valid CSV data found for PID {pid}")
                                else:
                                    logger.debug(f"Skipping info message from tasklist: {output}")
                            else:
                                logger.debug(f"Tasklist command failed for PID {pid}")
                        except (ValueError, StopIteration) as e:
                            logger.debug(f"Error processing PID for line '{line}': {e}")
                            continue
                    else:
                        logger.debug(f"Netstat line has insufficient parts: {line}")
                    
            else:
                logger.debug(f"No connections found on port {port}")
            return None
        except Exception as e:
            logger.error(f"Error getting process on port {port}: {e}")
            return None
            
    async def _kill_process_on_port(self, port: int) -> bool:
        """Kill process using port on Windows."""
        try:
            logger.debug(f"Attempting to identify process on port {port}")
            process_info = self._get_process_on_port(port)
            
            if process_info:
                pid, name = process_info
                logger.debug(f"Found process to kill: {name} (PID: {pid}) on port {port}")
                
                # Special handling for zombie processes
                if name == "ZOMBIE":
                    logger.warning(f"Attempting to kill zombie process (PID: {pid}) on port {port}")
                    # Try a series of increasingly aggressive methods
                    methods = [
                        # PowerShell commands first
                        ('powershell -Command "Stop-Process -Id {pid} -Force"', False),
                        ('powershell -Command "Get-NetTCPConnection -LocalPort {port} | Select-Object -ExpandProperty OwningProcess | ForEach-Object {{ Stop-Process -Id $_ -Force }}"', False),
                        # Then CMD commands
                        ("taskkill /F /PID {pid}", False),
                        ("taskkill /F /T /PID {pid}", True),
                        # Then network commands
                        ("netsh int ipv4 delete excludedportrange protocol=tcp startport={port} numberofports=1", True),
                        ("netsh int ipv4 add excludedportrange protocol=tcp startport={port} numberofports=1", True),
                        # Last resort - try to reset TCP stack
                        ('powershell -Command "Set-NetTCPSetting -SettingName InternetCustom -AutoTuningLevelLocal Disabled"', True),
                        ('powershell -Command "Set-NetTCPSetting -SettingName InternetCustom -AutoTuningLevelLocal Normal"', True),
                        ("netsh winsock reset", True),
                        ("netsh int ip reset", True)
                    ]
                    
                    for cmd_template, needs_admin in methods:
                        try:
                            cmd = cmd_template.format(pid=pid, port=port)
                            if needs_admin:
                                # Use runas to elevate privileges
                                cmd = f'powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/c,{cmd}\'"'
                            logger.debug(f"Executing command: {cmd}")
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                            logger.debug(f"Command output: stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}', returncode={result.returncode}")
                            await asyncio.sleep(2)
                            
                            # Check if port is now free
                            if not self._get_process_on_port(port):
                                logger.info(f"Successfully killed zombie process on port {port}")
                                return True
                        except Exception as e:
                            logger.debug(f"Command failed: {e}")
                            continue
                    
                    # If all methods failed, suggest manual intervention
                    logger.error(f"Failed to kill zombie process on port {port}. Please try restarting your computer.")
                    return False
                
                # Normal process killing logic
                for attempt in range(3):
                    logger.info(f"Attempt {attempt + 1}: Killing process {name} (PID: {pid}) on port {port}")
                    
                    # First try graceful termination with PowerShell
                    kill_command = f'powershell -Command "Stop-Process -Id {pid}"'
                    logger.debug(f"Executing graceful kill: {kill_command}")
                    result = subprocess.run(kill_command, shell=True, capture_output=True, text=True)
                    logger.debug(f"Graceful kill output: stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}', returncode={result.returncode}")
                    await asyncio.sleep(2)
                    
                    # Verify if process is gone
                    check_result = self._get_process_on_port(port)
                    if not check_result:
                        logger.info(f"Process {name} (PID: {pid}) on port {port} gracefully terminated.")
                        return True
                    else:
                        logger.debug(f"Process still exists after graceful kill: {check_result}")
                    
                    # If still running, force kill with PowerShell
                    force_kill_command = f'powershell -Command "Stop-Process -Id {pid} -Force"'
                    logger.debug(f"Executing force kill: {force_kill_command}")
                    force_result = subprocess.run(force_kill_command, shell=True, capture_output=True, text=True)
                    logger.debug(f"Force kill output: stdout='{force_result.stdout.strip()}', stderr='{force_result.stderr.strip()}', returncode={force_result.returncode}")
                    await asyncio.sleep(2)
                    
                    # Verify again
                    check_result = self._get_process_on_port(port)
                    if not check_result:
                        logger.info(f"Process {name} (PID: {pid}) on port {port} force-killed.")
                        return True
                    else:
                        logger.debug(f"Process still exists after force kill: {check_result}")
                    
                    logger.warning(f"Process {name} (PID: {pid}) still running on port {port} after attempt {attempt + 1}.")
                    await asyncio.sleep(1)
                
                logger.error(f"Failed to kill process {name} (PID: {pid}) on port {port} after multiple attempts.")
                return False
                
            else:
                logger.debug(f"No process found on port {port}")
                return True  # No process to kill
        except Exception as e:
            logger.error(f"Error killing process on port {port}: {e}")
            return False

    async def _wait_for_api_ready(self, timeout=30):
        """Wait for API server to become ready"""
        start_time = time.time()
        time.sleep(2)  # Add a small initial delay
        logger.info("Waiting for API server to become ready...")
        while time.time() - start_time < timeout:
            try:
                logger.debug("Sending health check request to API server...")
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{self.system_init.config.get('ports', {}).get('api', 8000)}/health",
                        timeout=2
                    ) as response:
                        logger.debug(f"Health check response: {response.status}")
                        if response.status == 200:
                            return True
            except (aiohttp.ClientError, asyncio.TimeoutError):
                await asyncio.sleep(0.5)
                continue
        return False

def main():
    """Main entry point for system initialization."""
    try:
        # Create and get event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create orchestrator
        orchestrator = SystemOrchestrator()
        
        try:
            # Run initialization
            loop.run_until_complete(orchestrator.initialize())
            
            # Keep the loop running to maintain the servers
            loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            # Run cleanup
            loop.run_until_complete(orchestrator.cleanup())
        finally:
            # Clean up pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Wait for task cancellation
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            # Close the loop
            loop.close()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main() 