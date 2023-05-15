import select
import threading
import errno
from time import sleep
from server.udp_server import UDPServer
import os
import lib. protocols as protocols
import socket
import logging
from random import randrange


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

        logging.info("Nueva conexion desde {}".format(client_address))
        
        #header(66) => method(1), isLast(1), secuenceNumber(32), fileName(32)
        request_method = int(data[0:1].decode(FORMAT))
        # print("request_method: ", request_method)
        is_last = int(data[1:2].decode(FORMAT))
        # print("is_last: ", is_last)
        sequence_number = int(data[2:34].decode(FORMAT))
        if sequence_number != 0:
            logging.warning("Error en el numero de secuencia")
            return
        # print("sequence_number: ", sequence_number)
        request_file_name = str(data[34:66].decode(FORMAT)).replace('0', '')
        # print("request_file_name: ", request_file_name)

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
                self.socket.sendto(("ERR" + str(0).zfill(31)).encode(FORMAT), client_address)
        # all segments were received/sent => close connection

    def handle_upload_request(self, file_name, client_address):
        incomming_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        goBackN = protocols.GoBackN(incomming_socket, client_address[0], client_address[1], file_name)
        goBackN.server_receive(self.dest)
        
        incomming_socket.close()
        return

    def handle_download_request(self, file_name, client_address):
        outgoing_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)



        file_path = os.path.join(self.dest, file_name)
        logging.info("Buscando archivo en -> "+ file_path)
        if not os.path.exists(file_path):
            logging.warning('Archivo inexistente')
            outgoing_socket.sendto((str('ERR') + str('1').zfill(31)).encode(FORMAT), client_address)
        elif not os.path.isfile(file_path):
            logging.warning('El nombre de archivo no es valido')
            outgoing_socket.sendto((str('ERR') + str('2').zfill(31)).encode(FORMAT), client_address)
        else:
            outgoing_socket.sendto(("ACK" + str("0").zfill(32)).encode(FORMAT), client_address)
            goBackN = protocols.GoBackN(outgoing_socket, client_address[0], client_address[1], file_path)
            goBackN.server_send(self.dest)

        outgoing_socket.close()

    
    def wait_for_client(self):
        try:
            self.socket.bind((self.host, self.port))
            while self._keep_alive:
                try: # receive request from client
                    data, client_address = self.socket.recvfrom(1024)
                    c_thread = threading.Thread(target = self.handle_request, args = (data, client_address))
                    c_thread.daemon = True
                    c_thread.start()
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