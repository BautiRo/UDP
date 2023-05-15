from multiprocessing.reduction import ACKNOWLEDGE
from random import randrange
from re import I
import re
import select
from socket import *
from sqlite3 import connect
from threading import Thread
from time import sleep
import traceback
import lib.timer as timer
import os
import logging

import server
from .constants import *

class ConnectionLostException(Exception):
    pass

class Protocol:
    def __init__(self, client_socket, server_name, server_port, file_path):
        self.client_socket = client_socket
        self.server_name = server_name
        self.server_port = server_port
        self.file_path = file_path
    
    def send(self):
        pass

    def receive(self):
        pass

    def close(self):
        pass

def send_chunk_stop_and_wait(client_socket, server_name, server_port, chunk):
    global TIMEOUT_SECS
    sent = False
    retries = 0
    logging.debug('Destino. Server ' + server_name + ' Puerto ' + str(server_port))
    while not sent:
        secuence_number = str(chunk[3:34].decode(FORMAT)).replace('0', '')
        logging.debug('Enviando paquete: ' + secuence_number + ' con Timeout de ' + str(round(TIMEOUT_SECS*1000, 2)) + ' ms')
        timer.start()
        client_socket.sendto(chunk,(server_name, server_port))

        # stop and wait for ACK
        ready = select.select([client_socket], [], [], TIMEOUT_SECS)
        if ready[0]:
            ack, server_address = client_socket.recvfrom(BUFFER_SIZE)
            
            TIMEOUT_SECS = timer.getUpdatedTimeout()
            logging.debug('Nuevo timeout fijado: ' + str(round(TIMEOUT_SECS*1000, 2)) + 'ms')
            retries = 0
            sent = True
            
            logging.debug('ACK recibido: ' + ack.decode(FORMAT))
        else:
            # duplico el los segundos para evitar un timeout prematuro cuando hay congestion
            retries += 1
            logging.debug('RETRIES ' + str(retries))
            if retries > MAX_RETRIES or TIMEOUT_SECS > 5:
                raise ConnectionLostException('El host destino no responde')

            TIMEOUT_SECS *= 2
            logging.debug('DUPLICO timeout:'+  str(round(TIMEOUT_SECS*1000, 2)) + ' ms')
            
            logging.info('Timeout! ACK no recibido para: ' + secuence_number)
    
    return server_address

def send_stop_and_wait(client_socket, server_name, server_port, file_path):
    try:
        file = open(file_path, 'rb')
        file_name = os.path.basename(file_path)
        #header(66) => method(1), is_last(1), secuence_number(32), file_name(32)
        i = 1
        header = bytes('1' + '0' + str(i).zfill(32) + file_name.zfill(32), FORMAT)
        server_address = send_chunk_stop_and_wait(client_socket, server_name, server_port, header)
        
        chunk = file.read(PAYLOAD_SIZE)
        while (chunk):
            i += 1
            header = bytes('1' + '0' + str(i).zfill(32) + file_name.zfill(32), FORMAT)
            if(send_chunk_stop_and_wait(client_socket, server_address[0], server_address[1], header + chunk)):
                chunk = file.read(PAYLOAD_SIZE)
        file.close()
        final = bytes('1' + '1' + str(i+1).zfill(32) + file_name.zfill(32), FORMAT)
        send_chunk_stop_and_wait(client_socket, server_address[0], server_address[1], final)

        logging.info('Archivo ('+ file_name +') enviado correctamente') 

    except KeyboardInterrupt:
        logging.info('Procesamiento cancelado por el usuario')
    except ConnectionLostException as e:
        logging.warning(e)
    except Exception as e:
        traceback.print_exc()
        print(e)

def recive_stop_and_wait(reciver_socket, server_name, server_port, file_name, file_dest_path):
    try:
        #header(66) => method(1), is_last(1), secuence_number(32), file_name(32)
        secuence_number = 1
        header = bytes('0' + '1' + str(secuence_number).zfill(32) + file_name.zfill(32), FORMAT)
        server_address = send_chunk_stop_and_wait(reciver_socket, server_name, server_port, header)
        
        recive_file(reciver_socket, server_address, file_name, file_dest_path)

    except KeyboardInterrupt:
        logging.info('Procesamiento cancelado por el usuario')
    except ConnectionLostException as e:
        logging.warning(e)
    except Exception as e:
        traceback.print_exc()
        print(e)

# ACK Message format: SEQUENCE_NUMBER
class GoBackN(Protocol):

    def __init__(self, client_socket, server_name, server_port, file_path):
        # Manejado por el thread que recibe
        self.last_aknowledged = 0
        self.last_ack_repetition_amount = 0
        
        # Manejado por el thread que envia
        self.last_sent = 0
        self.repeat_last_package = False

        self.finished_send = False
        self.finished = False

        self.client_socket = client_socket
        self.server_name = server_name
        self.server_port = server_port
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.server_address = None
        self.no_more_chunks = False
        self.dest = None
        self.finished_with_error = False
        self.file_was_sent_succesfully = False
        self.received_last_ack = False
        self.command_errors = {
            0: 'Bad request',
            1: 'Archivo inexistente',
            2: 'El nombre de archivo no es valido'
        }
    
    def sender_receive(self):
        logging.debug('Iniciando thread de recepcion de ACKs')
        retries = 0
        while True:
            ready = select.select([self.client_socket], [], [], 2)
            if ready[0]:
                ack, server_addres = self.client_socket.recvfrom(BUFFER_SIZE)
                is_ack = str(ack[0:3].decode(FORMAT))
                if is_ack != 'ACK':
                    continue

                ack = int(ack[3:].decode(FORMAT))
                logging.debug('ACK recibido: ' + str(ack))
                logging.debug('Ultimo enviado: ' + str(self.last_sent))

                retries = 0

                if ack == self.last_aknowledged:
                    self.last_ack_repetition_amount += 1
                    if self.last_ack_repetition_amount >= 3:
                        self.repeat_last_package = True
                        self.last_ack_repetition_amount = 0

                if ack >= self.last_aknowledged + 1:
                    self.last_aknowledged = ack

                    if self.no_more_chunks and self.last_aknowledged > self.last_sent:
                        logging.debug('Termino de los ACKs')
                        self.finished_send = True
                        self.file_was_sent_succesfully = True
                        self.received_last_ack = True
                        print('Enviado ultimo ACK de fin')
                        self.client_socket.sendto(bytes('1' + '1' + str("ACK").zfill(30), FORMAT), (self.server_name, self.server_port))
                        break
            else:
                logging.debug('Timeout')
                retries += 1
                if retries >= MAX_RETRIES:
                    print('Maximo de reintentos alcanzado')
                    self.finished_send = True
                    self.finished_with_error = True
                    break
                
                # Reinicio el ultimo paquete enviado
                self.repeat_last_package = True
                self.last_ack_repetition_amount = 0
        
        return

    def sender_send(self):

        file = open(self.file_path, 'rb')
        last_package_send_amount = 0
        while not self.finished_send:

            if self.repeat_last_package:
                packaget_to_repeat = self.last_aknowledged + 1
                logging.debug('Reenviando paquete: ' + str(packaget_to_repeat))
                file.seek((PAYLOAD_SIZE-34)*(self.last_aknowledged),0)
                chunk = file.read(PAYLOAD_SIZE-34)
                if not chunk:
                    self.no_more_chunks = True
                    if self.last_sent == self.last_aknowledged: # ACKs recibidos para todos los paquetes enviados con informacion
                        self.file_was_sent_succesfully = True
                        break
                    continue
                else:
                    self.repeat_last_package = False
                    header = bytes('1' + '0' + str(packaget_to_repeat).zfill(32), FORMAT)
                    self.client_socket.sendto(header+chunk,(self.server_name, self.server_port))
                    self.last_sent = packaget_to_repeat
                    
            if self.last_sent - self.last_aknowledged < WINDOW_SIZE:
                next_package_to_send = self.last_sent + 1
                offset = (PAYLOAD_SIZE-34) * self.last_sent
                file.seek(offset)
                chunk = file.read(PAYLOAD_SIZE-34)
                if not chunk:
                    self.no_more_chunks = True
                    if self.last_sent == self.last_aknowledged: # ACKs recibidos para todos los paquetes enviados con informacion
                        self.file_was_sent_succesfully = True
                        break
                    continue
                else:
                    logging.debug('Enviando paquete: ' + str(next_package_to_send))
                    header = bytes('1' + '0' + str(next_package_to_send).zfill(32), FORMAT)
                    self.client_socket.sendto(header+chunk,(self.server_name, self.server_port))
                    self.last_sent = next_package_to_send
                    last_package_send_amount = 0
        
        contador = 0
        while not self.received_last_ack:
            print('Envio paquete de fin de informacion')
            header = bytes('1' + '1' + str(self.last_sent + 1).zfill(32) + str("").zfill(PAYLOAD_SIZE-34), FORMAT)
            self.client_socket.sendto(header,(self.server_name, self.server_port))

            sleep(TIMEOUT_SECS)
            contador += 1
            if contador > 5:
                break

        if self.file_was_sent_succesfully:
            logging.info('Archivo enviado correctamente')
            if self.finished_with_error:
                logging.info('No se recibio confirmacion de llegada del ultimo paquete')

        # logging.info('Termino de enviar')
        file.close()

    def receiver_receive(self, file):

        last_received = 0
        finished = False

        # Receive the file itself
        while not finished:
            try:
                chunk, client_address = self.client_socket.recvfrom(512)
                # if len(chunk) < 66:
                #     logging.warning("Mensaje incompleto")
                #     logging.debug("Error -> " + chunk.decode(FORMAT))
                #     os.remove(os.path.join(dest_path, self.file_path))
                #     break
            except Exception as e:
                print(e)
                break
            is_last = int(chunk[1:2].decode(FORMAT))
            sequence_number_received = int(chunk[2:34].decode(FORMAT))
            payload = chunk[34:]
            
            logging.debug('Recibido segmento ' + str(sequence_number_received))
            if is_last == 1 and (sequence_number_received == (last_received + 1)):
                logging.debug('Archivo recibido con ultimo segmento ' + str(sequence_number_received))
                file.close()
                last_received += 1
                finished = True
            elif sequence_number_received == (last_received + 1):
                logging.debug('Recibido segmento ' + str(sequence_number_received) + " y escribiendo en archivo")
                file.write(payload)
                last_received = sequence_number_received
                self.client_socket.sendto(("ACK" + str(sequence_number_received).zfill(32)).encode(FORMAT), client_address)
                logging.debug('ACK enviado para ' + str(sequence_number_received))
            elif sequence_number_received <= last_received:
                self.client_socket.sendto(("ACK" + str(last_received).zfill(32)).encode(FORMAT), client_address)
                logging.debug('ACK enviado por repetido ' + str(last_received) + ' paquete ya recibido con anterioridad numero ' + str(sequence_number_received))
            else:
                self.client_socket.sendto(("ACK" + str(last_received).zfill(32)).encode(FORMAT), client_address)
                logging.debug('ACK enviado por repetido ' + str(last_received))

        # File finished goodbye handshake
        self.client_socket.sendto(("ACK" + str(last_received).zfill(32)).encode(FORMAT), client_address)
        finished_connection = False
        retries = 0
        while not finished_connection:
            ready = select.select([self.client_socket], [], [], 5)
            print('Esperando ACK de cierre de conexion')
            if ready[0]:
                print('Llego ACK de cierre de conexion + {}'.format(self.server_port))
                msg, server_address = self.client_socket.recvfrom(35)
                # header = method(), isLast(), ACK
                # print(server_address)
                is_last = int(msg[1:2].decode(FORMAT))
                is_ack = str(msg[2:].decode(FORMAT)).replace('0','')
                print(is_ack)
                print(is_last)
                if is_ack == "ACK" and is_last == 1:
                    break
                else:
                    print("Envio ultimo ACK con numero de secuencia " + str(last_received) + " por llegada de ACK erroneo")
                    self.client_socket.sendto(("ACK" + str(last_received).zfill(32)).encode(FORMAT), client_address)
            else:
                print("Envio ultimo ACK con numero de secuencia " + str(last_received) + " por {} vez por timeout".format(retries))
                self.client_socket.sendto(("ACK" + str(last_received).zfill(32)).encode(FORMAT), client_address)
                retries += 1
                if retries == MAX_RETRIES + 2:
                    break

        logging.info("Archivo completo recibido -> "+ self.file_path)
        return 
    
    def client_solicit(self, method):
        connected = False
        retries = 0
        while not connected: 
            header = bytes(str(method) + '0' + str(0).zfill(32) + str(self.file_name).zfill(32), FORMAT)
            self.client_socket.sendto(header, (self.server_name, self.server_port))

            ready = select.select([self.client_socket], [], [], 5)
            if ready[0]:
                msg, server_address = self.client_socket.recvfrom(35)
                # ack = "ACK" + str(0)
                self.server_port = server_address[1]
                command = str(msg[0:3].decode(FORMAT))
                if command == "ERR":
                    command_error_code = int(msg[3:].decode(FORMAT))
                    raise Exception('Dowload failed: ' + self.command_errors[command_error_code])
                if command != "ACK":
                    raise Exception('Handsake fallido')
                ack_number = int(msg[3:].decode(FORMAT))
                connected = True
            else:
                logging.warning('No se pudo conectar con el servidor')
                retries += 1
                if retries == MAX_RETRIES:
                    raise Exception('No se pudo conectar con el servidor, dejo de internar')
        return 

    # def sender_send(self): 
    # Use by the client to send a file
    def client_send(self):
        
        try:
            self.client_solicit(UPLOAD_CODE)
        except Exception as e:
            logging.warning(e)
            return

        try:
            thread_recieve = Thread(target=self.sender_receive, daemon=True)
            thread_recieve.start()
            thread_send = Thread(target=self.sender_send, daemon=True)
            thread_send.start()

            thread_send.join()
            thread_recieve.join()

            return
        except Exception as e:
            print(e)
            raise e

    # def client_receive(self):
    # Use by the client to receive a file
    def client_receive(self,dest_path):
        
        try:
            self.client_solicit(DOWNLOAD_CODE)
        except Exception as e:
            logging.warning(e)
            return

        file = open(os.path.join(dest_path, self.file_path), 'wb')
        
        self.receiver_receive(file)
        
        file.close()
            
        return


    # def server_send(self):
    # Use by the server to send a file
    def server_send(self,dest):
        
        logging.info('Conexion aceptada para enviar archivo en puerto ' + str(self.client_socket.getsockname()[1]))
        try:
            self.dest = dest
            thread_sender = Thread(target=self.sender_send, daemon=True)
            thread_sender.start()
            thread_reciever = Thread(target=self.sender_receive, daemon=True)
            thread_reciever.start()

            thread_sender.join()
            thread_reciever.join()
        except Exception as e:
            print(e)
            return
    
    # def server_receive(self):
    # Use by the server to receive a file
    def server_receive(self,dest_path):
        # method(1), isLast(1), secuenceNumber(32), data(PAYLOAD_SIZE)
        file = open(os.path.join(dest_path, self.file_path), 'wb')
        logging.info('Recibiendo archivo con go back n: ' + self.file_path)
        last_received = 0
        finished = False
        self.client_socket.sendto(("ACK" + str("0").zfill(32)).encode(FORMAT), (self.server_name, self.server_port))

        logging.info('Conexion aceptada para recibir archivo en puerto ' + str(self.client_socket.getsockname()[1]))

        self.receiver_receive(file)    
        file.close()
        logging.info("Archivo completo recibido -> "+ self.file_path)

def recive_file(reciver_socket, sender_address, file_name, file_dest_path):
    end_of_file = False
    file = open(os.path.join(file_dest_path, file_name), 'wb')
    ack = 1
    while not end_of_file:
        reciver_socket.sendto(str(ack).encode(FORMAT), sender_address)
        logging.debug("Enviado ACK-> " + str(ack))
        # wait next segment
        msg, sender_address = reciver_socket.recvfrom(1024)
        if len(msg) < 66:
            logging.warning("Mensaje incompleto")
            logging.debug("Error -> " + msg.decode(FORMAT))
            os.remove(os.path.join(file_dest_path, file_name))
            break
        payload = msg[66:]
        if ack < int(msg[3:34].decode(FORMAT)):
            file.write(payload)
            ack = int(msg[3:34].decode(FORMAT))
        logging.debug("Recibido ACK-> "+ str(ack))
        end_of_file = (int(msg[1:2].decode(FORMAT)) == 1)
    file.close()
    if end_of_file:
        reciver_socket.sendto(str(ack).encode(FORMAT), sender_address)
        logging.debug("Enviado ultimo ACK -> " + str(ack))
        logging.info("Archivo completo -> "+ file_name)
    else:
        logging.warning("Archivo incompleto")
    reciver_socket.close()
