import requests
import csv
import os
from datetime import datetime

ott_url = "https://ottcache.dof6.com/movistarplus/webplayer/OTT/contents/epg"
ott_csv_filepath = "ott.csv"
difusion_url = "https://ottcache.dof6.com/movistarplus/webplayer/DIFUSION/contents/epg"
difusion_csv_filepath = "difusion.csv"
cambios_filepath = "cambios.csv"

# Define los campos que se extraerán y usarán como encabezados en los CSV de datos
data_fields = ["CasId", "CodCadenaTv", "Nombre", "Logo", "PuntoReproduccion", "FormatoVideo"]

def load_existing_data(filepath):
    """Carga los datos de un archivo CSV existente en una lista de diccionarios."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Asegurarse de que todas las claves esperadas existan
            data = []
            # Determinar las claves esperadas del archivo si existe, o usar data_fields si no
            # Esto es importante si las columnas del archivo existente difieren
            fieldnames_from_file = reader.fieldnames if reader.fieldnames else data_fields
            expected_keys = set(fieldnames_from_file)

            for row in reader:
                # Añadir claves faltantes con valor vacío si es necesario
                for key in expected_keys:
                    row.setdefault(key, "")
                # Solo incluir las claves definidas en data_fields para consistencia interna
                filtered_row = {key: row.get(key, "") for key in data_fields}
                data.append(filtered_row)
            return data
    except Exception as e:
        print(f"Error al leer {filepath}: {e}")
        return []


def detect_changes(old_data, new_data, origen):
    """Detecta cambios entre dos conjuntos de datos y formatea los cambios para el log."""
    changes = []
    # CAMBIO: Formato de fecha DD/MM/YYYY
    date_now = datetime.now().strftime('%d/%m/%Y')
    old_data_dict = {row['CasId']: row for row in old_data}
    new_data_dict = {row['CasId']: row for row in new_data}

    all_keys = set(old_data_dict.keys()) | set(new_data_dict.keys())

    for casid in sorted(list(all_keys)): # Ordenar por CasId
        old_row = old_data_dict.get(casid)
        new_row = new_data_dict.get(casid)

        # Determinar el tipo de cambio
        if not old_row and new_row:
            cambio = "Añadido"
        elif old_row and not new_row:
            cambio = "Eliminado"
        elif old_row != new_row:
            cambio = "Modificado"
        else:
            continue # Sin cambios

        change_record = {
            "Fecha": date_now,
            "Origen": origen,
            "Cambio": cambio,
            "CasId": casid,
        }

        # Llenar los campos Antes_* y Despues_*
        for field in data_fields:
            old_val = old_row.get(field, "") if old_row else ""
            new_val = new_row.get(field, "") if new_row else ""

            antes_key = f"Antes_{field}"
            despues_key = f"Despues_{field}"

            if cambio == "Modificado":
                if old_val != new_val:
                    # CAMBIO: Campo modificado - registrar valor antiguo y nuevo (sin negrita)
                    change_record[antes_key] = old_val
                    change_record[despues_key] = new_val
                else:
                    # CAMBIO: Campo NO modificado dentro de una fila modificada - dejar en blanco
                    change_record[antes_key] = ""
                    change_record[despues_key] = ""
            elif cambio == "Añadido":
                change_record[antes_key] = ""
                change_record[despues_key] = new_val # Sin negrita
            elif cambio == "Eliminado":
                change_record[antes_key] = old_val # Sin negrita
                change_record[despues_key] = ""

        changes.append(change_record)

    return changes

def write_changes(changes):
    """Escribe los cambios detectados en el archivo de log CSV."""
    if not changes:
      return

    file_exists = os.path.exists(cambios_filepath)

    # CAMBIO: Definir encabezados con Antes y Después intercalados
    interleaved_fields = []
    for f in data_fields:
        interleaved_fields.append(f"Antes_{f}")
        interleaved_fields.append(f"Despues_{f}")
    fieldnames = ["Fecha", "Origen", "Cambio", "CasId"] + interleaved_fields

    with open(cambios_filepath, mode='a', newline='', encoding='utf-8') as f:
        # Usar QUOTE_ALL para manejar mejor comas o saltos de línea en los datos, si los hubiera
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        if not file_exists or os.path.getsize(cambios_filepath) == 0:
            writer.writeheader()
        writer.writerows(changes)

def export_movistarEPG_to_csv(epg_url, filepath, origen):
    """Descarga datos EPG, los guarda en CSV, detecta y registra cambios."""
    try:
        response = requests.get(epg_url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"ERROR al descargar {origen} desde {epg_url}: {e}")
        return

    try:
        movistarEPG = response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"ERROR al decodificar JSON de {origen}: {e}")
        print(f"Contenido recibido: {response.text[:500]}...")
        return

    csv_data = []

    if not isinstance(movistarEPG, list):
         print(f"ERROR: La estructura del JSON de {origen} no es una lista como se esperaba.")
         return

    # Procesar los datos JSON
    for grupo in movistarEPG:
         if not isinstance(grupo, dict):
             print(f"Advertencia: Elemento no es un diccionario en {origen}, saltando: {grupo}")
             continue

         logo_url = ""
         for logo_info in grupo.get("Logos", []):
             if isinstance(logo_info, dict) and logo_info.get("id") == "nobox_dark":
                 logo_url = logo_info.get("uri", "")
                 break

         row_data = {field: grupo.get(field, "") for field in data_fields}
         row_data["Logo"] = logo_url
         row_data["Nombre"] = str(row_data["Nombre"]).replace("\t", " ").replace("\n", " ").strip()
         if not row_data.get("CasId"):
             print(f"Advertencia: Registro sin CasId encontrado en {origen}, saltando: {row_data}")
             continue
         csv_data.append(row_data)

    # Cargar datos existentes y detectar cambios
    existing_data = load_existing_data(filepath)
    changes = detect_changes(existing_data, csv_data, origen)
    if changes:
        write_changes(changes)

    # Escribir los nuevos datos al archivo CSV (ott.csv o difusion.csv)
    try:
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data_fields, quoting=csv.QUOTE_ALL) # Usar QUOTE_ALL
            writer.writeheader()
            writer.writerows(csv_data)
        print(f"{origen} exportado a {filepath}. Cambios detectados: {len(changes)}")
    except IOError as e:
        print(f"Error al escribir en {filepath}: {e}")


# --- Ejecución Principal ---
def ejecutar_proceso():
    print(f"--- Inicio del proceso: {datetime.now().isoformat(timespec='seconds')} ---")
    export_movistarEPG_to_csv(ott_url, ott_csv_filepath, "OTT")
    export_movistarEPG_to_csv(difusion_url, difusion_csv_filepath, "DIFUSION")
    print(f"--- Fin del proceso: {datetime.now().isoformat(timespec='seconds')} ---")

# Ejecutar la función principal
ejecutar_proceso()
