#!/usr/bin/python3
# client_bw2.py
# Echo client program UDP
# Version con dos threads: uno lee de <input_file> hacia el socket y el otro del socket a <output_file>
import jsockets
import socket
import sys, threading

valid = 1

def Rdr(s, output_file, size):
    with open(output_file, "wb") as f:
        global valid
        s.settimeout(3)
        while True:
            try:
                data = s.recv(size)
            except socket.timeout:
                valid = 0
                break
            except Exception as e:
                print(f"Error: {e}")
                continue
            if not data: 
                break
            f.write(data)

if len(sys.argv) != 6:
    print('Use: '+sys.argv[0]+' <size> <input_file> <output_file> <host> <port>')
    sys.exit(1)

s = jsockets.socket_udp_connect(sys.argv[4], sys.argv[5])
if s is None:
    print('could not open socket')
    sys.exit(1)

size = int(sys.argv[1])

# Creo thread que lee desde el socket hacia <output_file>:
newthread = threading.Thread(target=Rdr, args=(s, sys.argv[3], size))
newthread.start()

# En este otro thread leo desde <input_file> hacia socket:
with open(sys.argv[2], "rb") as f:
    while True:
        chunk = f.read(size)
        if not chunk:
            break
        try:
            s.send(chunk)
        except Exception as e:
            print(f"Error: {e}")
            continue
    s.send(b"")

newthread.join()              # Espera que el thread termine
s.close()

if not valid:
    print("Medición inválida por timeout")