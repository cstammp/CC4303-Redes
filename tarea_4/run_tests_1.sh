if [ $# -ne 2 ]; then
	echo "Uso: $0 <host> <input_file>"
	exit 1
fi

HOST=$1
PORT="1818"
SIZES=(4096 4500 5000)
TIMEOUTS=(0.07 0.1)
WINDOW_SIZES=(10 20 30 40 50 60 70 80 90 100 200 300 400 500)
INPUT_FILE=$2
DIR_OUT="out"
LOG_FILE="log.txt"

mkdir -p "$DIR_OUT"

for SIZE in "${SIZES[@]}"; do
	echo "size=$SIZE..."
	for TIMEOUT in "${TIMEOUTS[@]}"; do
		echo "timeout=$TIMEOUT..."
		for WINDOW_SIZE in "${WINDOW_SIZES[@]}"; do
			echo "window_size=$WINDOW_SIZE..."
			start=$(date +%s.%N)

			OUTPUT_FILE="${DIR_OUT}/${SIZE}_${TIMEOUT}_${WINDOW_SIZE}_out.jpg"
			OUTPUT=$(python3 client_bw4.py "$SIZE" "$TIMEOUT" "$WINDOW_SIZE" "$INPUT_FILE" "$OUTPUT_FILE" "$HOST" "$PORT")

			if echo "$OUTPUT" | grep -q "Error: TimeoutException"; then
                echo "Error: TimeoutException con SIZE=$SIZE, TIMEOUT=$TIMEOUT, WINDOW_SIZE=$WINDOW_SIZE"
				exit 1
            fi

			end=$(date +%s.%N)
			duration=$(echo "$end - $start" | bc)   # requiere instalar bc (bash calculator)

			bytes_received=$(stat -c %s "$OUTPUT_FILE" || echo 0)

			# Calcula bandwidth
			bandwidth=$(echo "scale=2; $bytes_received / 1024 / $duration" | bc)

			# Guardar en log
			{
				echo "<size>$SIZE"
				echo "<timeout>$TIMEOUT"
				echo "<window_size>$WINDOW_SIZE"
				echo "Bytes recibidos: $bytes_received"
				echo "Tiempo: $duration segundos"
				echo "Bandwidth: $bandwidth KB/s"
				echo "$OUTPUT"
				echo
			} >> "$LOG_FILE"
		done
	done
done