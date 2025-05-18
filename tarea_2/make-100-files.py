import os

# Configuración
num_archivos = 100
tamano_archivo = 5000  # bytes
contenido = b'1' * tamano_archivo  # escribe puros "1"s
dir_archivos = "archivos_txt"

# Crear la carpeta si no existe
os.makedirs(dir_archivos, exist_ok=True)

# Crear los archivos
for i in range(num_archivos):
    nombre = f"{dir_archivos}/archivo_{i}.txt"
    with open(nombre, "wb") as f:
        f.write(contenido)