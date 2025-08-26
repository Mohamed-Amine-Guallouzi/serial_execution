from gtw_operations import GTWOperations
import time
import logging
import subprocess
from functools import wraps

logger = logging.getLogger(__name__)

def log_command(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Entering {func.__name__} (args: {args}, kwargs: {kwargs})")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise
    return wrapper

class CLIInterface:
    def __init__(self):
        logger.info("Initializing CLIInterface")
        self.gtw = None
        self.menu_options = {
            '1': {'desc': 'Get System Info', 'func': self.get_system_info},
            '2': {'desc': 'Run Custom Command', 'func': self.run_custom_cmd},
            '3': {'desc': 'Stream Live Command', 'func': self.stream_live_cmd},
            '4': {'desc': 'Run Tests', 'func': self.run_tests},
            '5': {'desc': 'Auto Tests', 'func': self.run_auto_tests},
            '6': {'desc': 'Configuration', 'func': self.configuration_menu},  # NEW OPTION
            '0': {'desc': 'Exit', 'func': self.exit},
        }
        self.test_options = {
            '1': {'desc': 'Reboot Test', 'func': self.test_reboot},
            '0': {'desc': 'Back to Main Menu', 'func': None}
        }
        self.auto_tests_options = {
            '1': {'desc': 'Ping Test', 'func': self.auto_ping_test},
            '2': {'desc': 'Flash Image', 'func': self.auto_flash_image},
            '0': {'desc': 'Back to Main Menu', 'func': None}
        }
        
        # NEW: Configuration menu options
        self.config_options = {
            '1': {'desc': 'WAN Surfing', 'func': self.config_wan_surfing},
            '2': {'desc': 'WebUI', 'func': self.config_webui},
            '3': {'desc': 'VoIP', 'func': self.config_voip},
            '4': {'desc': 'ACS', 'func': self.config_acs},
            '0': {'desc': 'Back to Main Menu', 'func': None}
        }

    @log_command
    def display_menu(self):
        print("\n=== Gateway Operations ===")
        for key, option in self.menu_options.items():
            print(f"{key}. {option['desc']}")

    @log_command
    def display_test_menu(self):
        print("\n=== Test Menu ===")
        for key, option in self.test_options.items():
            print(f"{key}. {option['desc']}")

    @log_command
    def display_auto_tests_menu(self):
        print("\n=== Auto Tests Menu ===")
        for key, option in self.auto_tests_options.items():
            print(f"{key}. {option['desc']}")
            
    # NEW: Display configuration menu
    @log_command
    def display_config_menu(self):
        print("\n=== Configuration Menu ===")
        for key, option in self.config_options.items():
            print(f"{key}. {option['desc']}")

    @log_command
    def select_connection(self):
        print("\n=== Select Connection Type ===")
        print("1. Serial Connection")
        print("2. Telnet Connection")
        while True:
            choice = input("Choose connection type (1/2): ").strip()
            if choice == '1':
                port = input("Enter serial port (leave empty for auto-detection): ") or None
                return GTWOperations(connection_type='serial', port=port)
            elif choice == '2':
                host = input("Enter telnet host [192.168.1.1]: ").strip() or '192.168.1.1'
                port = input("Enter telnet port [23]: ").strip() or '23'
                return GTWOperations(connection_type='telnet', host=host, port=int(port))
            print("Invalid choice! Please enter 1 or 2")

    @log_command
    def get_system_info(self):
        output_file = input("Enter output filename (leave empty for console only): ") or None
        results = self.gtw.get_system_info(output_file=output_file)
        self.display_results(results)
        if output_file:
            print(f"\nResults saved to: {output_file}")

    @log_command
    def run_custom_cmd(self):
        cmd = input("Enter command to execute: ").strip()
        if not cmd:
            print("Error: Command cannot be empty")
            return
        output_file = input("Enter output filename (leave empty for console only): ") or None
        results = self.gtw.conn.execute_commands(
            commands=[cmd],
            prompt=self.gtw.config['prompt'],
            output_file=output_file
        )
        self.display_results(results)
        if output_file:
            print(f"\nResults saved to: {output_file}")

    @log_command
    def stream_live_cmd(self):
        cmd = input("Enter command to stream (e.g. 'tail -F /var/log/messages'): ").strip()
        if not cmd:
            print("Error: Command cannot be empty")
            return
        output_file = input("Enter output filename (leave empty for console only): ") or None
        self.gtw.stream_command(command=cmd, output_file=output_file)

    @log_command
    def run_tests(self):
        while True:
            self.display_test_menu()
            choice = input("\nSelect a test (0 to go back): ").strip()
            if choice == '0':
                return
            elif choice in self.test_options and self.test_options[choice]['func']:
                self.test_options[choice]['func']()
            else:
                print("Invalid option!")

    @log_command
    def run_auto_tests(self):
        while True:
            self.display_auto_tests_menu()
            choice = input("\nSelect an auto test (0 to go back): ").strip()
            if choice == '0':
                return
            elif choice in self.auto_tests_options and self.auto_tests_options[choice]['func']:
                self.auto_tests_options[choice]['func']()
            else:
                print("Invalid option!")
                
    # NEW: Configuration menu handler
    @log_command
    def configuration_menu(self):
        while True:
            self.display_config_menu()
            choice = input("\nSelect a configuration option (0 to go back): ").strip()
            if choice == '0':
                return
            elif choice in self.config_options and self.config_options[choice]['func']:
                self.config_options[choice]['func']()
            else:
                print("Invalid option!")

    @log_command
    def auto_ping_test(self):
        print("\n=== Auto Ping Test ===")
        try:
            results = self.gtw.conn.execute_commands(["ping -c 4 8.8.8.8"],
                                                     prompt=self.gtw.config['prompt'],
                                                     output_file=None)
            output = next(iter(results.values()))
            if "0% packet loss" in output or "ttl=" in output.lower():
                print("✅ Internet surfing is OK")
            else:
                print("❌ Internet surfing FAILED")

            if subprocess.call(["ping", "-c", "4", "192.168.1.1"]) == 0:
                print("✅ PC can reach Gateway")
            else:
                print("❌ PC cannot reach Gateway")

        except Exception as e:
            print(f"Auto ping test failed: {str(e)}")

    @log_command
    def auto_flash_image(self):
        url = input("Enter full image URL (for download only, e.g., https://.../flash_cryptaes.rui): ").strip()
        if not url:
            print("❌ URL cannot be empty.")
            return

        local_path = "/var/www/html/flash_cryptaes.rui"
        print(f"Downloading image from {url} ...")
        try:
            url_safe = url.replace("#", "%23")
            subprocess.run(["wget", "-O", local_path, url_safe], check=True)
            print(f"✅ Image downloaded to {local_path}")
        except subprocess.CalledProcessError:
            print("❌ Failed to download image.")
            return

        # Send flash commands
        print("Sending flash commands to Gateway...")
        cmds = [
            'pcb_cli "Upgrade.Interface=lan"',
            'pcb_cli "ManagementServer.QueuedTransfers.RemoveTransfer(cmdkey1)"',
            'pcb_cli "ManagementServer.QueuedTransfers.AddTransfer(0, 0, cmdkey1, 1, 0, \\"1 Firmware Upgrade Image\\", \\"http://192.168.1.10:80/flash_cryptaes.rui\\", , , , , , cli, Initial, , )"'
        ]
        for cmd in cmds:
            self.run_custom_gateway_command(cmd)

        # Wait fixed 5 minutes with animated progress bar
        wait_time = 300  # 5 minutes
        interval = 1     # update every second
        total_steps = wait_time // interval
        bar_length = 50

        print(f"⏳ Waiting {wait_time//60} minutes for Gateway to flash and reboot...")
        for step in range(total_steps + 1):
            percent = (step / total_steps) * 100
            filled_length = int(bar_length * step // total_steps)
            bar = '=' * filled_length + '>' + '.' * (bar_length - filled_length - 1)
            remaining_time = wait_time - step * interval
            mins, secs = divmod(remaining_time, 60)
            print(f"\r[{bar}] {percent:6.2f}%  ETA: {mins:02d}:{secs:02d}", end='', flush=True)
            time.sleep(interval)
        print()  # newline after progress bar

        # Check version after flash
        version_after = self.gtw.conn.execute_commands(
            ["cat /etc/issue.local"],
            prompt=self.gtw.config['prompt'],
            output_file=None
        )
        version_after = next(iter(version_after.values())).strip()
        print(f"✅ Gateway finished flashing. New version detected:\n{version_after}")

    @log_command
    def run_custom_gateway_command(self, cmd):
        self.gtw.conn.execute_commands(commands=[cmd],
                                       prompt=self.gtw.config['prompt'],
                                       output_file=None)

    @log_command
    def test_reboot(self):
        print("\n=== Reboot Test ===")
        confirm = input("Are you sure you want to reboot? (y/n): ").lower()
        if confirm != 'y':
            print("Reboot cancelled.")
            return
        target_ip = self.gtw.conn.host if hasattr(self.gtw.conn, 'host') else None
        self.gtw.conn.execute_commands(["reboot"], prompt=self.gtw.config['prompt'], output_file=None)
        self.gtw.close()
        if target_ip:
            print(f"Waiting for {target_ip} to come back online...")
            if not self._wait_for_ping(target_ip):
                print("Timeout: Device didn't come back online")
                return
        print("Attempting reconnect...")
        if self.gtw.connect_and_login():
            print("✅ Gateway is back online after reboot.")
        else:
            print("❌ Failed to reconnect after reboot.")

    def _wait_for_ping(self, host, timeout=120, interval=2):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if subprocess.call(["ping", "-c", "1", host], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                return True
            time.sleep(interval)
        return False

    @log_command
    def display_results(self, results):
        print("\n=== Command Results ===")
        for cmd, output in results.items():
            print(f"\nCommand: {cmd}\n{'-'*30}\n{output or 'No output received'}")

    @log_command
    def exit(self):
        if self.gtw:
            self.gtw.close()
        print("\nGoodbye!")
        raise SystemExit

    @log_command
    def run(self):
        try:
            self.gtw = self.select_connection()
            while True:
                print(f"\nAttempting {self.gtw.connection_type} connection...")
                if self.gtw.connect_and_login():
                    break
                print("Connection failed. Retry?")
                if input("(y/n): ").lower() != "y":
                    self.exit()
            while True:
                self.display_menu()
                choice = input("\nSelect an option: ").strip()
                if choice in self.menu_options:
                    self.menu_options[choice]['func']()
                else:
                    print("Invalid option!")
        except KeyboardInterrupt:
            self.exit()
        except Exception:
            self.exit()
            
    # NEW: Configuration methods
    @log_command
    def config_wan_surfing(self):
        """Configure WAN Surfing"""
        print("\n=== Configuring WAN Surfing ===")
        commands = [
            'pcb_cli "NMC.Username=softathome"',
            'pcb_cli "NMC.Password=softathome"'
        ]
        self._execute_config_commands(commands, "WAN Surfing")

    @log_command
    def config_webui(self):
        """Configure WebUI"""
        print("\n=== Configuring WebUI ===")
        commands = [
            'pcb_cli "UserManagement.User.admin.Password=1234"',
            'pcb_cli "UserInterface.CurrentState=connected"'
        ]
        self._execute_config_commands(commands, "WebUI")

    @log_command
    def config_voip(self):
        """Configure VoIP"""
        print("\n=== Configuring VoIP ===")
        commands = [
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.RegistrarServer=172.16.41.10"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.ProxyServer=172.16.41.10"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.UserAgentDomain=172.16.41.10"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.OutboundProxy=172.16.41.10"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.OutboundProxyPort=5060"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.EventSubscribe.mwi"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.EventSubscribe.mwi.Event=message-summary"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.EventSubscribe.mwi.Notifier=172.16.41.10"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.EventSubscribe.mwi.NotifierPort=5060"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.EventSubscribe.mwi.NotifierTransport=UDP"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.SIP.EventSubscribe.mwi.ExpireTime=0"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Line.LINE1.CallingFeatures.X_ORANGE-COM_IncomingCallerIDNameEnable=1"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Line.LINE1.CallingFeatures.MWIEnable=1"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Line.LINE1.CallingFeatures.X_ORANGE-COM_MWIType=both"',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Line.LINE1.SIP.URI=\\"sip:1001@172.16.41.10\\""',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Line.LINE1.SIP.AuthUserName=\\"1001\\""',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Line.LINE1.SIP.AuthPassword=\\"sah\\""',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Line.LINE1.DirectoryNumber=\\"1001\\""',
            'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Line.LINE1.Enable=\\"Enabled\\""',
            'pcb_cli "VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Reset=1"'
        ]
        self._execute_config_commands(commands, "VoIP")
        
        # Wait 5 seconds with animation before checking status
        print("\n⏳ Waiting for VoIP service to initialize...")
        self._countdown_with_animation(10)
        
        # Check VoIP status
        print("\n=== Checking VoIP Status ===")
        status_cmd = 'pcb_cli "Device.Services.VoiceService.VoiceApplication.VoiceProfile.SIP-Trunk.Line.LINE1.Status?"'
        results = self.gtw.conn.execute_commands(
            commands=[status_cmd],
            prompt=self.gtw.config['prompt'],
            output_file=None
        )
        
        status = next(iter(results.values())).strip()
        print(f"VoIP Status: {status}")
        
        if "Up" in status or "Registered" in status:
            print("✅ VoIP configuration is working correctly")
        else:
            print("❌ VoIP configuration has issues")

    @log_command
    def _countdown_with_animation(self, seconds):
        """Display a countdown animation with progress bar"""
        bar_length = 30
        interval = 0.1  # Update every 100ms
        total_steps = int(seconds / interval)
        
        for step in range(total_steps + 1):
            elapsed = step * interval
            remaining = seconds - elapsed
            percent = (elapsed / seconds) * 100
            
            # Progress bar
            filled_length = int(bar_length * elapsed // seconds)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Countdown timer
            mins, secs = divmod(remaining, 60)
            timer = f"{int(mins):02d}:{int(secs):02d}"
            
            print(f"\r[{bar}] {percent:5.1f}%  Time remaining: {timer}", end='', flush=True)
            time.sleep(interval)
        
        print()  # New line after countdown

    @log_command
    def config_acs(self):
        """Configure ACS"""
        print("\n=== Configuring ACS ===")
        print("1. ACS HTTP")
        print("2. ACS HTTPS")
        choice = input("Select ACS type (1/2): ").strip()
        
        if choice == '1':
            commands = [
                'pcb_cli "ManagementServer.Username=admin"',
                'pcb_cli "ManagementServer.URL=http://10.255.18.20/ACS"',
                'pcb_cli "ManagementServer.Password=cpetest"',
                'pcb_cli "ManagementServer.ConnectionRequestUsername=softathome"',
                'pcb_cli "ManagementServer.ConnectionRequestPassword=softathome"',
                'pcb_cli "ManagementServer.PeriodicInformInterval=120"',
                'pcb_cli "ManagementServer.EnableCWMP=1"',
                'pcb_cli "ManagementServer.AllowConnectionRequestFromAddress="'
            ]
        elif choice == '2':
            commands = [
                'pcb_cli "ManagementServer.Username=admin"',
                'pcb_cli "ManagementServer.URL=https://pnpq3-qualif.spnp.orange.com:443/ACS"',
                'pcb_cli "ManagementServer.Password=cpetest"',
                'pcb_cli "ManagementServer.ConnectionRequestUsername=softathome"',
                'pcb_cli "ManagementServer.ConnectionRequestPassword=softathome"',
                'pcb_cli "ManagementServer.PeriodicInformInterval=120"',
                'pcb_cli "ManagementServer.EnableCWMP=1"',
                'pcb_cli "ManagementServer.AllowConnectionRequestFromAddress="'
            ]
        else:
            print("Invalid choice!")
            return
            
        self._execute_config_commands(commands, "ACS")

    @log_command
    def _execute_config_commands(self, commands, config_name):
        """Helper method to execute configuration commands"""
        print(f"Executing {config_name} configuration commands...")
        
        for cmd in commands:
            try:
                print(f"Executing: {cmd}")
                results = self.gtw.conn.execute_commands(
                    commands=[cmd],
                    prompt=self.gtw.config['prompt'],
                    output_file=None
                )
                output = next(iter(results.values()))
                if "Error" in output or "error" in output:
                    print(f"❌ Error in command: {cmd}")
                    print(f"Output: {output}")
                else:
                    print("✅ Command executed successfully")
            except Exception as e:
                print(f"❌ Failed to execute command: {cmd}")
                print(f"Error: {str(e)}")
                
        self._countdown_with_animation(2)
        print(f"\n{config_name} configuration completed!")