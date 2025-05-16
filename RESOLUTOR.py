import itertools as it
import os # Importado para la creación de archivo de ejemplo

# --- Definiciones Principales del Sudoku ---
DOMINIO = set(range(1, 10))
ID_COLUMNAS = "ABCDEFGHI"
# Genera las claves de las celdas como A1, B1, ..., I1, A2, B2, ..., I9
# Este orden debe coincidir con el formato del archivo de entrada si es un valor por línea.
# Generación original de strKeys:
# _claves_originales = list(it.product(range(1,10),ID_COLUMNAS)) # (1,'A'), (1,'B')...
# CLAVES_CELDA = [f"{clave[1]}{clave[0]}" for clave in _claves_originales] # A1, B1...I1, A2, B2...I2 etc.

# Generación estándar de claves de celda (A1, A2, ... A9, B1, ... B9)
# Esto es a menudo más común para cadenas de 81 caracteres o entradas línea por línea
# donde el archivo es valor A1, valor A2, ... valor A9, valor B1 ...
# Para consistencia con el fragmento de código original del usuario y su probable bucle de lectura de archivos,
# mantendremos su generación de strKeys. Si tu archivo es A1..A9, B1..B9, etc.,
# entonces CLAVES_CELDA debería ser: [f"{col}{fila}" for col in ID_COLUMNAS for fila in range(1, 10)]
# Asumiremos que el formato del archivo coincide con el orden implícito en strKeys del código original del usuario:
# Línea 1: A1, Línea 2: B1, ..., Línea 9: I1, Línea 10: A2, etc.
_claves_para_strKeys = list(it.product(range(1,10), ID_COLUMNAS)) # (1,'A'), (1,'B'),...,(1,'I'),(2,'A')...
CLAVES_CELDA = [f"{col_char}{num_fila}" for num_fila, col_char in _claves_para_strKeys] # A1,B1,...,I1,A2,B2,...,I2...


# --- Definiciones de Restricciones (del código del usuario, con ajustes menores) ---
def definir_restricciones_columnas(id_cols, valores_dominio):
    restricciones_columnas = []
    for id_col in id_cols:
        variables_restriccion = [f"{id_col}{i}" for i in valores_dominio]
        restricciones_columnas.append(variables_restriccion)
    return restricciones_columnas

def definir_restricciones_filas(id_cols, valores_dominio):
    restricciones_filas = []
    for i in valores_dominio: # Para cada número de fila
        # Corregido para formar claves como A1, B1, C1 para la fila 1
        variables_restriccion = [f"{id_col}{i}" for id_col in id_cols]
        restricciones_filas.append(variables_restriccion)
    return restricciones_filas

def definir_restricciones_cajas(id_cols_str, valores_dominio):
    todas_las_cajas = []
    lista_id_cols = list(id_cols_str)
    for inicio_fila in range(1, 10, 3): # 1, 4, 7
        for inicio_idx_col in range(0, 9, 3): # 0, 3, 6 (índices para lista_id_cols)
            variables_caja = []
            for i in range(3): # Desplazamiento en fila para la caja
                for j in range(3): # Desplazamiento en columna para la caja
                    fila = inicio_fila + i
                    col_char = lista_id_cols[inicio_idx_col + j]
                    variables_caja.append(f"{col_char}{fila}")
            todas_las_cajas.append(variables_caja)
    return todas_las_cajas

TODAS_LAS_RESTRICCIONES = (definir_restricciones_columnas(ID_COLUMNAS, DOMINIO) +
                           definir_restricciones_filas(ID_COLUMNAS, DOMINIO) +
                           definir_restricciones_cajas(ID_COLUMNAS, DOMINIO))

# --- Funciones del Solucionador CSP ---

def asignacion_esta_completa(asignacion, todas_las_variables):
    """Verifica si todas las variables han sido asignadas."""
    return len(asignacion) == len(todas_las_variables)

def seleccionar_variable_no_asignada_mrv(asignacion, dominios, todas_las_variables):
    """Selecciona la variable no asignada con el Mínimo de Valores Restantes (MRV)."""
    variables_no_asignadas = [v for v in todas_las_variables if v not in asignacion]
    if not variables_no_asignadas:
        return None

    variable_mrv = None
    tamano_minimo_dominio = float('inf')

    for var in variables_no_asignadas:
        if var not in dominios: # No debería ocurrir con una inicialización adecuada
            print(f"Advertencia: Variable {var} no encontrada en dominios durante la selección MRV.")
            continue
        tamano_actual_dominio = len(dominios[var])
        if tamano_actual_dominio < tamano_minimo_dominio:
            tamano_minimo_dominio = tamano_actual_dominio
            variable_mrv = var
        # Aquí se podría agregar un desempate (ej. heurística de grado) para optimización adicional.
    return variable_mrv

def ordenar_valores_del_dominio(variable, dominios):
    """Ordena los valores en el dominio de la variable. Orden numérico simple por ahora."""
    if variable not in dominios:
        print(f"Advertencia: Variable {variable} no encontrada en dominios para ordenar valores.")
        return []
    return sorted(list(dominios[variable]))

def es_consistente_con_asignacion(variable, valor, asignacion, restricciones):
    """
    Verifica si asignar 'valor' a 'variable' es consistente con la 'asignacion' actual
    basado en las reglas del Sudoku (restricciones).
    """
    for grupo_restriccion in restricciones:
        if variable in grupo_restriccion:
            for variable_par in grupo_restriccion:
                if variable_par != variable and variable_par in asignacion:
                    if asignacion[variable_par] == valor:
                        return False
    return True

def forward_checking(variable_asignada, valor_asignado, asignacion, dominios_actuales, registro_cambios_dominio, restricciones):
    """
    Realiza forward checking después de asignar 'valor_asignado' a 'variable_asignada'.
    Actualiza 'dominios_actuales' y registra los cambios en 'registro_cambios_dominio'.
    Retorna True si es exitoso, False si se encuentra una inconsistencia (dominio vacío).
    'asignacion' aquí ya DEBERÍA contener la nueva asignación de variable_asignada.
    """
    for grupo_restriccion in restricciones:
        if variable_asignada in grupo_restriccion:
            for vecino in grupo_restriccion:
                # Considerar solo vecinos no asignados
                if vecino != variable_asignada and vecino not in asignacion: # vecino aún no está asignado
                    if valor_asignado in dominios_actuales[vecino]:
                        dominios_actuales[vecino].discard(valor_asignado)
                        registro_cambios_dominio.append((vecino, valor_asignado)) # Registrar para posible deshacer
                        if not dominios_actuales[vecino]: # El dominio se vuelve vacío
                            return False # Inconsistencia encontrada
    return True

def backtrack_resolver(asignacion, dominios_actuales):
    """
    Función recursiva de backtracking para resolver el Sudoku.
    'dominios_actuales' es modificado por esta función y sus llamadas hijas;
    los cambios se revierten al hacer backtracking.
    """
    if asignacion_esta_completa(asignacion, CLAVES_CELDA):
        return asignacion # Solución encontrada

    variable_a_asignar = seleccionar_variable_no_asignada_mrv(asignacion, dominios_actuales, CLAVES_CELDA)
    if variable_a_asignar is None: # Solo debería ocurrir si MRV tiene un problema o error lógico
        print("Error: MRV no seleccionó ninguna variable, pero la asignación no está completa.")
        return None

    for valor in ordenar_valores_del_dominio(variable_a_asignar, dominios_actuales):
        if es_consistente_con_asignacion(variable_a_asignar, valor, asignacion, TODAS_LAS_RESTRICCIONES):
            asignacion[variable_a_asignar] = valor
            cambios_dominio_fc = [] # Registro para valores eliminados por forward checking

            # Realizar Forward Checking
            if forward_checking(variable_a_asignar, valor, asignacion, dominios_actuales, cambios_dominio_fc, TODAS_LAS_RESTRICCIONES):
                resultado = backtrack_resolver(asignacion, dominios_actuales)
                if resultado:
                    return resultado # Solución encontrada y propagada

            # Backtrack: Deshacer asignación y cambios de Forward Checking
            # Deshacer cambios de FC primero
            for var_cambiada, val_eliminado in cambios_dominio_fc:
                dominios_actuales[var_cambiada].add(val_eliminado)
            # Deshacer asignación
            del asignacion[variable_a_asignar]

    return None # No se encontró solución desde esta rama

def aplicar_consistencia_inicial(dominios, restricciones):
    """
    Aplica una verificación de consistencia básica (consistencia de arco para restricciones unarias).
    Elimina repetidamente valores de los dominios si una variable en una restricción está asignada de forma única.
    Modifica 'dominios' en el lugar. Retorna True si es consistente, False si algún dominio se vacía.
    """
    cambio_en_iteracion = True
    while cambio_en_iteracion:
        cambio_en_iteracion = False
        for grupo_restriccion in restricciones:
            for var1 in grupo_restriccion:
                if len(dominios[var1]) == 1: # var1 está asignada
                    valor_a_eliminar = list(dominios[var1])[0]
                    for var2 in grupo_restriccion:
                        if var1 != var2 and valor_a_eliminar in dominios[var2]:
                            dominios[var2].discard(valor_a_eliminar)
                            cambio_en_iteracion = True
                            if not dominios[var2]: # Dominio vaciado
                                print(f"Inconsistencia encontrada durante la propagación inicial: dominio de {var2} vacío.")
                                return False
    return True

def resolver_sudoku_desde_archivo(ruta_archivo_tablero):
    """
    Función principal para cargar un Sudoku desde un archivo y resolverlo.
    """
    dominios_iniciales = {clave: DOMINIO.copy() for clave in CLAVES_CELDA}

    try:
        with open(ruta_archivo_tablero, 'r') as f:
            # Asume que el archivo tiene 81 líneas, una para cada celda.
            # El orden de las líneas debe coincidir con CLAVES_CELDA: A1, B1, C1...I1, A2, B2...I2 etc.
            # '0' o cualquier carácter no numérico (1-9) representa una celda vacía.
            for clave in CLAVES_CELDA:
                valor_linea = f.readline().strip()
                if valor_linea and valor_linea.isdigit() and valor_linea != '0':
                    num_val = int(valor_linea)
                    if 1 <= num_val <= 9:
                        dominios_iniciales[clave] = {num_val}
                    else:
                        print(f"Advertencia: Número inválido '{valor_linea}' para {clave} en entrada. Tratando como vacía.")
                # Si valor_linea es '0', no numérico o vacío, es una celda vacía; el dominio permanece completo.
            # Verificar si se leyeron suficientes líneas
            if f.readline(): # Si todavía hay datos, el archivo podría ser demasiado largo
                print("Advertencia: El archivo puede contener más de 81 líneas de datos relevantes.")

    except FileNotFoundError:
        print(f"Error: Archivo '{ruta_archivo_tablero}' no encontrado.")
        return None
    except Exception as e:
        print(f"Error leyendo o procesando el archivo '{ruta_archivo_tablero}': {e}")
        return None

    # Aplicar propagación de consistencia inicial
    if not aplicar_consistencia_inicial(dominios_iniciales, TODAS_LAS_RESTRICCIONES):
        print("El Sudoku es inconsistente después de la propagación inicial basada en los valores de entrada.")
        return None

    # Iniciar la búsqueda con backtracking
    print(f"\nIntentando resolver Sudoku desde: {ruta_archivo_tablero}")
    asignacion_solucion = backtrack_resolver({}, dominios_iniciales) # Empezar con asignación vacía

    if asignacion_solucion:
        print("\n¡Solución encontrada!")
        return asignacion_solucion
    else:
        print("\nNo se encontró solución para el Sudoku.")
        return None

def imprimir_solucion_sudoku(asignacion_solucion):
    """Imprime la cuadrícula del Sudoku a partir de una asignación de solución."""
    if not asignacion_solucion:
        print("No hay solución para imprimir.")
        return

    print("\nCuadrícula del Sudoku Resuelto:")
    # Visualización estándar del Sudoku: Filas 1-9, Columnas A-I
    for num_f in range(1, 10): # Para cada número de fila 1..9
        if num_f > 1 and (num_f - 1) % 3 == 0:
            print("------+-------+------") # Separador horizontal para cajas 3x3
        
        valores_fila = []
        for idx_c, char_col in enumerate(ID_COLUMNAS): # Para cada caracter de columna A..I
            clave = f"{char_col}{num_f}" # Nombre de celda ej., A1, B1 para num_f=1
            valor = asignacion_solucion.get(clave, ".") # Obtener valor, por defecto .
            valores_fila.append(str(valor))
            if (idx_c + 1) % 3 == 0 and idx_c < len(ID_COLUMNAS) - 1:
                valores_fila.append("|") # Separador vertical para cajas 3x3
        print(" ".join(valores_fila))

# --- Ejecución Principal ---
if __name__ == "__main__":
    # IMPORTANTE: Crea un archivo llamado "sudoku_a_resolver.txt" en el mismo directorio,
    # o cambia la ruta abajo.
    # El archivo debe tener 81 líneas. Cada línea es un dígito para una celda.
    # '0' significa vacío. El orden de las celdas en el archivo debe ser:
    # Valor para A1
    # Valor para B1
    # ...
    # Valor para I1 (9na línea)
    # Valor para A2 (10ma línea)
    # Valor para B2
    # ...
    # Valor para I9 (81va línea)
    
    # Ejemplo: para crear un archivo Sudoku muy simple para pruebas "sudoku_a_resolver.txt":
    # A1=1, todos los demás 0.
    # El contenido del archivo sería:
    # 1
    # 0
    # ... (79 líneas más de '0')
    
    # Para un nivel "imposible" de Sudokumania, copia su representación a este formato.
    # Si Sudokumania da una cadena de 81 caracteres (ej. 0030206009003050010018064...),
    # necesitarás un pequeño script para convertir esa cadena a un archivo de 81 líneas donde
    # el carácter para A1 está en la línea 1, B1 en la línea 2, ..., I1 en la línea 9, A2 en la línea 10, etc.
    # O, ajusta la lógica de lectura de archivos en `resolver_sudoku_desde_archivo` si tu formato
    # de entrada es diferente (ej., una cadena de 81 caracteres directamente).

    ruta_del_archivo = "sudoku_a_resolver.txt" 
    print(f"Intentando usar el orden de CLAVES_CELDA: {CLAVES_CELDA[:12]}...") # Imprime las primeras claves para confirmar el orden
    
    # Crear un "sudoku_a_resolver.txt" de ejemplo si no existe para pruebas rápidas
    if not os.path.exists(ruta_del_archivo):
        print(f"'{ruta_del_archivo}' no encontrado. Creando un archivo de Sudoku de ejemplo vacío.")
        with open(ruta_del_archivo, 'w') as f:
            for _ in range(81):
                f.write("0\n")
        print(f"Archivo de ejemplo '{ruta_del_archivo}' creado con un Sudoku vacío. Por favor, reemplázalo con tu Sudoku objetivo.")


    sudoku_resuelto = resolver_sudoku_desde_archivo(ruta_del_archivo)

    if sudoku_resuelto:
        imprimir_solucion_sudoku(sudoku_resuelto)