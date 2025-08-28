# cli_interface.py
from gtw_operations import GTWOperations
import time
import logging
import subprocess
from functools import wraps
import webbrowser
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from config_loader import config

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

def connect_wifi_real(ssid, password):
    try:
        print(f"🔗 Connecting to Wi-Fi SSID: {ssid} ...")

        # Disconnect from any network first (optional)
        subprocess.run(["nmcli", "device", "disconnect", config.get('wifi.interface', 'wlp0s20f3')], check=False)

        # Try to connect to given SSID with password
        result = subprocess.run(
            ["nmcli", "device", "wifi", "connect", ssid, "password", password, "ifname", config.get('wifi.interface', 'wlp0s20f3')],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ Connected successfully to", ssid)
            return True
        else:
            print("❌ Failed to connect:", result.stderr.strip())
            return False

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return False

def test_internet_connectivity():
    try:
        subprocess.run(
            ["ping", "-c", str(config.get_int('network.ping_count', 2)), config.get('network.test_ips')[0]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        print("✅ Internet connectivity OK")
        return True
    except subprocess.CalledProcessError:
        print("❌ No Internet connectivity")
        return False

def test_youtube_reachability():
    try:
        subprocess.run(["curl", "-Is", config.get('youtube.test_url')], check=True)
        print("✅ YouTube reachable")
        return True
    except subprocess.CalledProcessError:
        print("❌ YouTube not reachable")
        return False

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
            '6': {'desc': 'Configuration', 'func': self.configuration_menu},
            '0': {'desc': 'Exit', 'func': self.exit},
        }
        self.test_options = {
            '1': {'desc': 'Reboot Test', 'func': self.test_reboot},
            '0': {'desc': 'Back to Main Menu', 'func': None}
        }
        self.auto_tests_options = {
            '1': {'desc': 'Ping Test', 'func': self.auto_ping_test},
            '2': {'desc': 'Flash Image', 'func': self.auto_flash_image},
            '3': {'desc': 'Connect to Wi-Fi', 'func': self.auto_connect_wifi},
            '4': {'desc': 'YouTube Stream', 'func': self.config_youtube},
            '0': {'desc': 'Back to Main Menu', 'func': None}
        }
        
        # Configuration menu options
        self.config_options = {
            '1': {'desc': 'WAN Surfing', 'func': self.config_wan_surfing},
            '2': {'desc': 'WebUI', 'func': self.config_webui},
            '3': {'desc': 'VoIP', 'func': self.config_voip},
            '4': {'desc': 'ACS', 'func': self.config_acs},
            '5': {'desc': 'WiFi Configuration', 'func': self.config_wifi},
            '0': {'desc': 'Back to Main Menu', 'func': None}
        }

    @log_command
    def config_wifi(self):
        """Configure WiFi SSID and password"""
        print("\n=== Configuring WiFi ===")
        
        # Get values from config or ask user
        ssid = input(f"Enter WiFi SSID [default: {config.get('wifi.default_ssid', 'Lb3_2Ghz')}]: ").strip() or config.get('wifi.default_ssid', 'Lb3_2Ghz')
        password = input(f"Enter WiFi Password [default: {config.get('wifi.default_password', '123456789')}]: ").strip() or config.get('wifi.default_password', '123456789')
        
        commands = [
            config.get('pcb_cli.wifi.ssid_set').format(ssid=ssid),
            config.get('pcb_cli.wifi.password_set').format(password=password)
        ]
        
        self._execute_config_commands(commands, "WiFi")
        
        print(f"\n✅ WiFi configured successfully: SSID={ssid}, Password={password}")
    
    @log_command
    def config_youtube(self):
        print("🔹 Running YouTube stream test...")

        # Step 1: Test internet connectivity
        try:
            r = requests.get("https://www.youtube.com", timeout=config.get_int('timeouts.youtube_reachability_timeout', 5))
            if r.status_code != 200:
                print("❌ YouTube not reachable")
                return False
        except Exception as e:
            print(f"❌ Internet/YouTube not reachable: {e}")
            return False

        print("✅ Internet connectivity OK")
        print("✅ YouTube is reachable")

        # Step 2: Open YouTube with controlled browser process
        url = config.get('youtube.test_url') + config.get('youtube.autoplay_param')
        try:
            user = os.environ.get("SUDO_USER", None)
            
            # Determine the best browser to use
            browser_cmd = self._get_browser_command()
            if not browser_cmd:
                print("❌ No supported browser found")
                return False
            
            # Open browser with URL
            if user:
                full_cmd = f"{browser_cmd} {url}"
                browser_process = subprocess.Popen(
                    ['sudo', '-u', user, 'bash', '-c', full_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                browser_process = subprocess.Popen(
                    browser_cmd.split() + [url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            print("🎬 Opening YouTube video in browser")
            
            # Wait a moment for browser to launch
            time.sleep(3)
            
            # Step 3: Start countdown
            print(f"⏰ Streaming for {config.get_int('youtube.stream_duration', 210) // 60} minutes...")
            self._countdown_with_animation(config.get_int('youtube.stream_duration', 210))
            
            # Step 4: Close the browser after stream ends
            print("🛑 Ending YouTube stream...")
            browser_process.terminate()
            time.sleep(1)
            browser_process.kill()  # Force kill if terminate didn't work
            
            print("✅ Stream completed and browser closed")
            return True
            
        except Exception as e:
            print(f"❌ Failed to open browser: {e}")
            return False

    def _get_browser_command(self):
        """Get the best available browser command"""
        browsers = config.get_list('browser.commands', [
            'google-chrome --autoplay-policy=no-user-gesture-required',
            'chromium-browser --autoplay-policy=no-user-gesture-required',
            'google-chrome',
            'chromium-browser',
            'firefox'
        ])
        
        for browser_cmd in browsers:
            browser_name = browser_cmd.split()[0]
            result = subprocess.run(['which', browser_name], capture_output=True, text=True)
            if result.returncode == 0:
                return browser_cmd
        
        return None

    def _countdown_with_animation(self, seconds):
        """Display a countdown with animation"""
        for i in range(seconds, 0, -1):
            mins, secs = divmod(i, 60)
            time_format = f"{mins:02d}:{secs:02d}"
            
            # Animation frames
            frames = ["🌕", "🌖", "🌗", "🌘", "🌑", "🌒", "🌓", "🌔"]
            frame = frames[i % len(frames)]
            
            print(f"\r{frame} Streaming time remaining: {time_format}", end="", flush=True)
            time.sleep(1)
        
        print("\r✅ Stream completed successfully! " + " " * 30)

    @log_command
    def auto_connect_wifi(self):
        # Get SSID
        ssid_output = next(iter(self.gtw.conn.execute_commands(
            [config.get('pcb_cli.wifi.ssid_get')],
            prompt=self.gtw.config['prompt']
        ).values())).strip()
        ssid = ssid_output.split('=')[-1]  # extract only the value

        # Get password
        pwd_output = next(iter(self.gtw.conn.execute_commands(
            [config.get('pcb_cli.wifi.password_get')],
            prompt=self.gtw.config['prompt']
        ).values())).strip()
        password = pwd_output.split('=')[-1]  # extract only the value

        print(f"SSID: {ssid}, Password: {password}")

        # Simulate connection
        success = connect_wifi_real(ssid, password)
        if success:
            print("✅ Wi-Fi auto-test passed")
        else:
            print("❌ Wi-Fi auto-test failed")

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
                host = input(f"Enter telnet host [{config.get('connection.telnet.default_host', '192.168.1.1')}]: ").strip() or config.get('connection.telnet.default_host', '192.168.1.1')
                port = input(f"Enter telnet port [{config.get('connection.telnet.default_port', 23)}]: ").strip() or str(config.get('connection.telnet.default_port', 23))
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
            results = self.gtw.conn.execute_commands([f"ping -c {config.get_int('network.ping_count', 4)} {config.get('network.test_ips')[0]}"],
                                                     prompt=self.gtw.config['prompt'],
                                                     output_file=None)
            output = next(iter(results.values()))
            if "0% packet loss" in output or "ttl=" in output.lower():
                print("✅ Internet surfing is OK")
            else:
                print("❌ Internet surfing FAILED")

            if subprocess.call(["ping", "-c", str(config.get_int('network.ping_count', 4)), config.get('network.test_ips')[1]]) == 0:
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

        local_path = config.get('paths.local_flash_image', '/var/www/html/flash_cryptaes.rui')
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
        flash_commands = config.get_list('commands.flash', [
            'pcb_cli "Upgrade.Interface=lan"',
            'pcb_cli "ManagementServer.QueuedTransfers.RemoveTransfer(cmdkey1)"',
            'pcb_cli "ManagementServer.QueuedTransfers.AddTransfer(0, 0, cmdkey1, 1, 0, \\"1 Firmware Upgrade Image\\", \\"http://192.168.1.10:80/flash_cryptaes.rui\\", , , , , , cli, Initial, , )"'
        ])
        
        for cmd in flash_commands:
            self.run_custom_gateway_command(cmd)

        # Wait fixed time with animated progress bar
        wait_time = config.get_int('timeouts.flash_wait', 300)  # 5 minutes
        interval = config.get_int('timeouts.flash_interval', 1)  # update every second
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

    def _wait_for_ping(self, host, timeout=None, interval=None):
        timeout = timeout or config.get_int('timeouts.reboot_wait', 120)
        interval = interval or config.get_int('timeouts.reboot_check_interval', 2)
        
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
            
    # Configuration methods
    @log_command
    def config_wan_surfing(self):
        """Configure WAN Surfing"""
        print("\n=== Configuring WAN Surfing ===")
        commands = [
            config.get('pcb_cli.wan.username_set').format(username='softathome'),
            config.get('pcb_cli.wan.password_set').format(password='softathome')
        ]
        self._execute_config_commands(commands, "WAN Surfing")

    @log_command
    def config_webui(self):
        """Configure WebUI"""
        print("\n=== Configuring WebUI ===")
        commands = [
            config.get('pcb_cli.webui.admin_password_set').format(password='1234'),
            config.get('pcb_cli.webui.ui_state_set')
        ]
        self._execute_config_commands(commands, "WebUI")

    @log_command
    def config_voip(self):
        """Configure VoIP"""
        print("\n=== Configuring VoIP ===")
        server = config.get('voip.sip_server', '172.16.41.10')
        port = config.get_int('voip.sip_port', 5060)
        username = config.get('voip.line_username', '1001')
        password = config.get('voip.line_password', 'sah')
        number = config.get('voip.line_number', '1001')
        
        commands = [
            config.get('pcb_cli.voip.registrar_server').format(server=server),
            config.get('pcb_cli.voip.proxy_server').format(server=server),
            config.get('pcb_cli.voip.user_agent_domain').format(server=server),
            config.get('pcb_cli.voip.outbound_proxy').format(server=server),
            config.get('pcb_cli.voip.outbound_proxy_port').format(port=port),
            config.get('pcb_cli.voip.event_subscribe_mwi'),
            config.get('pcb_cli.voip.event_subscribe_mwi_event'),
            config.get('pcb_cli.voip.event_subscribe_mwi_notifier').format(server=server),
            config.get('pcb_cli.voip.event_subscribe_mwi_notifier_port').format(port=port),
            config.get('pcb_cli.voip.event_subscribe_mwi_notifier_transport'),
            config.get('pcb_cli.voip.event_subscribe_mwi_expire_time'),
            config.get('pcb_cli.voip.line_incoming_caller_id'),
            config.get('pcb_cli.voip.line_mwi_enable'),
            config.get('pcb_cli.voip.line_mwi_type'),
            config.get('pcb_cli.voip.line_sip_uri').format(username=username, server=server),
            config.get('pcb_cli.voip.line_auth_username').format(username=username),
            config.get('pcb_cli.voip.line_auth_password').format(password=password),
            config.get('pcb_cli.voip.line_directory_number').format(number=number),
            config.get('pcb_cli.voip.line_enable'),
            config.get('pcb_cli.voip.voice_profile_reset')
        ]
        self._execute_config_commands(commands, "VoIP")
        
        # Wait before checking status
        wait_time = config.get_int('timeouts.voip_init_wait', 10)
        print(f"\n⏳ Waiting {wait_time} seconds for VoIP service to initialize...")
        self._countdown_with_animation(wait_time)
        
        # Check VoIP status
        print("\n=== Checking VoIP Status ===")
        status_cmd = config.get('pcb_cli.voip.line_status')
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
            acs_config = config.get('acs.http')
            commands = [
                config.get('pcb_cli.acs.username_set').format(username=acs_config['username']),
                config.get('pcb_cli.acs.url_set').format(url=acs_config['url']),
                config.get('pcb_cli.acs.password_set').format(password=acs_config['password']),
                config.get('pcb_cli.acs.connection_username_set').format(username=acs_config['connection_username']),
                config.get('pcb_cli.acs.connection_password_set').format(password=acs_config['connection_password']),
                config.get('pcb_cli.acs.periodic_interval_set').format(interval=acs_config['periodic_interval']),
                config.get('pcb_cli.acs.enable_cwmp'),
                config.get('pcb_cli.acs.allow_connection_request')
            ]
        elif choice == '2':
            acs_config = config.get('acs.https')
            commands = [
                config.get('pcb_cli.acs.username_set').format(username=acs_config['username']),
                config.get('pcb_cli.acs.url_set').format(url=acs_config['url']),
                config.get('pcb_cli.acs.password_set').format(password=acs_config['password']),
                config.get('pcb_cli.acs.connection_username_set').format(username=acs_config['connection_username']),
                config.get('pcb_cli.acs.connection_password_set').format(password=acs_config['connection_password']),
                config.get('pcb_cli.acs.periodic_interval_set').format(interval=acs_config['periodic_interval']),
                config.get('pcb_cli.acs.enable_cwmp'),
                config.get('pcb_cli.acs.allow_connection_request')
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