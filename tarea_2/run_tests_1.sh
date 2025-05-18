if [ $# -ne 1 ]; then
    echo "Uso: $0 <host>"
    exit 1
fi

SIZES=(1024 1500 2048 2500 3072 3500 4096 4500 5000)
INPUT_FILE="mona_lisa.jpg"
DIR_OUT="out"
HOST=$1
PORT="1818"
LOG_FILE="log.txt"

mkdir -p "$DIR_OUT"

for SIZE in "${SIZES[@]}"; do
    echo "size=$SIZE..."
    start=$(date +%s.%N)

    while true; do
        OUTPUT_FILE="${DIR_OUT}/${SIZE}_out.jpg"
        OUTPUT=$(python3 client_bw2.py "$SIZE" "$INPUT_FILE" "$OUTPUT_FILE" "$HOST" "$PORT")
        echo "$OUTPUT"
        # Verifica si fue exitosa
        if echo "$OUTPUT" | grep -q "Medición inválida por timeout"; then
            echo "reintentando size=$SIZE..."
        else
            break
        fi
    done

	end=$(date +%s.%N)
    duration=$(echo "$end - $start" | bc)   # requiere instalar bc (bash calculator)

	file="${DIR_OUT}/${SIZE}_out.jpg"
    bytes_received=$(stat -c %s "$file" || echo 0)

	# Calcula bandwidth
    bandwidth=$(echo "scale=2; $bytes_received / 1000 / $duration" | bc)

    # Guardar en log
    {
        echo "<size>$SIZE"
        echo "Bytes recibidos: $bytes_received"
        echo "Tiempo: $duration segundos"
        echo "Bandwidth: $bandwidth KB/s"
        echo
    } >> "$LOG_FILE"
done