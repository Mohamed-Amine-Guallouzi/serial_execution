#!/usr/bin/env python3
import argparse
from cli_interface import CLIInterface
from logger import setup_logging
import logging
from config_loader import config

def parse_args():
    parser = argparse.ArgumentParser(
        description='Gateway Operations Tool',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-l', '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=config.get('app.log_level', 'INFO'),
        help='Set the logging level'
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    setup_logging(
        log_level=getattr(logging, args.log_level)
    )
    try:
        CLIInterface().run()
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}", exc_info=True)
        raise