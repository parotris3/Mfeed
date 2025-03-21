import requests
import csv

ott_url = "https://ottcache.dof6.com/movistarplus/webplayer/OTT/contents/epg"
ott_csv_filepath = "ott.csv"
difusion_url = "https://ottcache.dof6.com/movistarplus/webplayer/DIFUSION/contents/epg"
difusion_csv_filepath = "difusion.csv"

def export_movistarEPG_to_csv(epg_url, filepath):

    response = requests.get(epg_url)
    if response.status_code == 200:
        movistarEPG = response.json()
    else:
        print("ERROR: movistarEPG no disponible")
        return

    csv_data = []
    for indice, grupo in enumerate(movistarEPG):
        # Busca el logo con 'id': 'nobox_dark' dentro de la lista 'Logos'
        logo_url = ""  # Inicializa logo_url
        for logo_info in grupo.get("Logos", []):  # Itera sobre la lista Logos (o una lista vacía si no existe)
            if logo_info.get("id") == "nobox_dark":
                logo_url = logo_info.get("uri", "")  # Obtiene la URI
                break  # Sale del bucle interno una vez que encuentra el logo correcto

        csv_data.append({
            "CasId": grupo.get("CasId", ""),
            "CodCadenaTv": grupo.get("CodCadenaTv", ""),
            "Nombre": grupo.get("Nombre", "").replace("\t", "").replace("\n", ""),
            "Logo": logo_url,
            "PuntoReproduccion": grupo.get("PuntoReproduccion", ""),
            "FormatoVideo": grupo.get("FormatoVideo", ""),
        })

    # Define CSV headers
    headers = ["CasId", "CodCadenaTv", "Nombre", "Logo", "PuntoReproduccion", "FormatoVideo"]

    # Write CSV data to file
    with open(filepath, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers, delimiter=',')
        writer.writeheader()
        writer.writerows(csv_data)

    print(f"movistarEPG exported to {filepath}")


def flujo_vaginal():

    export_movistarEPG_to_csv(ott_url, ott_csv_filepath)
    export_movistarEPG_to_csv(difusion_url, difusion_csv_filepath)


flujo_vaginal()
