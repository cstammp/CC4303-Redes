if [ $# -ne 2 ]; then
	echo "Uso: $0 <host> <timeout>"
	exit 1
fi

SIZES=(1024 1500 2048 2500 3072 3500 4096 4500 5000)
INPUT_FILE="mona_lisa.jpg"
TIMEOUT=$2
DIR_OUT="out"
HOST=$1
PORT="1818"
LOG_FILE="log.txt"

mkdir -p "$DIR_OUT"

for SIZE in "${SIZES[@]}"; do
	echo "size=$SIZE..."
	start=$(date +%s.%N)

	OUTPUT_FILE="${DIR_OUT}/${SIZE}_out.jpg"
	OUTPUT=$(python3 client_bw3.py "$SIZE" "$TIMEOUT" "$INPUT_FILE" "$OUTPUT_FILE" "$HOST" "$PORT")

	end=$(date +%s.%N)
	duration=$(echo "$end - $start" | bc)   # requiere instalar bc (bash calculator)

	file="${DIR_OUT}/${SIZE}_out.jpg"
	bytes_received=$(stat -c %s "$file" || echo 0)

	# Calcula bandwidth
	bandwidth=$(echo "scale=2; $bytes_received / 1024 / $duration" | bc)

	# Guardar en log
	{
		echo "<timeout>$TIMEOUT"
		echo "<size>$SIZE"
		echo "Bytes recibidos: $bytes_received"
		echo "Tiempo: $duration segundos"
		echo "Bandwidth: $bandwidth KB/s"
		echo "Efficiency: $OUTPUT"
		echo
	} >> "$LOG_FILE"
done