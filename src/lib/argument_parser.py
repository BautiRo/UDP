import argparse
import logging


def get_upload_argparser():
    ap = argparse.ArgumentParser()

    group = ap.add_mutually_exclusive_group()

    group.add_argument(
        '-v', '--verbose',
        help="increase output verbosity",
        action="store_const", dest="loglevel", const=logging.DEBUG,
        default=logging.INFO,
    )
    group.add_argument(
        '-q', '--quiet',
        help="decrease output verbosity",
        action="store_const", dest="loglevel", const=logging.WARNING,
    )

    ap.add_argument(
        "-H",
        "--host",
        help="server IP address",
        metavar="")
    
    ap.add_argument(
        "-p", "--port", help="server port", required=True, metavar=""
    )
    
    ap.add_argument(
        "-s", "--src", help="source file path", required=True, metavar=""
    )
    
    ap.add_argument(
        "-n",
        "--name",
        help="file name",
        required=True,
        metavar="")

    return ap


def get_download_argparser():
    ap = argparse.ArgumentParser()

    group = ap.add_mutually_exclusive_group()
    group.add_argument(
        '-v', '--verbose',
        help="Increase output verbose",
        action="store_const", dest="loglevel", const=logging.DEBUG,
        default=logging.INFO,
    )
    group.add_argument(
        '-q', '--quiet',
        help="Decrease output verbose",
        action="store_const", dest="loglevel", const=logging.WARNING,
    )
    ap.add_argument(
        "-H",
        "--host",
        help="server IP address",
        metavar="")
    ap.add_argument(
        "-p", "--port", help="server port", required=True, metavar=""
    )
    ap.add_argument(
        "-d", "--dst", help="destination file path", required=True, metavar=""
    )
    ap.add_argument(
        "-n",
        "--name",
        help="file name",
        required=True,
        metavar="")

    return ap


def get_server_argparser():

    ap = argparse.ArgumentParser()

    group = ap.add_mutually_exclusive_group()

    group.add_argument(
        '-v', '--verbose',
        help="Increase output verbose",
        action="store_const", dest="loglevel", const=logging.DEBUG,
        default=logging.INFO,
    )
    
    group.add_argument(
        '-q', '--quiet',
        help="Decrease output verbose",
        action="store_const", dest="loglevel", const=logging.WARNING,
    )

    ap.add_argument(
        "-H",
        "--host",
        help="server IP address",
        metavar="")

    ap.add_argument(
        "-p", "--port", help="server port", required=True, metavar=""
    )

    ap.add_argument(
        "-s", "--dirpath", help="storage dir path", required=True, metavar=""
    )

    return ap
