#!/usr/bin/env python3

import serial
import serial.tools.list_ports
import time  # This was missing
from datetime import datetime

# Configuration
SERIAL_PORT = '/dev/ttyUSB0'  # Explicitly set your port
BAUD_RATE = 115200
USERNAME = "root"
PASSWORD = "sah"
PROMPT = "/cfg/system/root #"
OUTPUT_FILE = "serial_output.txt"
COMMANDS = ["time", "uptime"]

def read_until(ser, pattern, timeout=5):
    """Read from serial until pattern is found or timeout"""
    end_time = time.time() + timeout
    buffer = ""
    pattern = pattern.strip()
    
    while time.time() < end_time:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            buffer += data
            if pattern in buffer:
                return buffer
        time.sleep(0.1)
    return buffer

def clean_output(output, cmd):
    """Clean the command output"""
    output = output.replace(f"{cmd}\r\n", "")
    if PROMPT in output:
        output = output.split(PROMPT)[0]
    return output.strip()

def serial_connect():
    try:
        print(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
        
        with serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        ) as ser:
            
            time.sleep(2)  # Wait for connection
            
            with open(OUTPUT_FILE, "a") as f:
                f.write(f"\n=== Session started at {datetime.now()} ===\n")
                
                # Login process
                ser.write(b"\r\n")
                read_until(ser, "login:", timeout=5)
                ser.write(f"{USERNAME}\r\n".encode())
                
                read_until(ser, "Password:", timeout=5)
                ser.write(f"{PASSWORD}\r\n".encode())
                
                read_until(ser, PROMPT, timeout=10)
                
                # Execute commands
                for cmd in COMMANDS:
                    ser.write(f"{cmd}\r\n".encode())
                    output = read_until(ser, PROMPT, timeout=10)
                    
                    f.write(f"\nCommand: {cmd}\n")
                    f.write(clean_output(output, cmd))
                    f.write("\n" + "-"*50 + "\n")
                    print(f"Executed: {cmd}")
            
            print(f"Done. Output saved to {OUTPUT_FILE}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    serial_connect()