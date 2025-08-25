from gtw_operations import GTWOperations
import time
import logging
import subprocess
import shlex
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
        url = input("Enter full image URL (e.g., http://192.168.1.10:80/flash_cryptaes.rui): ").strip()
        if not url:
            print("❌ URL cannot be empty.")
            return

        # Replace '#' with '%23' to make wget work
        url_safe = url.replace("#", "%23")
        local_path = "/var/www/html/flash_cryptaes.rui"

        print(f"Downloading image from {url_safe} ...")
        try:
            subprocess.run(["wget", "-O", local_path, url_safe], check=True)
            print(f"✅ Image downloaded to {local_path}")
        except subprocess.CalledProcessError:
            print("❌ Failed to download image.")
            return

        print("Sending flash commands to Gateway...")
        cmds = [
            'pcb_cli "Upgrade.Interface=lan"',
            'pcb_cli "ManagementServer.QueuedTransfers.RemoveTransfer(cmdkey1)"',
            'pcb_cli "ManagementServer.QueuedTransfers.AddTransfer(0, 0, cmdkey1, 1, 0, \\"1 Firmware Upgrade Image\\", \\"' + url + '\\", , , , , , cli, Initial, , )"'
        ]
        for cmd in cmds:
            self.run_custom_gateway_command(cmd)

        # ✅ Add wait time for flash and reboot
        flash_wait_time = 60  # seconds, adjust if needed
        print(f"⏳ Waiting {flash_wait_time} seconds for Gateway to flash and reboot...")
        time.sleep(flash_wait_time)

        # Ping until gateway is fully back online
        ip = "192.168.1.1"
        timeout = 600  # max total wait time
        interval = 5
        elapsed = 0
        while elapsed < timeout:
            if subprocess.call(["ping", "-c", "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                print(f"✅ Gateway {ip} is back online.")
                break
            time.sleep(interval)
            elapsed += interval
        else:
            print("❌ Gateway did not come back online after flash.")
            return


        version_output = self.gtw.conn.execute_commands(["cat /etc/issue.local"],
                                                       prompt=self.gtw.config['prompt'],
                                                       output_file=None)
        version = next(iter(version_output.values())).strip()
        print(f"Flashed version: {version}")
        confirm = input("Is this the correct image? (y/n): ")
        if confirm.lower() == "y":
            print("✅ Flash is done.")
        else:
            print("❌ Flash problem.")

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
