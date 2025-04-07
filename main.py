import requests
import csv
import os
from datetime import datetime

ott_url = "https://ottcache.dof6.com/movistarplus/webplayer/OTT/contents/epg"
ott_csv_filepath = "ott.csv"
difusion_url = "https://ottcache.dof6.com/movistarplus/webplayer/DIFUSION/contents/epg"
difusion_csv_filepath = "difusion.csv"
cambios_filepath = "cambios.csv"

def load_existing_data(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def detect_changes(old_data, new_data, origen):
    changes = []
    date_now = datetime.now().isoformat(timespec='seconds')
    old_data_dict = {row['CasId']: row for row in old_data}
    new_data_dict = {row['CasId']: row for row in new_data}

    # Detect added or modified
    for casid, new_row in new_data_dict.items():
        if casid not in old_data_dict:
            changes.append({"Fecha": date_now, "Origen": origen, "Cambio": "Añadido", "CasId": casid, "Detalles": str(new_row)})
        elif old_data_dict[casid] != new_row:
            changes.append({"Fecha": date_now, "Origen": origen, "Cambio": "Modificado", "CasId": casid, "Detalles": str(new_row)})

    # Detect removed
    for casid in old_data_dict:
        if casid not in new_data_dict:
            changes.append({"Fecha": date_now, "Origen": origen, "Cambio": "Eliminado", "CasId": casid, "Detalles": str(old_data_dict[casid])})

    return changes

def write_changes(changes):
    file_exists = os.path.exists(cambios_filepath)
    with open(cambios_filepath, mode='a', newline='', encoding='utf-8') as f:
        fieldnames = ["Fecha", "Origen", "Cambio", "CasId", "Detalles"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(changes)

def export_movistarEPG_to_csv(epg_url, filepath, origen):
    response = requests.get(epg_url)
    if response.status_code != 200:
        print(f"ERROR: {origen} no disponible")
        return

    movistarEPG = response.json()
    csv_data = []

    for grupo in movistarEPG:
        logo_url = ""
        for logo_info in grupo.get("Logos", []):
            if logo_info.get("id") == "nobox_dark":
                logo_url = logo_info.get("uri", "")
                break
        csv_data.append({
            "CasId": grupo.get("CasId", ""),
            "CodCadenaTv": grupo.get("CodCadenaTv", ""),
            "Nombre": grupo.get("Nombre", "").replace("\t", "").replace("\n", ""),
            "Logo": logo_url,
            "PuntoReproduccion": grupo.get("PuntoReproduccion", ""),
            "FormatoVideo": grupo.get("FormatoVideo", "")
        })

    existing_data = load_existing_data(filepath)
    changes = detect_changes(existing_data, csv_data, origen)
    if changes:
        write_changes(changes)

    headers = ["CasId", "CodCadenaTv", "Nombre", "Logo", "PuntoReproduccion", "FormatoVideo"]
    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(csv_data)

    print(f"{origen} exportado a {filepath}. Cambios detectados: {len(changes)}")


def flujo_vaginal():
    export_movistarEPG_to_csv(ott_url, ott_csv_filepath, "OTT")
    export_movistarEPG_to_csv(difusion_url, difusion_csv_filepath, "DIFUSION")


flujo_vaginal()
