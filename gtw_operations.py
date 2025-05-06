from serial_interface import SerialInterface
from telnet_interface import TelnetInterface

class GTWOperations:
    def __init__(self, connection_type='serial', port=None, host='192.168.1.1'):
        self.connection_type = connection_type.lower()
        self.conn = None
        self.config = {
            'username': 'root',
            'password': 'sah',
            'prompt': '/cfg/system/root #',
            'login_prompt': 'login:',
            'password_prompt': 'Password:'
        }
        
        if self.connection_type == 'serial':
            self.conn = SerialInterface(port=port)
        elif self.connection_type == 'telnet':
            self.conn = TelnetInterface(host=host)
        else:
            raise ValueError("Invalid connection type. Choose 'serial' or 'telnet'")

    def connect_and_login(self):
        """Establish connection and login"""
        if not self.conn.connect():
            return False
            
        return self.conn.login(
            username=self.config['username'],
            password=self.config['password'],
            login_prompt=self.config['login_prompt'],
            password_prompt=self.config['password_prompt'],
            main_prompt=self.config['prompt']
        )

    def get_system_info(self, output_file=None):
        """Get system information"""
        commands = [
            'date "+%Y-%m-%d %H:%M:%S"',
            'uptime',
            'uname -a',
            'free -m',
            'df -h',
            'ifconfig bridge'
        ]
        return self.conn.execute_commands(
            commands=commands,
            prompt=self.config['prompt'],
            output_file=output_file
        )

    def stream_command(self, command, output_file=None):
        """Stream live command output"""
        self.conn.stream_command(
            command=command,
            prompt=self.config['prompt'],
            output_file=output_file
        )

    def close(self):
        """Close connection"""
        self.conn.disconnect()