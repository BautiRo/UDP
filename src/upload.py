from socket import *
from lib.argument_parser import get_upload_argparser
import lib.protocols as protocols
import logging
import os



## python3 upload.py -H localhost -p 8888 -n test_doc.pdf -s client_files -v
def main():
    args = get_upload_argparser().parse_args()

    logging.basicConfig(
        level=args.loglevel,
        format='%(asctime)s.%(msecs)03d  - %(message)s',
        datefmt='%H:%M:%S')



    server_port = int(args.port)
    source_file_path = args.src
    file_name_dst = args.name
    
    logging.debug("Server port: {}".format(server_port))
    logging.debug(
        "Source file path: {}".format(source_file_path))
    logging.debug("File name: {}".format(file_name_dst))
    logging.info(
        "Servidor host : {} , port: {}"
        .format(args.host, server_port))

    if not os.path.exists(source_file_path):
        logging.warning('Ruta inexistente')
        quit()
    
    file_path = os.path.join(source_file_path, file_name_dst)

    if not os.path.exists(file_path):
        logging.warning('Archivo inexistente')
        quit()

    if not os.path.isfile(file_path):
        logging.warning('El nombre de archivo no es valido')
        quit()
    
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    

    try:
        protocols.send_stop_and_wait(clientSocket, args.host, server_port, file_path)
    except Exception as err:
        logging.warning('No se pudo leer el archivo {}'.format(err))

    logging.info('Cerrando conexion')
    clientSocket.close()

main()
