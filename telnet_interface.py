import telnetlib
import time
from datetime import datetime

class TelnetInterface:
    def __init__(self, host='192.168.1.1', port=23, timeout=3):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tn = None
        self.log_file = None

    def connect(self):
        """Establish telnet connection"""
        try:
            print(f"Connecting to {self.host}:{self.port}...")
            self.tn = telnetlib.Telnet(self.host, self.port, timeout=self.timeout)
            return True
        except Exception as e:
            print(f"Telnet connection error: {str(e)}")
            return False

    def login(self, username, password, login_prompt="login:", password_prompt="Password:", main_prompt="#"):
        """Login to telnet device"""
        try:
            self.read_until(login_prompt)
            self.send_command(username)
            self.read_until(password_prompt)
            self.send_command(password, end="")
            time.sleep(0.5)
            self.send_command("\r\n")
            
            if not self.read_until(main_prompt, timeout=5):
                raise Exception("Login failed")
            return True
        except Exception as e:
            print(f"Telnet login error: {str(e)}")
            return False

    def send_command(self, command, end="\r\n", wait=0.5):
        """Send command with proper flushing"""
        if not self.tn:
            raise Exception("Telnet connection not established")
        
        # Clear residual data
        try:
            while self.tn.read_eager():
                pass
        except:
            pass
        
        self.tn.write(f"{command}{end}".encode())
        time.sleep(wait)

    def read_until(self, patterns, timeout=5, max_retries=3):
        """Read until pattern is found"""
        if isinstance(patterns, str):
            patterns = [patterns]
        patterns = [p.encode() for p in patterns]
        
        buffer = b''
        for _ in range(max_retries):
            try:
                match_idx, match, data = self.tn.expect(patterns, timeout=timeout)
                buffer += data
                if match:
                    return buffer.decode('utf-8', errors='ignore')
            except EOFError:
                break
            time.sleep(0.5)
        
        return buffer.decode('utf-8', errors='ignore') if buffer else "No output received"

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
                    data = self.tn.read_very_eager().decode('utf-8', errors='ignore')
                    if data:
                        print(data, end='', flush=True)
                        if output_file:
                            with open(output_file, 'a') as f:
                                f.write(data)
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\nStopping stream...")
                self.tn.write(b'\x03')  # Send Ctrl+C
            
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
        """Close telnet connection"""
        if self.tn:
            self.tn.close()
            print("Telnet connection closed")