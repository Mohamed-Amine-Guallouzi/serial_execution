import telnetlib
import time
from datetime import datetime
import logging
import socket

logger = logging.getLogger(__name__)

class TelnetInterface:
    def __init__(self, host='192.168.1.1', port=23, timeout=3):
        logger.info(f"Initializing TelnetInterface with {host}:{port}")
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tn = None
        self.log_file = None

    def connect(self):
        """Establish telnet connection"""
        logger.debug(f"Connecting to {self.host}:{self.port}")
        try:
            self.tn = telnetlib.Telnet(self.host, self.port, timeout=self.timeout)
            logger.info("Telnet connection established")
            return True
        except socket.timeout:
            logger.error(f"Connection timeout to {self.host}:{self.port}")
            return False
        except Exception as e:
            logger.error(f"Telnet connection failed: {str(e)}", exc_info=True)
            return False

    def is_connected(self):
        """Check if connection is active"""
        connected = self.tn is not None
        logger.debug(f"Connection status: {'connected' if connected else 'disconnected'}")
        return connected

    def login(self, username, password, login_prompt="login:", password_prompt="Password:", main_prompt="#"):
        """Login to telnet device"""
        logger.info(f"Attempting login as {username}")
        try:
            login_result = self.read_until(login_prompt)
            if not login_result:
                logger.error("Login prompt not found")
                return False
            
            logger.debug("Sending username")
            self.send_command(username)
            
            password_result = self.read_until(password_prompt)
            if not password_result:
                logger.error("Password prompt not found")
                return False
            
            logger.debug("Sending password")
            self.send_command(password, end="")
            time.sleep(0.5)
            self.send_command("\r\n")
            
            if not self.read_until(main_prompt, timeout=5):
                logger.error("Main prompt not found after login")
                return False
                
            logger.info("Login successful")
            return True
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return False

    def send_command(self, command, end="\r\n", wait=0.5):
        """Send command with proper flushing"""
        logger.debug(f"Sending command: {command}")
        if not self.is_connected():
            logger.error("Cannot send command - not connected")
            raise Exception("Telnet connection not established")
        
        try:
            while self.tn.read_eager():
                pass
        except:
            pass
        
        full_command = f"{command}{end}".encode()
        self.tn.write(full_command)
        time.sleep(wait)

    def read_until(self, patterns, timeout=5, max_retries=3):
        """Read until pattern is found"""
        logger.debug(f"Reading until pattern: {patterns} (timeout: {timeout}, retries: {max_retries})")
        if isinstance(patterns, str):
            patterns = [patterns]
        patterns = [p.encode() for p in patterns]
        
        buffer = b''
        for attempt in range(max_retries):
            try:
                match_idx, match, data = self.tn.expect(patterns, timeout=timeout)
                buffer += data
                if match:
                    logger.debug(f"Pattern matched after {attempt+1} attempts")
                    return buffer.decode('utf-8', errors='ignore')
            except EOFError:
                logger.warning("EOFError occurred while reading")
                break
            except Exception as e:
                logger.warning(f"Read error (attempt {attempt+1}): {str(e)}")
            time.sleep(0.5)
        
        result = buffer.decode('utf-8', errors='ignore') if buffer else "No output received"
        logger.debug(f"Final read result: {result[:100]}...")  # Log first 100 chars
        return result

    def stream_command(self, command, prompt, output_file=None):
        """Stream live command output"""
        logger.info(f"Starting command stream: {command}")
        try:
            self.send_command(command)
            
            if output_file:
                logger.debug(f"Streaming output to file: {output_file}")
                with open(output_file, 'a') as f:
                    f.write(f"\n=== Streaming: {command} ===\n")
                    f.write(f"Started at: {datetime.now()}\n")
            
            print(f"\nStreaming output (Ctrl+C to stop)...\n")
            logger.debug("Starting stream loop")
            try:
                while True:
                    data = self.tn.read_very_eager().decode('utf-8', errors='ignore')
                    if data:
                        print(data, end='', flush=True)
                        if output_file:
                            with open(output_file, 'a') as f:
                                f.write(data)
                    time.sleep(0.1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, stopping stream")
                print("\nStopping stream...")
                self.tn.write(b'\x03')  # Send Ctrl-C
        except Exception as e:
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            raise

    def execute_commands(self, commands, prompt, output_file=None):
        """Execute multiple commands"""
        logger.info(f"Executing {len(commands)} commands")
        if output_file:
            logger.debug(f"Output will be saved to: {output_file}")
            self.log_file = open(output_file, 'a')
            self.log_file.write(f"\n=== Session started at {datetime.now()} ===\n")

        results = {}
        for cmd in commands:
            try:
                logger.debug(f"Executing command: {cmd}")
                self.send_command(cmd)
                
                if cmd.strip() == "reboot":
                    logger.warning("Reboot command detected, special handling")
                    time.sleep(1)
                    results[cmd] = "Reboot command sent"
                    continue
                    
                output = self.read_until(prompt)
                cleaned = self._clean_output(output, cmd, prompt)
                
                if self.log_file:
                    self.log_file.write(f"\nCommand: {cmd}\n{cleaned}\n{'='*50}\n")
                
                results[cmd] = cleaned
            except Exception as e:
                logger.error(f"Error executing {cmd}: {str(e)}", exc_info=True)
                results[cmd] = None

        if self.log_file:
            self.log_file.close()
            self.log_file = None

        logger.debug(f"Command execution completed, {len(results)} results")
        return results

    def _clean_output(self, output, cmd, prompt):
        """Clean command output"""
        cleaned = output.replace(f"{cmd}\r\n", "").replace(f"{cmd}\n", "")
        if prompt in cleaned:
            cleaned = cleaned.split(prompt)[0]
        logger.debug(f"Cleaned output (length: {len(cleaned)})")
        return cleaned.strip()

    def disconnect(self):
        """Close telnet connection"""
        logger.info("Disconnecting telnet")
        if self.tn:
            try:
                self.tn.close()
                logger.info("Telnet connection closed")
            except Exception as e:
                logger.error(f"Error closing telnet: {str(e)}", exc_info=True)
                raise
        self.tn = None