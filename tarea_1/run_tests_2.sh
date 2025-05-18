
if [ $# -ne 1 ]; then
    echo "Uso: $0 <size>"
    exit 1
fi

SIZE=$1
DIR_IN="./archivos_txt"
DIR_OUT="./out_txt"

mkdir -p "$DIR_OUT"

# Correr 100 procesos en paralelo para cada archivo
for i in $(seq 0 99); do
    INPUT_FILE="${DIR_IN}/archivo_${i}.txt"
    OUTPUT_FILE="${DIR_OUT}/archivo_${i}_out.txt"
    ./client_bw.py "$SIZE" "$INPUT_FILE" "$OUTPUT_FILE" "anakena.dcc.uchile.cl" "1818" &
done

# Espera que todos los procesos terminen
for i in $(seq 0 99); do
    wait
done

echo "done."
