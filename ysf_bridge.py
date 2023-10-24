#!/usr/bin/python3

#    ysf_bridge
#
#    Created by Antonio Matraia (IU5JAE) on 25/07/2020.
#    Copyright 2020 Antonio Matraia (IU5JAE). All rights reserved.

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import threading
import time
import logging
import socket
import sys
import queue
import configparser
from logging.handlers import RotatingFileHandler
import signal
import ysffich
import ysfpayload
import hashlib

ver = '231015'

a_connesso = False
b_connesso = False

a_tf = 0.0 # tempo trascorso da ultimo pacchetto
b_tf = 0.0

q_ab = queue.Queue() # coda pacchetti A -> B 
q_ba = queue.Queue() # coda pacchetti B -> A 

lock_a = threading.Lock()
lock_b = threading.Lock()
lock_a_time = threading.Lock()
lock_b_time = threading.Lock()
lock_conn_a = threading.Lock()
lock_conn_b = threading.Lock()
lock_dir = threading.Lock()
a_b_dir = False # direzione attiva A --> B
b_a_dir = False # direzione attiva B --> A
bufferSize = 2048

## config
config = configparser.ConfigParser()

if (len(sys.argv) != 2):
  print('Invalid Number of Arguments')
  logging.error('Invalid Number of Arguments')
  print('use: ysf_bridge <configuration file>')
  logging.error('use: ysf_bridge <configuration file>')
  sys.exit()
  
config_file = sys.argv[1].strip()
config.read(config_file)
log_file = config['general']['log_file'] 


try:
  log_maxBytes = int(config['general']['log_maxBytes'])
except:
  log_maxBytes = 1000000
try:    
  log_backupCount = int(config['general']['log_backupCount'])
except:
  log_backupCount = 10  

try:
  ack_period = float(config['general']['ack_period'])
except:
  ack_period = 3.0
  
try:
  ack_tout = float(config['general']['ack_tout'])
except:
  ack_tout = 30.0  
  
ack_time_a = ack_tout 
ack_time_b = ack_tout 


# "A" side
UDP_IP_A = config['A']['address']
try:
  UDP_PORT_A = int(config['A']['port'])
except:
  UDP_PORT_A = 42000
    
CALL_A = config['A']['call'] 
try:
  YCS_A = int(config['A']['ycs_connection'])
except:
  YCS_A = 0

try:
  REM_PREF_A = int(config['A']['remove_prefix'])
except:
  REM_PREF_A = 0

try:
  YCS_ID_A = int(config['A']['ycs_ID'])
except:
  YCS_ID_A = 0    

try:
  RX_A = config['A']['rx_freq'][:9].ljust(9)
except:
  RX_A = ' '.ljust(9)

try:  
  TX_A = config['A']['tx_freq'][:9].ljust(9)
except:
  TX_A = ' '.ljust(9)

try:
  LOC_A = config['A']['locator'][:6].ljust(6)
except:
  LOC_A = ' '.ljust(6)

try:
  LOCATION_A = config['A']['location'][:20].ljust(20)
except:
  LOCATION_A = ' '.ljust(20)
  
try:
  HS_TY_A = config['A']['hs_type'][:12].ljust(12)
except:
  HS_TY_A = ' '.ljust(12)

try:
  YSFG_ID_A = config['A']['ysfgateway_ID'][:7].ljust(7)
except:
  YSFG_ID_A = ' '.ljust(7)

# enable authentication style BM direct
try:
  AUTH_A = int(config['A']['auth'])
except:
  AUTH_A = 0

try:
  PASSWORD_A = bytes(config['A']['password'].strip(), 'utf-8')
except:
  PASSWORD_A = bytes('', 'utf-8')
  
try:
  OPTIONS_A = config['A']['options']
except:
  OPTIONS_A = ''


# "B" side
UDP_IP_B = config['B']['address']
try:
  UDP_PORT_B = int(config['B']['port'])
except:
  UDP_PORT_B = 42000
  
CALL_B = config['B']['call'] 

try:
  YCS_B = int(config['B']['ycs_connection'])
except:
  YCS_B = 0

try:
  REM_PREF_B = int(config['B']['remove_prefix'])
except:
  REM_PREF_B = 0


try:
  YCS_ID_B = int(config['B']['ycs_ID'])
except:
  YCS_ID_B = 0    
  
try:
  RX_B = config['B']['rx_freq'][:9].ljust(9)
except:
  RX_B = ' '.ljust(9)

try:  
  TX_B = config['B']['tx_freq'][:9].ljust(9)
except:
  TX_B = ' '.ljust(9)

try:
  LOC_B = config['B']['locator'][:6].ljust(6)
except:
  LOC_B = ' '.ljust(6)

try:
  LOCATION_B = config['B']['location'][:20].ljust(20)
except:
  LOCATION_B = ' '.ljust(20)
  
try:
  HS_TY_B = config['B']['hs_type'][:12].ljust(12)
except:
  HS_TY_B = ' '.ljust(12)

try:
  YSFG_ID_B = config['B']['ysfgateway_ID'][:7].ljust(7)
except:
  YSFG_ID_B = ' '.ljust(7)


##log
logging.basicConfig(handlers=[RotatingFileHandler(log_file, maxBytes=log_maxBytes, backupCount=log_backupCount)], format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.INFO)


while (len(CALL_A) != 10):
	CALL_A += ' '

while (len(CALL_B) != 10):
	CALL_B += ' '
if (AUTH_A == 1):    
  MESSAGE_A = 'YSFL' + CALL_A # stringa connessione "A"
else:  
  MESSAGE_A = 'YSFP' + CALL_A # stringa connessione "A"

MESSAGE_B = 'YSFP' + CALL_B   # stringa connessione "B"

DISCONN_A = 'YSFU'  # stringa disconnessione "A"
DISCONN_B = 'YSFU'  # stringa disconnessione "B"

if (AUTH_A == 1):
  ACK_A =   '              '
else:  
  ACK_A = 'YSFPREFLECTOR '
#ACK_A =   'YSFPBM_2222  '


ACK_B = 'YSFPREFLECTOR '

#CALL_A = CALL_A.strip()
#CALL_B = CALL_B.strip()

keepalive_str_a = 'YSFP' + CALL_A
keepalive_str_b = 'YSFP' + CALL_B 


# socket connessione A
sock_a = socket.socket(socket.AF_INET, 
                        socket.SOCK_DGRAM) 

sock_a.settimeout(ack_tout + 10.0)

# socket connessione B
sock_b = socket.socket(socket.AF_INET, 
                        socket.SOCK_DGRAM) 

sock_b.settimeout(ack_tout + 10.0)

ycs_a_down = False
ycs_b_down = False

a_connecting = True
b_connecting = True

def signal_handler(signal, frame):
  global run, a_connesso, b_connesso, arresto
  logging.info('Arresto in corso ...')
  arresto = True
  time.sleep(0.5)
  if a_connesso:
    q_ba.put(str.encode(DISCONN_A))
    logging.info('Disconnessione da A')
    time.sleep(1)
    a_connesso = False
  if b_connesso:
    q_ab.put(str.encode(DISCONN_B))
    logging.info('Disconnessione da B')
    time.sleep(1)
    b_connesso = False
  if ((not a_connesso) and (not b_connesso)):
    run = False
 

def conn (sock, lato):
    global a_connesso, b_connesso, ACK_A
    if ((lato == 'A') and (AUTH_A == 0)):
      logging.info('conn: provo a connettere A') 
      try:
        sock.sendto(str.encode(MESSAGE_A), (UDP_IP_A, UDP_PORT_A))
        msgFromServer = sock.recvfrom(bufferSize)
        sock_err = False
      except Exception as e:
        logging.error('conn: Errore connessione A ' + str(e))
        sock_err = True
      if (not sock_err):  
        
        # scelgo la stringa giusta da verificare
        
        msg = msgFromServer[0][0:14]
        
        if (msg == str.encode(ACK_A)):
          if (YCS_A == 1) and (YCS_ID_A > 0):
            s_ycs = 'YSFO' + CALL_A.ljust(10) + (str(YCS_ID_A) + ';').ljust(36)
            try:
              sock.sendto(str.encode(s_ycs), (UDP_IP_A, UDP_PORT_A))  
            except Exception as e:
              logging.error('conn: Errore connessione A YCS STR 1 ' + str(e))
              sock_err = True
            if (not sock_err):
              logging.info('connesso A')
              lock_conn_a.acquire()
              a_connesso = True
              lock_conn_a.release()  
              a_connecting = True           
              try: 
                sock.sendto(str.encode('YSFI' + CALL_A.ljust(10) + RX_A + TX_A + LOC_A + LOCATION_A + HS_TY_A + YSFG_ID_A + '   '), (UDP_IP_A, UDP_PORT_A))
              except Exception as e:
                logging.error('conn: Errore connessione A YCS STR 2 ' + str(e))   
          else:
            logging.info('connesso A')
            lock_conn_a.acquire()
            a_connesso = True
            lock_conn_a.release() 
            a_connecting = True    
          lock_a.acquire()
          ack_time_a = 0
          lock_a.release()
  
    # Connection to BM YSF DIRECT
    if ((lato == 'A') and (AUTH_A == 1)):
      logging.info('conn: provo a connettere A') 
      try:
        sock.sendto(str.encode(MESSAGE_A), (UDP_IP_A, UDP_PORT_A))
        # print(str.encode(MESSAGE_A))
        msgFromServer = sock.recvfrom(bufferSize)
        # print(msgFromServer[0])
        sock_err = False
      except Exception as e:
        logging.error('conn: Errore connessione A ' + str(e))
        sock_err = True
      if (not sock_err):  
        msg = msgFromServer[0][0:16]
        # print(msg)
        if ((len(msg) == 16) and (msg[0:6] == b'YSFACK')):
          ACK_A = 'YSFP' + msg[6:16].decode("utf-8") 
          key = msgFromServer[0][16:20]
          s_auth = bytes('YSFK' + CALL_A.ljust(10), 'utf-8') + hashlib.sha256(key + PASSWORD_A).digest() 
          
          try:
            sock.sendto(s_auth, (UDP_IP_A, UDP_PORT_A))
           # print(s_auth)
            msgFromServer = sock.recvfrom(bufferSize)
            # print(msgFromServer[0])
          except Exception as e:
            logging.error('conn: Errore connessione A BM invio password ' + str(e))
            sock_err = True
          # print(str.encode('YSFACK' + ACK_A[4:14]))
          if ((not sock_err) and (len(msg) == 16) and (msg[0:16] == str.encode('YSFACK' + ACK_A[4:14]))): 
            s_ycs = 'YSFO' + CALL_A.ljust(10) + OPTIONS_A
            try:
              sock.sendto(str.encode(s_ycs), (UDP_IP_A, UDP_PORT_A))
              msgFromServer = sock.recvfrom(bufferSize)
            except Exception as e:
              logging.error('conn: Errore connessione A BM invio Options ' + str(e))
              sock_err = True
           
            
            if ((not sock_err) and (len(msg) == 16) and (msg[0:16] == str.encode('YSFACK' + ACK_A[4:14]))):
              logging.info('connesso A')
              lock_conn_a.acquire()
              a_connesso = True
              lock_conn_a.release()  
              a_connecting = True           
                 
              lock_a.acquire()
              ack_time_a = 0
              lock_a.release()


         
    if (lato == 'B'): 
      logging.info('conn: provo a connettere B')
      try:
        sock.sendto(str.encode(MESSAGE_B), (UDP_IP_B, UDP_PORT_B))
        msgFromServer = sock.recvfrom(bufferSize)
        sock_err = False
      except Exception as e:
        logging.error('conn: Errore connessione B ' + str(e))  
        sock_err = True
      if (not sock_err):  
        
        msg = msgFromServer[0][0:14]
        
        if (msg == str.encode(ACK_B)):
          if (YCS_B == 1) and (YCS_ID_B > 0):
            s_ycs = 'YSFO' + CALL_B.ljust(10) + (str(YCS_ID_B) + ';').ljust(36)
            try:
              sock.sendto(str.encode(s_ycs), (UDP_IP_B, UDP_PORT_B))  
            except Exception as e:
              logging.error('conn: Errore connessione B YCS STR 1 ' + str(e))
              sock_err = True
            if (not sock_err):  
              logging.info('connesso B')
              lock_conn_b.acquire()
              b_connesso = True
              lock_conn_b.release()
              b_connecting = True 
              try:
                sock.sendto(str.encode('YSFI' + CALL_B.ljust(10) + RX_B + TX_B + LOC_B + LOCATION_B + HS_TY_B + YSFG_ID_B + '   '), (UDP_IP_B, UDP_PORT_B))
              except Exception as e:
                logging.error('conn: Errore connessione B YCS STR 2 ' + str(e))      
          else:
            logging.info('connesso B')
            lock_conn_b.acquire()
            b_connesso = True
            lock_conn_b.release()
            b_connecting = True 
          lock_b.acquire()
          ack_time_b = 0
          lock_b.release()

# invio dati a "A"
def send_a():
  while True:
    msg = q_ba.get()
    try: 
      sock_a.sendto(msg, (UDP_IP_A, UDP_PORT_A))
    except Exception as e:
      logging.error('send_a: errore invio ad A ' + str(e))

# invio dati a "B" 
def send_b():
  while True:
    msg = q_ab.get()
    try: 
      sock_b.sendto(msg, (UDP_IP_B, UDP_PORT_B))
    except Exception as e:
      logging.error('send_b: errore invio a B ' + str(e))

def rcv_a():
  global a_connesso, b_connesso, a_b_dir, b_a_dir, ack_time_a, a_tf, b_tf, ycs_a_down, a_connecting
  while True:
    if a_connesso:  
      try:
        msgFromServer = sock_a.recvfrom(bufferSize)
        #print(msgFromServer[0])
        if ((len(msgFromServer[0]) == 14) and (msgFromServer[0][0:14] == str.encode(ACK_A))):
          if ((ack_time_a < (1.1 * ack_period)) and ycs_a_down):
            ycs_a_down = False
            logging.info('rcv_a: Send YSO string for YCS_A down')
            s_ycs = 'YSFO' + CALL_A.ljust(10) + (str(YCS_ID_A) + ';').ljust(36)
            q_ba.put(str.encode(s_ycs)) 
          
          if (a_connecting):
            a_connecting = False
               
          lock_a.acquire()
          ack_time_a = 0
          lock_a.release()
       
        if (msgFromServer[0][0:4] == b'YSFD'):
          # print(msgFromServer[0])
          if ysffich.decode(msgFromServer[0][40:]): 
            FI = ysffich.getFI()
            SQL = ysffich.getSQ()
            VOIP = ysffich.getVoIP()
            FN = ysffich.getFN()
            DT = ysffich.getDT()
            # print('FI: ' + str(ysffich.getFI()) + ' - DT: ' + str(ysffich.getDT()))
            # print(msgFromServer[0])
            # print('*****')
            if (((YCS_A == 1) and ((SQL == YCS_ID_A) or (SQL == 0))) or (YCS_A == 0)):
              if (YCS_B == 1):
                ysffich.setSQ(YCS_ID_B)  
              if ((YCS_B == 0) and (SQL != 0)):
                ysffich.setSQ(0)
              ysffich.setVoIP(False)
              bya_msg = bytearray(msgFromServer[0])   
              ysffich.encode(bya_msg)
              if ((not a_b_dir) and (not b_a_dir) and (FI != 2)):  # new stream and bridge free
                if (FI == 0):  # valid HC
                  lock_dir.acquire()
                  a_b_dir = True
                  b_a_dir = False
                  lock_dir.release()
                else: # HC missing  
                  logging.error('rcv_a: add missing HC at ' + bya_msg[4:14].decode() + ' from ' + bya_msg[14:24].decode() + ' to ' + bya_msg[24:34].decode())
                  # print(bya_msg)
                  data = [0] * 120
                  csd1 = [0] * 20
                  csd2 = [0] * 20
                  csd1 = (bya_msg[24:34] + bya_msg[14:24])  # destination/source
                  csd2 = ('          ' + '          ').encode()  # downlink/uplink
                  try:
                    ysfpayload.writeHeader(data, csd1, csd2)
                    bya_msg[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
                  except Exception as e:
                    logging.error('rcv_a: error writing missing HC ' + str(e))
                  # print('setto direzioni')
                  ysffich.setFI(0)
                  ysffich.encode(bya_msg)
                  # print(bya_msg)
                  lock_dir.acquire()
                  a_b_dir = True
                  b_a_dir = False
                  lock_dir.release()
                  
            # clean dgid prefix  
              if ((YCS_A == 1) or (REM_PREF_A == 1)):
                if ((FN == 1) and (DT == 2)):
                  dt = [0] * 10
                  ysfpayload.readDataVDModeData2(bya_msg[35:], dt)  
                  src_orig = ''
                  for c in dt:
                    if ((c > 31) and (c < 127)):
                      src_orig = src_orig + chr(c)
                    else:
                      src_orig = src_orig + chr(32)
                      
                  src_spl = src_orig.split('/')
                  if ((len(src_spl) > 1) and src_spl[0].isnumeric()):
                    dgid = int(src_spl[0])
                    if ((dgid > 0) and (dgid < 100)):
                      data_np = bya_msg[35:]
                      src = str(src_spl[1]).ljust(10).encode()
                      ysfpayload.writeVDMmode2Data(data_np, src)
                      data_mod = bytearray(155)  
                      bya_msg[35:] = data_np     
                  
              lock_b_time.acquire()
              b_tf = 0.0
              lock_b_time.release()
              if (a_connesso and b_connesso and a_b_dir):
                bya_msg[4:14] = str.encode(CALL_B.ljust(10))
                q_ab.put(bytes(bya_msg))    
       
              if (FI == 2):
                lock_dir.acquire()
                a_b_dir = False
                b_a_dir = False
                lock_dir.release()  
            if ((YCS_A == 1) and (SQL != YCS_ID_A) and (SQL != 0)):
              s_ycs = 'YSFO' + CALL_A.ljust(10) + (str(YCS_ID_A) + ';').ljust(36)
              q_ba.put(str.encode(s_ycs))
          else:
            logging.error('rcv_a: error decoding FICH')  
      except Exception as e:
        logging.error('rcv_a: ' + str(e))
        
    else:
      time.sleep(1.0)   


def rcv_b():
  global a_connesso, b_connesso, a_b_dir, b_a_dir, ack_time_b, a_tf, b_tf, ycs_b_down, b_connecting
  while True:
    if b_connesso:
      try:
        msgFromServer = sock_b.recvfrom(bufferSize)
        # print(msgFromServer[0]) 
        if ((len(msgFromServer[0]) == 14) and (msgFromServer[0][0:14] == str.encode(ACK_B))):
          if ((ack_time_b < (1.1 * ack_period)) and ycs_b_down):
            ycs_b_down = False
            logging.info('rcv_b: Send YSO string for YCS_B down')
            s_ycs = 'YSFO' + CALL_B.ljust(10) + (str(YCS_ID_B) + ';').ljust(36)
            q_ab.put(str.encode(s_ycs)) 
          if (b_connecting):
            b_connecting = False
          
          lock_b.acquire()
          ack_time_b = 0
          lock_b.release()
          
        if (msgFromServer[0][0:4] == b'YSFD'):
          if ysffich.decode(msgFromServer[0][40:]): 
            FI = ysffich.getFI()
            SQL = ysffich.getSQ()
            VOIP = ysffich.getVoIP()
            FN = ysffich.getFN()
            DT = ysffich.getDT()
            if (((YCS_B == 1) and ((SQL == YCS_ID_B) or (SQL == 0))) or (YCS_B == 0)):              
              if (YCS_A == 1):
                ysffich.setSQ(YCS_ID_A)  
              if ((YCS_A == 0) and (SQL != 0)):
                ysffich.setSQ(0)
              ysffich.setVoIP(False)
              bya_msg = bytearray(msgFromServer[0])   
              ysffich.encode(bya_msg)
              if ((not a_b_dir) and (not b_a_dir) and (FI != 2)):  # header and bridge free
                if (FI == 0):
                  lock_dir.acquire()
                  a_b_dir = False
                  b_a_dir = True
                  lock_dir.release()
                else:
                  logging.error('rcv_b: add missing HC at ' + bya_msg[4:14].decode() + ' from ' + bya_msg[14:24].decode() + ' to ' + bya_msg[24:34].decode())
                  # print(bya_msg)
                  data = [0] * 120
                  csd1 = [0] * 20
                  csd2 = [0] * 20
                  csd1 = (bya_msg[24:34] + bya_msg[14:24])  # destination/source
                  csd2 = ('          ' + '          ').encode()  # downlink/uplink
                  try:
                    ysfpayload.writeHeader(data, csd1, csd2)
                    bya_msg[35 + ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:] = data[ysfpayload.YSF_SYNC_LENGTH_BYTES + ysfpayload.YSF_FICH_LENGTH_BYTES:]
                  except Exception as e:
                    logging.error('rcv_b: error writing missing HC ' + str(e))
                  ysffich.setFI(0)
                  ysffich.encode(bya_msg)
                  # print('setto direzioni')
                  # print(bya_msg)
                  lock_dir.acquire()
                  a_b_dir = False
                  b_a_dir = True
                  lock_dir.release()

                  
            # clean dgid prefix  
              if ((YCS_B == 1) or (REM_PREF_B == 1)):
                if ((FN == 1) and (DT == 2)):
                  dt = [0] * 10
                  ysfpayload.readDataVDModeData2(bya_msg[35:], dt)  
                  src_orig = ''
                  for c in dt:
                    if ((c > 31) and (c < 127)):
                      src_orig = src_orig + chr(c)
                    else:
                      src_orig = src_orig + chr(32)
                      
                  src_spl = src_orig.split('/')
                  if ((len(src_spl) > 1) and src_spl[0].isnumeric()):
                    dgid = int(src_spl[0])
                    if ((dgid > 0) and (dgid < 100)):
                      data_np = bya_msg[35:]
                      src = str(src_spl[1]).ljust(10).encode()
                      ysfpayload.writeVDMmode2Data(data_np, src)
                      data_mod = bytearray(155)  
                      bya_msg[35:] = data_np     
                    
              lock_a_time.acquire()
              a_tf = 0.0
              lock_a_time.release()
              
              
              if (a_connesso and b_connesso and b_a_dir):
                bya_msg[4:14] = str.encode(CALL_A.ljust(10))
                q_ba.put(bytes(bya_msg))    
            
   
              if (FI == 2):
                lock_dir.acquire()
                a_b_dir = False
                b_a_dir = False
                lock_dir.release()  
            if ((YCS_B == 1) and (SQL != YCS_ID_B) and (SQL != 0)):
              s_ycs = 'YSFO' + CALL_B.ljust(10) + (str(YCS_ID_B) + ';').ljust(36)
              q_ab.put(str.encode(s_ycs))
          else:
             logging.error('rcv_b: error decoding FICH')  
      except Exception as e:
        logging.error('rcv_b: ' + str(e))
    else:
      time.sleep(1.0)


# clock per gestione keepalive
def clock ():
 global ack_time_a, ack_time_b, ack_tout, a_tf, b_tf, a_b_dir, b_a_dir, ycs_a_down, ycs_b_down
 t = ack_tout * 1.1
 while 1:
     if (a_tf < 5.0):
       lock_a_time.acquire()
       a_tf += 0.1
       lock_a_time.release()  
       
     if ((a_tf > 2.0) and (b_a_dir == True)):
       lock_dir.acquire()
       b_a_dir = False
       lock_dir.release()    
         
     if (b_tf < 5.0):
       lock_b_time.acquire()
       b_tf += 0.1
       lock_b_time.release()
       
     if ((b_tf > 2.0) and (a_b_dir == True)):
         lock_dir.acquire()
         a_b_dir = False
         lock_dir.release()   
         
     if (ack_time_a < t):   
       lock_a.acquire()
       ack_time_a +=0.1
       lock_a.release()
     if (ack_time_b < t):     
       lock_b.acquire()
       ack_time_b +=0.1
       lock_b.release()
     
     if ((YCS_A == 1) and (ack_time_a > (ack_period * 1.5)) and a_connesso and not ycs_a_down and not a_connecting):
       ycs_a_down = True
       logging.info('clock: YCS_A Down')
     if ((YCS_B == 1) and (ack_time_b > (ack_period * 1.5)) and b_connesso and not ycs_b_down and not b_connecting):
       ycs_b_down = True  
       logging.info('clock: YCS_B Down')
      
     time.sleep(0.1)

# controllo connessioni
def check_conn():
  global a_connesso, b_connesso  
  while True:
    if (ack_time_a > ack_tout):
      logging.info('check_conn: Timeout - Connetto A')
      lock_conn_a.acquire()
      a_connesso = False
      lock_conn_a.release()
      conn (sock_a, 'A')    
    if (ack_time_b > ack_tout):
      logging.info('check_conn: Timeout - Connetto B')
      lock_conn_b.acquire()
      b_connesso = False
      lock_conn_b.release()
      conn (sock_b, 'B')
    time.sleep(ack_tout/2.0)

# invio pacchetti keepalive
def keepalive():
  global ack_time_a, ack_time_b   
  ncnt = 0
  while True:
    ncnt += 1
    if (a_connesso and not arresto):
        q_ba.put(str.encode(keepalive_str_a))
       # print(str.encode(keepalive_str_a))
        if (YCS_A == 1) and (YCS_ID_A > 0) and (ncnt >= 5):
          s_ycs = 'YSFO' + CALL_A.ljust(10) + (str(YCS_ID_A) + ';').ljust(36)
          q_ba.put(str.encode(s_ycs))
        
    if (b_connesso and not arresto):
        q_ab.put(str.encode(keepalive_str_b))
        if (YCS_B == 1) and (YCS_ID_B > 0) and (ncnt >= 5):
          s_ycs = 'YSFO' + CALL_B.ljust(10) + (str(YCS_ID_B) + ';').ljust(36)
          q_ab.put(str.encode(s_ycs))
    
    
    if (ncnt >= 10):
      ncnt = 0
       
    time.sleep(ack_period)  


run = True
arresto = False
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

t_clock = threading.Thread(target = clock)
t_clock.daemon = True
t_conn = threading.Thread(target = check_conn)
t_conn.daemon = True
t_keep = threading.Thread(target = keepalive)
t_keep.daemon = True
t_send_a = threading.Thread(target = send_a)
t_send_a.daemon = True
t_send_b = threading.Thread(target = send_b)
t_send_b.daemon = True
t_rcv_a = threading.Thread(target = rcv_a)
t_rcv_a.daemon = True
t_rcv_b = threading.Thread(target = rcv_b)
t_rcv_b.daemon = True


logging.info('YSF Bridge Ver. ' + ver + ' : avvio')



t_clock.start() 
t_conn.start()
t_keep.start()
t_send_a.start()
t_send_b.start()
t_rcv_a.start()
t_rcv_b.start()



while run:
  time.sleep(3.0)
logging.info('ysf_bridge correttamente arrestato')

