# gtw_operations.py
from serial_interface import SerialInterface
from telnet_interface import TelnetInterface
from datetime import datetime
import time
import logging
from config_loader import config

logger = logging.getLogger(__name__)

class GTWOperations:
    def __init__(self, connection_type='serial', port=None, host=None, **kwargs):
        logger.info(f"Initializing GTWOperations with {connection_type} connection")
        logger.debug(f"Connection params - port: {port}, host: {host}, kwargs: {kwargs}")
        self.connection_type = connection_type.lower()
        self.conn = None
        self.config = {
            'username': config.get('credentials.username', 'root'),
            'password': config.get('credentials.password', 'sah'),
            'prompt': config.get('credentials.prompts.main', '/cfg/system/root #'),
            'login_prompt': config.get('credentials.prompts.login', 'login:'),
            'password_prompt': config.get('credentials.prompts.password', 'Password:')
        }
                
        try:
            if self.connection_type == 'serial':
                logger.debug("Creating SerialInterface")
                self.conn = SerialInterface(port=port)
            elif self.connection_type == 'telnet':
                logger.debug("Creating TelnetInterface")
                host = host or config.get('connection.telnet.default_host', '192.168.1.1')
                self.conn = TelnetInterface(host=host)
            else:
                error_msg = f"Invalid connection type: {self.connection_type}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"Connection initialization failed: {str(e)}", exc_info=True)
            raise

    def connect_and_login(self):
        """Establish connection and login"""
        logger.info("Attempting to connect and login")
        try:
            if not self.conn.connect():
                logger.error("Connection failed")
                return False
                        
            logger.debug("Connection established, attempting login")
            result = self.conn.login(
                username=self.config['username'],
                password=self.config['password'],
                login_prompt=self.config['login_prompt'],
                password_prompt=self.config['password_prompt'],
                main_prompt=self.config['prompt']
            )
            logger.info(f"Login {'successful' if result else 'failed'}")
            return result
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return False

    def get_system_info(self, output_file=None):
        """Get system information"""
        logger.info("Getting system information")
        commands = config.get_list('commands.system_info', [
            'date "+%Y-%m-%d %H:%M:%S"',
            'uptime',
            'uname -a',
            'free -m',
            'df -h',
            'ifconfig bridge'
        ])
        logger.debug(f"System info commands: {commands}")
                
        try:
            results = self.conn.execute_commands(
                commands=commands,
                prompt=self.config['prompt'],
                output_file=output_file
            )
            logger.debug("System info retrieved successfully")
            return results
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}", exc_info=True)
            raise

    def stream_command(self, command, output_file=None):
        """Stream live command output"""
        logger.info(f"Streaming command: {command}")
        try:
            self.conn.stream_command(
                command=command,
                prompt=self.config['prompt'],
                output_file=output_file
            )
            logger.debug("Command streaming completed")
        except Exception as e:
            logger.error(f"Error streaming command: {str(e)}", exc_info=True)
            raise

    def close(self):
        """Close connection"""
        logger.info("Closing connection")
        try:
            self.conn.disconnect()
            logger.info("Connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}", exc_info=True)
            raise