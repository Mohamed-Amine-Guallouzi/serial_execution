import serial
import serial.tools.list_ports
import time
from datetime import datetime

class SerialInterface:
    def __init__(self, port=None, baudrate=115200, timeout=3):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.log_file = None

    def connect(self):
        """Establish serial connection"""
        try:
            if not self.port:
                self.port = self._find_serial_port()
                if not self.port:
                    raise Exception("No serial port found")

            print(f"Connecting to {self.port} at {self.baudrate} baud...")
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            time.sleep(2)
            return True
        except Exception as e:
            print(f"Connection error: {str(e)}")
            return False

    def _find_serial_port(self):
        """Auto-detect serial port"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "USB" in port.description or "Serial" in port.description:
                return port.device
        return None

    def login(self, username, password, login_prompt="login:", password_prompt="Password:", main_prompt="#"):
        """Login to serial device"""
        try:
            self.send_command("\r\n")
            response = self.read_until([login_prompt, main_prompt], timeout=5)
            
            if main_prompt in response:
                return True  # Already logged in
                
            if login_prompt not in response:
                raise Exception("Login prompt not found")

            self.send_command(username)
            self.read_until(password_prompt)
            self.send_command(password, end="")  # Don't send extra newline
            time.sleep(0.5)  # Small delay after password
            self.send_command("\r\n")  # Then send newline
            
            if not self.read_until(main_prompt, timeout=5):
                raise Exception("Login verification failed")
            return True
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False

    def send_command(self, command, end="\r\n"):
        """Send command to serial device"""
        if not self.serial_conn or not self.serial_conn.is_open:
            raise Exception("Serial connection not established")
        full_command = f"{command}{end}".encode()
        self.serial_conn.write(full_command)

    def read_until(self, patterns, timeout=5):
        """Read until one of the patterns is found"""
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
                        return buffer
            time.sleep(0.1)
        return buffer

    def stream_command(self, command, prompt, output_file=None):
        """Stream live command output"""
        try:
            self.send_command(command)
            
            if output_file:
                with open(output_file, 'a') as f:
                    f.write(f"\n=== Streaming: {command} ===\n")
                    f.write(f"Started at: {datetime.now()}\n")
            
            print(f"\nStreaming output (Ctrl+C to stop)...\n")
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
                print("\nStopping stream...")
                self.send_command('\x03')  # Send Ctrl+C
            
        except Exception as e:
            print(f"Stream error: {str(e)}")

    def execute_commands(self, commands, prompt, output_file=None):
        """Execute multiple commands"""
        if output_file:
            self.log_file = open(output_file, 'a')
            self.log_file.write(f"\n=== Session started at {datetime.now()} ===\n")

        results = {}
        for cmd in commands:
            try:
                print(f"Executing: {cmd}")
                self.send_command(cmd)
                output = self.read_until(prompt)
                cleaned = self._clean_output(output, cmd, prompt)
                
                if self.log_file:
                    self.log_file.write(f"\nCommand: {cmd}\n{cleaned}\n{'='*50}\n")
                
                results[cmd] = cleaned
            except Exception as e:
                print(f"Error executing {cmd}: {str(e)}")
                results[cmd] = None

        if self.log_file:
            self.log_file.close()
            self.log_file = None

        return results

    def _clean_output(self, output, cmd, prompt):
        """Clean command output"""
        output = output.replace(f"{cmd}\r\n", "")
        output = output.replace(f"{cmd}\n", "")
        if prompt in output:
            output = output.split(prompt)[0]
        return output.strip()

    def disconnect(self):
        """Close serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Serial connection closed")