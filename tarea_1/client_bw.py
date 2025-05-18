#!/usr/bin/python3
# Echo client program
# Version con dos threads: uno lee de stdin hacia el socket y el otro al revés
import jsockets
import sys, threading
import time
import os

bytes_enviados = 0
bytes_recibidos = 0

def Rdr(s, output_file, size, file_size):
    with open(output_file, "wb") as f:
        global bytes_recibidos
        while bytes_recibidos < file_size:
            try:
                data = s.recv(size)
            except:
                continue
            if not data: 
                break
            f.write(data)
            bytes_recibidos += len(data)

if len(sys.argv) != 6:
    print('Use: '+sys.argv[0]+' <size> <input_file> <output_file> <host> <port>')
    sys.exit(1)

s = jsockets.socket_tcp_connect(sys.argv[4], sys.argv[5])
if s is None:
    print('could not open socket')
    sys.exit(1)

size = int(sys.argv[1])
file_size = os.path.getsize(sys.argv[2])

# Creo thread que lee desde el socket hacia <output_file>:
newthread = threading.Thread(target=Rdr, args=(s, sys.argv[3], size, file_size))
newthread.start()

# En este otro thread leo desde <input_file> hacia socket:
with open(sys.argv[2], "rb") as f:
    while True:
        chunk = f.read(size)
        if not chunk:
            break
        try:
            s.send(chunk)
            bytes_enviados += len(chunk)
        except:
            continue

newthread.join()              # Espera que el thread termine
s.close()

print(f"Bytes enviados: {bytes_enviados}")
print(f"Bytes recibidos: {bytes_recibidos}")