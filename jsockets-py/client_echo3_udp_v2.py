#!/usr/bin/python3
# Echo client program (modificado para leer cualquier archivo binario)
# Version con dos threads: uno lee de stdin hacia el socket y el otro al revés
import jsockets
import sys, threading
import time

def Rdr(s, output_file):
    with open(output_file, "wb") as f:
        while True:
            try:
                data = s.recv(1024)
            except:
                data = None
            if not data: 
                break
            f.write(data)

if len(sys.argv) != 5:
    print('Use: '+sys.argv[0]+' <host> <port> <input_file> <output_file>')
    sys.exit(1)

s = jsockets.socket_udp_connect(sys.argv[1], sys.argv[2])
if s is None:
    print('could not open socket')
    sys.exit(1)

# Esto es para dejar tiempo al server para conectar el socket
s.send(b'hola')
s.recv(1024)

# Creo thread que lee desde el socket hacia stdout:
output_file = sys.argv[4]
newthread = threading.Thread(target=Rdr, args=(s, output_file))
newthread.start()

# En este otro thread leo desde archivo hacia socket:
with open(sys.argv[3], "rb") as f:
    while True:
        chunk = f.read(1024)
        if not chunk:
            break
        try:
            s.send(chunk)
        except:
            continue

time.sleep(3)  # dar tiempo para que vuelva la respuesta
s.close()

