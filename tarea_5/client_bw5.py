#!/usr/bin/python3
# client_bw5.py
# Echo client program UDP with Selective Repeat
# Version con dos threads: uno lee de <input_file> hacia el socket y el otro del socket a <output_file>
import jsockets
import socket
import sys, threading
import time
import os
import fcntl

MAX_SEQ = 1000
window = [None] * MAX_SEQ    # Cada indice contiene [data, fecha_envio, retransmitido]
acked = [False] * MAX_SEQ

sender_eof = False
receiver_eof = False
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
	if start <= end:
		return start <= seq and seq < end
	else:
		return start <= seq or seq < end

def get_timeout(start, end, timeout):
	min_tout = timeout
	seq = start
	while seq != end:
			if acked[seq]:  # no ha sido recibido
				tout = timeout - (time.time() - window[seq][1])

				if tout < min_tout:
					min_tout = tout
			seq = (seq + 1) % MAX_SEQ
	return min_tout

def print_window_state():
	print("\n--- Estado actual de la ventana ---")
	for i in range(MAX_SEQ):
		if window[i] is not None:
			status = []
			if window[i][2]:
				status.append("retransmitido")
			if acked[i]:
				status.append("recibido")
			else:
				status.append("pendiente")
			print(f"Seq {i:03d}: {' | '.join(status)}")
	print("-----------------------------------\n")

##########################
#    Thread Receptor     #
##########################

def Rdr(sock, output_file, size, max_window_size):
	global receiver_eof, rtt_est, valid

	recv_start = 0    # Inicio ventana de recepción
	recv_buffer = {}  # Buffer que guarda paquetes recibidos fuera de orden

	sock.settimeout(15)

	with open(output_file, "wb") as f:
		while not receiver_eof:
			try:
				print_window_state()
				data = sock.recv(size + 3)
			except socket.timeout:
				valid = 0
				break
			except Exception as e:
				print(f"Error: {e}")
				continue

			rcv_seq = from_seq(data[:3])
			payload = data[3:]

			with cond:
				# if seq dentro de la ventana de recepción
				if in_window(rcv_seq, recv_start, (recv_start + max_window_size) % MAX_SEQ):

					# Marcar como recibido
					acked[rcv_seq] = True

					# if seq == esperado:
					if rcv_seq == recv_start:
						if len(payload) == 0:
							receiver_eof = True
							break
						else:
							# escribir data a archivo
							f.write(payload)

							# calculo del rtt estimado (ignorar paquetes retransmitidos)
							if window[rcv_seq] is not None and not window[rcv_seq][2]:
								rtt = time.time() - window[rcv_seq][1]
								rtt_est = rtt if rtt_est is None else (0.5 * rtt + 0.5 * rtt_est)

						# correr ventana de recepción revisando todos los paquetes ya recibidos
						# escribiéndolos al archivo y revisando eof
						recv_start = next_seq(recv_start)
						while recv_start in recv_buffer:
							chunk = recv_buffer[recv_start]
							if len(chunk) == 0:
								receiver_eof = True
								break
							else: 
								chunk = recv_buffer.pop(recv_start)	
								f.write(chunk)

							# calculo del rtt estimado (ignorar paquetes retransmitidos)
							if window[recv_start] is not None and not window[recv_start][2]:
								rtt = time.time() - window[recv_start][1]
								rtt_est = rtt if rtt_est is None else (0.5 * rtt + 0.5 * rtt_est)
							
							recv_start = next_seq(recv_start)
						cond.notify()

					else: # dentro de la ventana pero fuera de orden
						# guardar en la ventana de recepción y anotarlo como "recibido" (para que no lo retransmita)
						recv_buffer[rcv_seq] = payload
						acked[rcv_seq] = True

				else: # Si no esta en la ventana de recepcion, lo ignoro
					continue
					

##########################
#          Main          #
##########################

if len(sys.argv) != 8:
	print('Use: '+sys.argv[0]+' <size> <timeout> <window_size> <input_file> <output_file> <host> <port>')
	
	

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
newthread = threading.Thread(target=Rdr, args=(s, output_file, size, max_window_size))
newthread.start()

##########################
#     Thread Emisor      #
##########################

start_window = 0  # Indice inicio ventana
end_window = 0    # Indice final ventana

# Estadísticas
retransmitted_packages = 0
sent_packages = 0   # paquetes enviados (sin contar retransmiciones)
max_win = 0		  # Registra el máximo tamaño alcanzado de la ventana

# En este otro thread leo desde <input_file> hacia socket:
with open(input_file, "rb") as f:
	while not (sender_eof and start_window == end_window):

		# correr la ventana del emisor hasta el último paquete secuencial recibido
		with cond:
			while start_window != end_window and acked[start_window]:
				window[start_window] = None
				start_window = next_seq(start_window)

			# while ventana llena
			while (end_window - start_window) % MAX_SEQ == max_window_size:
				tout = get_timeout(start_window, end_window, timeout)
				if tout <= 0: tout = 0
				if not cond.wait(tout):
					# retransmitir paquetes expirados que no hayan sido recibidos
					seq = start_window
					while seq != end_window:
						if window[seq] and (time.time() - window[seq][1]) >= timeout and not acked[seq]:
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
				# correr la ventana hasta el último paquete secuencial recibido
				while start_window != end_window and window[start_window] and acked[start_window]:
					window[start_window] = None
					start_window = next_seq(start_window)

		# Hay espacio en la ventana
		if not sender_eof:
			data = f.read(size)
			chunk = to_seq(end_window) + data
			print(f"{to_seq(end_window)} AAAAAAAAAA")
			if not data:
				sender_eof = True
			try:
				s.send(chunk)
				window[end_window] = [data, time.time(), False]
				sent_packages += 1
				end_window = next_seq(end_window)
				current_window_size = (end_window - start_window) % MAX_SEQ
				max_win = max(max_win, current_window_size)
			except Exception as e:
				print(f"Error: {e}")
				continue
		
		# Revisar si hay que retransmitir la ventana
		tout = get_timeout(start_window, end_window, timeout)
		if tout <= 0:
			# retransmitir paquetes expirados que no hayan sido recibidos
			seq = start_window
			while seq != end_window:
				if window[seq] and (time.time() - window[seq][1]) >= timeout and not acked[seq]:
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

##########################
#   Print Estadisticas   #
##########################

if valid:
	if sent_packages > 0:
		total = sent_packages + retransmitted_packages
		retrans_percentage = (100 * retransmitted_packages / total) if total > 0 else 0

		print(f"sent {sent_packages} packets, retrans {retransmitted_packages}, tot packs {total}, {retrans_percentage}%")
		print(f"Max_win: {max_win}")
		print(f"rtt est = {rtt_est}")
	else:
		print("Error: No se enviaron paquetes.")
else:
	print("Error: TimeoutException")