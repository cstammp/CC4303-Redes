#!/usr/bin/python3
# client_bw3.py
# Echo client program UDP with Stop&Wait
# Version con dos threads: uno lee de <input_file> hacia el socket y el otro del socket a <output_file>
import jsockets
import socket
import sys, threading
import time
import os
import fcntl

seq = "000"
last_ack = None
error_count = 0
total_sent_packages = 0
valid = 1

# Lock y condición para sincronización entre threads
lock = threading.Lock()
cond = threading.Condition(lock)

def next_seq(seq):
	return f"{(int(seq) + 1) % 1000:03d}"

def Rdr(s, output_file, size):
	global last_ack, valid
	expected_seq = "000"
	s.settimeout(3)
	with open(output_file, "wb") as f:
		while True:
			try:
				data = s.recv(size + 3)
			except socket.timeout:
				valid = 0
				break
			except Exception as e:
				print(f"Error: {e}")
				continue
			if not data: 
				break

			recv_seq = data[:3].decode()
			payload = data[3:]
			with cond:
				last_ack = recv_seq
				cond.notify()
			# EOF
			if not payload:
				break
			if recv_seq == expected_seq:    # Evita duplicados
				f.write(payload)
				expected_seq = next_seq(expected_seq)



if len(sys.argv) != 7:
	print('Use: '+sys.argv[0]+' <size> <timeout> <input_file> <output_file> <host> <port>')
	sys.exit(1)

s = jsockets.socket_udp_connect(sys.argv[5], sys.argv[6])
if s is None:
	print('could not open socket')
	sys.exit(1)

size = int(sys.argv[1])
timeout = float(sys.argv[2])

# Creo thread que lee desde el socket hacia <output_file>:
newthread = threading.Thread(target=Rdr, args=(s, sys.argv[4], size))
newthread.start()

# En este otro thread leo desde <input_file> hacia socket:
with open(sys.argv[3], "rb") as f:
	while True:
		data = f.read(size)
		chunk = seq.encode() + data
		valid_ack = False
		while not valid_ack:
			try:
				s.send(chunk)
				total_sent_packages += 1
			except Exception as e:
				print(f"Error: {e}")
				continue

			with cond:
				cond.wait(timeout)
				if not valid:
					break
				if last_ack == seq:
					valid_ack = True
				else:
					error_count += 1
		if not data:
			break
		seq = next_seq(seq)

newthread.join()              # Espera que el thread termine
s.close()

if valid:
	if total_sent_packages > 0:
		error_percentage = (error_count / total_sent_packages) * 100
		print(f"Sent {total_sent_packages} packages, lost {error_count}, {error_percentage:.2f}%")
	else:
		print("Error: No se enviaron paquetes.")
else:
	print("ERROR por TimeoutException")