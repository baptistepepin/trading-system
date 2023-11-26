# standard
import os
import sys
import argparse
import logging.config
import signal
# local
from config.configuration import resolve_yaml_config
from data.cryptoDatabase import CryptoDatabase
from engine.engine import Engine


def main(config):
    log = logging.getLogger('app')
    log.info('STARTUP')
    cryptoDatabase = CryptoDatabase(config, log, '2023-10-01')
    cryptoDatabase.close()
    engine = Engine(config, log, cryptoDatabase)
    signal.signal(signal.SIGINT, engine.sig_handler)
    engine.start()
    engine.join()
    log.info('SHUTDOWN')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="Gateway App")
    parser.add_argument('-c', '--config',
                        type=argparse.FileType('r', encoding='UTF-8'),
                        required=True,
                        help='filepath to YAML configuration')
    args = parser.parse_args()

    try:
        cfg = resolve_yaml_config(args.config)
        os.makedirs(os.getenv('LOGDIR'), exist_ok=True)
        logging.config.dictConfig(cfg['logging'])
    except Exception as e:
        print(f'STARTUP FAILURE: {e}', file=sys.stderr)
        exit(1)
    else:
        main(cfg)
