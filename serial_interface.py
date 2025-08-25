import serial
import serial.tools.list_ports
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SerialInterface:
    def __init__(self, port=None, baudrate=115200, timeout=3):
        logger.info(f"Initializing SerialInterface (port: {port}, baudrate: {baudrate})")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.log_file = None

    def connect(self):
        """Establish serial connection"""
        try:
            if not self.port:
                logger.debug("Auto-detecting serial port")
                self.port = self._find_serial_port()
                if not self.port:
                    logger.error("No serial port found")
                    return False
            
            logger.info(f"Connecting to {self.port} at {self.baudrate} baud")
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            time.sleep(2)  # Allow time for connection
            logger.info("Serial connection established")
            return True
        except Exception as e:
            logger.error(f"Serial connection failed: {str(e)}", exc_info=True)
            return False

    def _find_serial_port(self):
        """Auto-detect serial port"""
        logger.debug("Searching for available serial ports")
        ports = serial.tools.list_ports.comports()
        for port in ports:
            logger.debug(f"Found port: {port.device} ({port.description})")
            if "USB" in port.description or "Serial" in port.description:
                logger.info(f"Auto-selected port: {port.device}")
                return port.device
        logger.warning("No suitable serial port found")
        return None

    def is_connected(self):
        """Check if connection is active"""
        connected = self.serial_conn and self.serial_conn.is_open
        logger.debug(f"Connection status: {'connected' if connected else 'disconnected'}")
        return connected

    def login(self, username, password, login_prompt="login:", password_prompt="Password:", main_prompt="#"):
        """Login to serial device"""
        logger.info(f"Attempting login as {username}")
        try:
            self.send_command("\r\n")
            response = self.read_until([login_prompt, main_prompt], timeout=5)
            
            if main_prompt in response:
                logger.info("Already logged in")
                return True
                
            if login_prompt not in response:
                logger.error("Login prompt not found")
                return False

            logger.debug("Sending username")
            self.send_command(username)
            self.read_until(password_prompt)
            
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

    def send_command(self, command, end="\r\n"):
        """Send command to serial device"""
        logger.debug(f"Sending command: {command}")
        if not self.is_connected():
            logger.error("Cannot send command - not connected")
            raise Exception("Serial connection not established")
        full_command = f"{command}{end}".encode()
        self.serial_conn.write(full_command)

    def read_until(self, patterns, timeout=5):
        """Read until one of the patterns is found"""
        logger.debug(f"Reading until pattern: {patterns} (timeout: {timeout})")
        if isinstance(patterns, str):
            patterns = [patterns]
            
        end_time = time.time() + timeout
        buffer = ""
        patterns = [p.strip() for p in patterns]

        while time.time() < end_time:
            if self.serial_conn.in_waiting:
                data = self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='ignore')
                buffer += data
                for pattern in patterns:
                    if pattern in buffer:
                        logger.debug(f"Pattern matched: {pattern}")
                        return buffer
            time.sleep(0.1)
        
        logger.debug(f"Read timeout, buffer: {buffer[:100]}...")  # Log first 100 chars
        return buffer

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
                    if self.serial_conn.in_waiting:
                        data = self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='ignore')
                        print(data, end='', flush=True)
                        if output_file:
                            with open(output_file, 'a') as f:
                                f.write(data)
                    time.sleep(0.1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, stopping stream")
                print("\nStopping stream...")
                self.send_command('\x03')  # Send Ctrl-C
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
        """Close serial connection"""
        logger.info("Disconnecting serial")
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                logger.info("Serial connection closed")
            except Exception as e:
                logger.error(f"Error closing serial: {str(e)}", exc_info=True)
                raise
        self.serial_conn = None