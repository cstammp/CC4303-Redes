#!/usr/bin/python3
# client_bw4.py
# Echo client program UDP with Go-Back-N
# Version con dos threads: uno lee de <input_file> hacia el socket y el otro del socket a <output_file>
import jsockets
import socket
import sys, threading
import time
import os
import fcntl

MAX_SEQ = 1000
window = [None] * MAX_SEQ    # Cada indice contiene [data, fecha_envio, retransmitido]

last_ack = None
error_count = 0
retransmitted_packages = 0
total_sent_packages = 0
eof = False
valid = 1
rtt_est = None

# Lock y condición para sincronización entre threads
lock = threading.Lock()
cond = threading.Condition(lock)

def to_seq(n):
	if n < 0 or n > 999:
		print("invalid seq", file=sys.stderr)
		sys.exit(1)
	return format(n,'03d').encode()

def from_seq(s):
	return int(s.decode())

def next_seq(seq):
	return (seq + 1) % MAX_SEQ

def in_window(seq, start, end):
	return (start <= end and start <= seq < end) or (start > end and (seq >= start or seq < end))

def Rdr(s, output_file, size):
	global last_ack, valid, rtt_est
	expected_seq = 0
	s.settimeout(15)
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

			recv_seq = from_seq(data[:3])
			payload = data[3:]
			if in_window(recv_seq, start_window, end_window):
				with cond:
					if recv_seq == expected_seq:
						last_ack = recv_seq
						f.write(payload)
						if not window[recv_seq][2]:  # No fue retransmitido
							rtt = time.time() - window[recv_seq][1]
							rtt_est = (0.5 * rtt) + (0.5 * rtt_est) if rtt_est is not None else rtt  # Promedio ponderado
						expected_seq = next_seq(expected_seq)
						if not payload:    # EOF
							break
					cond.notify()

if len(sys.argv) != 8:
	print('Use: '+sys.argv[0]+' <size> <timeout> <window_size> <input_file> <output_file> <host> <port>')
	sys.exit(1)

size = int(sys.argv[1])
timeout = float(sys.argv[2])
max_window_size = int(sys.argv[3])
input_file = sys.argv[4]
output_file = sys.argv[5]
host = sys.argv[6]
port = sys.argv[7]

s = jsockets.socket_udp_connect(host, port)
if s is None:
	print('Error: could not open socket')
	sys.exit(1)

# Creo thread que lee desde el socket hacia <output_file>:
newthread = threading.Thread(target=Rdr, args=(s, output_file, size))
newthread.start()

start_window = 0  # Indice inicio ventana
end_window = 0    # Indice final ventana (No inclusivo)
max_win = 0		  # Registra el máximo tamaño alcanzado de la ventana (Para estadísticas)

# En este otro thread leo desde <input_file> hacia socket:
with open(input_file, "rb") as f:
	while not (eof and last_ack == (end_window - 1) % MAX_SEQ):
		# correr la ventana hasta el último ack recibido
		with cond:
			if last_ack is not None and in_window(last_ack, start_window, end_window):
					start_window = next_seq(last_ack)

		# while ventana llena
		while (end_window - start_window) % MAX_SEQ == max_window_size:
			with cond:
				tout = timeout - (time.time() - window[start_window][1])
				if tout < 0: tout = 0
				if not cond.wait(tout):
					# retransmitir ventana
					error_count += 1
					seq = start_window
					while seq != end_window:
						data = window[seq][0]
						chunk = to_seq(seq) + data
						try:
							s.send(chunk)
							window[seq][1] = time.time()
							window[seq][2] = True
							retransmitted_packages += 1
						except Exception as e:
							print(f"Error: {e}")
							pass
						seq = next_seq(seq)
				# correr la ventana hasta el último ack recibido recibido
				if last_ack is not None and in_window(last_ack, start_window, end_window):
						start_window = next_seq(last_ack)

		# Hay espacio en la ventana
		if not eof:
			data = f.read(size)
			chunk = to_seq(end_window) + data
			if not data:
				eof = True
			try:
				s.send(chunk)
				window[end_window] = [data, time.time(), False]
				total_sent_packages += 1
				end_window = next_seq(end_window)
				current_window_size = (end_window - start_window) % MAX_SEQ
				max_win = max(max_win, current_window_size)
			except Exception as e:
				print(f"Error: {e}")
				continue

		# Revisar si hay que retransmitir la ventana
		with cond:
			if window[start_window] and (time.time() - window[start_window][1]) >= timeout:
				error_count += 1
				seq = start_window
				while seq != end_window:
					data = window[seq][0]
					chunk = to_seq(seq) + data
					try:
						s.send(chunk)
						window[seq][1] = time.time()
						window[seq][2] = True
						retransmitted_packages += 1
					except Exception as e:
						print(f"Error: {e}")
						pass
					seq = next_seq(seq)

newthread.join()              # Espera que el thread termine
s.close()

if valid:
	if total_sent_packages > 0:
		error_percentage = (error_count / total_sent_packages) * 100
		extra_packages_sent_percentage = ((total_sent_packages + retransmitted_packages) / total_sent_packages) * 100
		print(f"Sent {total_sent_packages} packages, retrans {error_count}, {error_percentage:.2f}%, tot packs {total_sent_packages + retransmitted_packages}, {extra_packages_sent_percentage:.2f}%")
		print(f"Max_win: {max_win}")
		print(f"rtt est = {rtt_est}")
	else:
		print("Error: No se enviaron paquetes.")
else:
	print("Error: TimeoutException")