from gtw_operations import GTWOperations
import time

class CLIInterface:
    def __init__(self):
        self.gtw = None
        self.menu_options = {
            '1': {'desc': 'Get System Info', 'func': self.get_system_info},
            '2': {'desc': 'Run Custom Command', 'func': self.run_custom_cmd},
            '3': {'desc': 'Stream Live Command', 'func': self.stream_live_cmd},
            '4': {'desc': 'Exit', 'func': self.exit}
        }

    def display_menu(self):
        """Display the main menu options"""
        print("\n=== Gateway Operations ===")
        for key, option in self.menu_options.items():
            print(f"{key}. {option['desc']}")

    def select_connection(self):
        """Handle connection type selection"""
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

    def get_system_info(self):
        """Execute system info commands"""
        output_file = input("Enter output filename (leave empty for console only): ") or None
        try:
            results = self.gtw.get_system_info(output_file=output_file)
            self.display_results(results)
            if output_file:
                print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"Error getting system info: {str(e)}")

    def run_custom_cmd(self):
        """Execute a custom command"""
        cmd = input("Enter command to execute: ").strip()
        if not cmd:
            print("Error: Command cannot be empty")
            return
            
        output_file = input("Enter output filename (leave empty for console only): ") or None
        try:
            results = self.gtw.conn.execute_commands(
                commands=[cmd],
                prompt=self.gtw.config['prompt'],
                output_file=output_file
            )
            self.display_results(results)
            if output_file:
                print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"Error executing command: {str(e)}")

    def stream_live_cmd(self):
        """Stream a live command"""
        cmd = input("Enter command to stream (e.g. 'tail -F /var/log/messages'): ").strip()
        if not cmd:
            print("Error: Command cannot be empty")
            return
            
        output_file = input("Enter output filename (leave empty for console only): ") or None
        try:
            self.gtw.stream_command(
                command=cmd,
                output_file=output_file
            )
        except Exception as e:
            print(f"Error streaming command: {str(e)}")

    def display_results(self, results):
        """Display command results"""
        print("\n=== Command Results ===")
        for cmd, output in results.items():
            print(f"\nCommand: {cmd}\n{'-'*30}\n{output or 'No output received'}")

    def exit(self):
        """Clean up and exit"""
        if self.gtw:
            self.gtw.close()
        print("\nGoodbye!")
        raise SystemExit

    def run(self):
        """Main execution loop"""
        try:
            # Connection setup (only ask once)
            self.gtw = self.select_connection()
            
            # Connection attempt loop
            while True:
                print(f"\nAttempting {self.gtw.connection_type} connection...")
                if self.gtw.connect_and_login():
                    break
                print("Connection failed. Please check settings and try again.")
                if input("Retry? (y/n): ").lower() != 'y':
                    self.exit()
            
            # Main menu
            while True:
                self.display_menu()
                choice = input("\nSelect an option: ").strip()
                if choice in self.menu_options:
                    self.menu_options[choice]['func']()
                else:
                    print("Invalid option!")

        except KeyboardInterrupt:
            self.exit()
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            self.exit()