import requests
import csv
import os
from datetime import datetime

ott_url = "https://ottcache.dof6.com/movistarplus/webplayer/OTT/contents/epg"
ott_csv_filepath = "ott.csv"
difusion_url = "https://ottcache.dof6.com/movistarplus/webplayer/DIFUSION/contents/epg"
difusion_csv_filepath = "difusion.csv"
cambios_filepath = "cambios.csv"

data_fields = ["CasId", "CodCadenaTv", "Nombre", "Logo", "PuntoReproduccion", "FormatoVideo"]

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

    all_keys = set(old_data_dict.keys()) | set(new_data_dict.keys())

    for casid in all_keys:
        old_row = old_data_dict.get(casid, {})
        new_row = new_data_dict.get(casid, {})

        if not old_row:
            cambio = "Añadido"
        elif not new_row:
            cambio = "Eliminado"
        elif old_row != new_row:
            cambio = "Modificado"
        else:
            continue  # sin cambios

        change_row = {
            "Fecha": date_now,
            "Origen": origen,
            "Cambio": cambio,
            "CasId": casid,
        }

        for field in data_fields:
            old_val = old_row.get(field, "")
            new_val = new_row.get(field, "")

            if cambio == "Modificado":
                if old_val != new_val:
                    change_row[f"Antes_{field}"] = old_val
                    change_row[f"Despues_{field}"] = new_val
                else:
                    change_row[f"Antes_{field}"] = ""
                    change_row[f"Despues_{field}"] = ""
            elif cambio == "Añadido":
                change_row[f"Antes_{field}"] = ""
                change_row[f"Despues_{field}"] = new_val
            elif cambio == "Eliminado":
                change_row[f"Antes_{field}"] = old_val
                change_row[f"Despues_{field}"] = ""

        changes.append(change_row)

    return changes

def write_changes(changes):
    file_exists = os.path.exists(cambios_filepath)
    with open(cambios_filepath, mode='a', newline='', encoding='utf-8') as f:
        fieldnames = ["Fecha", "Origen", "Cambio", "CasId"] + \
                     [f"Antes_{f}" for f in data_fields] + \
                     [f"Despues_{f}" for f in data_fields]
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

    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data_fields)
        writer.writeheader()
        writer.writerows(csv_data)

    print(f"{origen} exportado a {filepath}. Cambios detectados: {len(changes)}")

def flujo_vaginal():
    export_movistarEPG_to_csv(ott_url, ott_csv_filepath, "OTT")
    export_movistarEPG_to_csv(difusion_url, difusion_csv_filepath, "DIFUSION")

flujo_vaginal()
