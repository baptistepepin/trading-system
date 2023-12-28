import argparse
import logging.config
import os
import signal
import sys

from dotenv import load_dotenv

from config.configuration import resolve_yaml_config
from data.cryptoDatabase import CryptoDatabase
from engine.engine import Engine

load_dotenv()


def start():
    parser = argparse.ArgumentParser(prog="Gateway App")
    parser.add_argument(
        "-c",
        "--config",
        type=argparse.FileType("r", encoding="UTF-8"),
        required=True,
        help="filepath to YAML configuration",
    )
    args = parser.parse_args()

    try:
        cfg = resolve_yaml_config(args.config)
        os.makedirs(os.getenv("LOGDIR"), exist_ok=True)
        logging.config.dictConfig(cfg["logging"])
    except Exception as e:
        print(f"STARTUP FAILURE: {e}", file=sys.stderr)
        exit(1)
    else:
        log = logging.getLogger("app")
        log.info("STARTUP")
        cryptoDatabase = CryptoDatabase(cfg, log)
        cryptoDatabase.close()
        engine = Engine(cfg, log, cryptoDatabase)
        signal.signal(signal.SIGINT, engine.sig_handler)
        engine.start()
        engine.join()
        log.info("SHUTDOWN")
