from server.udp_server_multi_client_go_back_n import UDPServerMultiClient
from lib.argument_parser import get_server_argparser
import logging
import threading


## python3 start-server-go-back-n.py -H localhost -p 8888 -s server_files -v
def main():
    try:
        args = get_server_argparser().parse_args()

        logging.basicConfig(
            level=args.loglevel,
            format='%(asctime)s.%(msecs)03d  - %(message)s',
            datefmt='%H:%M:%S')

        logging.debug(
            "[INFO] Iniciando servidor en el host : {} y port: {}"
            .format(args.host, int(args.port)))

        udp_server_multi_client = UDPServerMultiClient(args.host, int(args.port))
        udp_server_multi_client.configure_server(args.dirpath)
        thread = threading.Thread(target = udp_server_multi_client.wait_for_client)
        thread.start()

        userInput = input()

        while userInput != 'q':
            userInput = input()
    except KeyboardInterrupt:
        pass
    logging.info("[INFO] - Apagando servidor")
    udp_server_multi_client.shutdown_server()
    thread.join()
    logging.info("[INFO] - Servidor apagado correctamente")

if __name__ == '__main__':
    main()
    