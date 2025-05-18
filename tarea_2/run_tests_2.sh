if [ $# -ne 1 ]; then
    echo "Uso: $0 <host>"
    exit 1
fi

HOST=$1
PORT="1818"
SIZES=(1024 1500 2048 2500 3072 3500 4096 4500 5000)
DIR_IN="archivos_txt"
DIR_OUT="out_txt"
LOG_FILE="log.txt"

mkdir -p "$DIR_OUT"

run_udp_test() {
    local i=$1
    local SIZE=$2
    local INPUT_FILE="${DIR_IN}/archivo_${i}.txt"
    local OUTPUT_FILE="${DIR_OUT}/archivo_${i}_out_${SIZE}.txt"

    while true; do
        OUTPUT=$(python3 client_bw2.py "$SIZE" "$INPUT_FILE" "$OUTPUT_FILE" "$HOST" "$PORT")
        echo "[archivo_${i}] size=$SIZE :: $OUTPUT"

        if echo "$OUTPUT" | grep -q "Medición inválida por timeout"; then
            echo "[archivo_${i}] Reintentando size=$SIZE..."
        else
            break
        fi
    done
}

# Ejecuta las pruebas para cada SIZE
for SIZE in "${SIZES[@]}"; do
    echo "size=$SIZE..."

	# Borra los archivos generados (para no terminar con 500 archivos)
    rm -f "${DIR_OUT}/archivo_"*_out_*.txt
    start=$(date +%s.%N)

    # Lanza 100 pruebas en paralelo
    for i in $(seq 0 99); do
        run_udp_test "$i" "$SIZE" &
    done

    # Espera a que terminen
    wait
    end=$(date +%s.%N)
    duration=$(echo "$end - $start" | bc)   # requiere instalar bc (bash calculator)

    # Suma bytes recibidos
    total_received=0
    for i in $(seq 0 99); do
        file="${DIR_OUT}/archivo_${i}_out_${SIZE}.txt"
        bytes=$(stat -c %s "$file" || echo 0)
        total_received=$((total_received + bytes))
    done

    # Calcula bandwidth
    bandwidth=$(echo "scale=2; $total_received / 1000 / $duration" | bc)

    # Guardar en log
    {
        echo "<size>$SIZE"
        echo "Bytes totales recibidos: $total_received"
        echo "Tiempo total: $duration segundos"
        echo "Bandwidth: $bandwidth KB/s"
        echo
    } >> "$LOG_FILE"
done