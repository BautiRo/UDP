import socket
from datetime import datetime
import threading
import logging

FORMAT = 'utf-8'
class UDPServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.dest = ''

    def configure_server(self, dest_path = ''):
        # create UDP socket with IPv4 addressing
        # bind server to the address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dest = dest_path
        if(dest_path[:-1] != '/'):
            self.dest += '/'
        logging.info(f'Servidor escuchando en {self.host}:{self.port}')
    
    def handle_request(self, data, client_address):
        msg = data.decode(FORMAT)
        logging.debug("{} ha enviado:".format(client_address))
        print("Datos -> ", msg)
        # send response to the client
        ack = "ACK para: " + msg
        self.socket.sendto(ack.encode(FORMAT), client_address)
        logging.debug("Enviado -> ", ack)

    def wait_for_client(self):
        try:
            # receive message from a client
            data, client_address = self.socket.recvfrom(1024)
            # handle client's request
            self.handle_request(data, client_address)
        except OSError as err:
            self.printwt(err)
    
    def shutdown_server(self):
        logging.info('Apagando el servidor')
        self.socket.close()