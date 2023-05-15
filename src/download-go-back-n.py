from socket import *
from lib.argument_parser import get_download_argparser
import lib.protocols as protocols
import logging
import os


## python3 download-go-back-n.py -H localhost -p 8888 -n test -d client_files -v
def main():
    args = get_download_argparser().parse_args()

    logging.basicConfig(
        level=args.loglevel,
        format='%(asctime)s.%(msecs)03d  - %(message)s',
        datefmt='%H:%M:%S')

    server_port = int(args.port)
    dest_file_path = args.dst
    file_name_dst = args.name
    
    logging.debug("Server port: {}".format(server_port))
    logging.debug(
        "dest file path: {}".format(dest_file_path))
    logging.debug("File name: {}".format(file_name_dst))
    logging.info(
        "Servidor host : {} , port: {}"
        .format(args.host, server_port))

    if not os.path.exists(dest_file_path):
        logging.warning('Ruta destino inexistente')
        quit()
    
    clientSocket = socket(AF_INET, SOCK_DGRAM)

    try:
        goBackN = protocols.GoBackN(clientSocket, args.host, server_port, file_name_dst)
        goBackN.client_receive(dest_file_path)
    except Exception as err:
        logging.warning('Error {}'.format(err))

    logging.info('Cerrando conexion')
    clientSocket.close()

main()
