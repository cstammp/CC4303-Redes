import os

num_archivos = 1
tamano_archivo = 25 * 1024 * 1024  # 25 MB
contenido = b'1' * tamano_archivo  # escribe puros "1"s
dir_archivos = "archivos_txt"

# Crea la carpeta si no existe
os.makedirs(dir_archivos, exist_ok=True)

for i in range(num_archivos):
    nombre = f"{dir_archivos}/archivo_{i}.txt"
    with open(nombre, "wb") as f:
        f.write(contenido)