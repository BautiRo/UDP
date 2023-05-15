from ast import If
import errno
from multiprocessing.dummy import shutdown
import threading
from server.udp_server import UDPServer
import os
import lib. protocols as protocols
import socket
import logging

FORMAT = 'utf-8'
class UDPServerMultiClient(UDPServer):
    def __init__(self, host, port):
        super().__init__(host, port)
        self.socket_lock = threading.Lock()
        self._thread = None
        self._keep_alive = True

    def handle_request(self, data, client_address):
        # handles the first segment from a flow
        # pid = os.getpid()
        # print("PID ", pid)
        if not client_address:
            self.socket.close()
            return
        
        logging.debug("{} ha enviado:".format(client_address))

        
        #header(66) => method(1), isLast(1), secuenceNumber(32), fileName(32)
        request_method = int(data[0:1].decode(FORMAT))
        request_file_name = str(data[34:66].decode(FORMAT)).replace('0', '')
        
        if request_method == 0:
            # client request download a file
            logging.info("Empezando descarga -> " + request_file_name)            
            self.handle_download_request(request_file_name, client_address)
        elif request_method == 1:
            # client request upload a file
            logging.info("Empezando subida -> " + request_file_name)
            self.handle_upload_request(request_file_name, client_address)
        else:
            # Corrupted segment, close connection
            with self.socket_lock:
                logging.warning('Bad request', data)
                self.socket.sendto("Bad request".encode(FORMAT), client_address)
        # all segments were received/sent => close connection

    def handle_upload_request(self, file_name, client_address):
        incomming_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        logging.info('Conexion aceptada para recibir archivo en puerto ' + str(incomming_socket.getsockname()[1]))

        protocols.recive_file(incomming_socket, client_address, file_name, self.dest)


    def handle_download_request(self, file_name, client_address):
        outgoing_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        outgoing_socket.sendto(str(1).encode(FORMAT), client_address)

        logging.info('Conexion aceptada para enviar archivo en puerto ' + str(outgoing_socket.getsockname()[1]))

        file_path = os.path.join(self.dest, file_name)
        logging.info("Buscando archivo en -> "+ file_path)
        if not os.path.exists(file_path):
            logging.warning('Archivo inexistente')
            self.socket.sendto('Archivo inexistente'.encode(FORMAT), client_address)

        elif not os.path.isfile(file_path):
            logging.warning('El nombre de archivo no es valido')
            self.socket.sendto('El nombre de archivo no es valido'.encode(FORMAT), client_address)
        else:
            protocols.send_stop_and_wait(outgoing_socket, client_address[0], client_address[1], file_path)

        outgoing_socket.close()
    
    def wait_for_client(self):
        try:
            self.socket.bind((self.host, self.port))
            while self._keep_alive:
                try: # receive request from client
                    data, client_address = self.socket.recvfrom(1024)
                    self._thread = threading.Thread(target = self.handle_request, args = (data, client_address))
                    self._thread.daemon = True
                    self._thread.start()
                except OSError as err:
                    print(err)
        except KeyboardInterrupt:
            self._thread.join()
            self.shutdown_server()

    def shutdown_server(self):
        self._keep_alive = False
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError as exc:
            if exc.errno != errno.ENOTCONN: # Socket is not connected, so can't send FIN packet.
                raise 
        if self._thread and self._thread.is_alive():
            self._thread.join()