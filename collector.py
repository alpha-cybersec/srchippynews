import json
import os
import sys

import requests


URL = "https://gbhackers.com/wp-json/wp/v2/posts"


def main():

    print("")
    print("############################################")
    print("#      GBHACKERS WORDPRESS API TEST        #")
    print("############################################")
    print("")

    print(f"[+] URL: {URL}")
    print("[+] Realizando GET directo...")
    print("[+] Sin parámetros.")
    print("[+] Sin filtros.")
    print("[+] Sin fechas.")
    print("")

    try:

        response = requests.get(
            URL,
            timeout=30
        )

    except Exception as exc:

        print(f"[ERROR] Error de conexión: {exc}")
        sys.exit(1)

    print("=" * 70)

    print(
        f"[+] HTTP Status: "
        f"{response.status_code}"
    )

    print(
        f"[+] URL final: "
        f"{response.url}"
    )

    print(
        f"[+] Content-Type: "
        f"{response.headers.get('content-type', 'UNKNOWN')}"
    )

    print(
        f"[+] Bytes recibidos: "
        f"{len(response.content)}"
    )

    print("=" * 70)
    print("")

    # --------------------------------------------------------
    # SI NO ES 200
    # --------------------------------------------------------

    if response.status_code != 200:

        print(
            f"[ERROR] El servidor respondió "
            f"HTTP {response.status_code}"
        )

        print("")
        print(
            "[DEBUG] Primeros 1000 caracteres "
            "de la respuesta:"
        )

        print("")
        print(response.text[:1000])

        # Guardar respuesta igualmente para revisarla
        os.makedirs(
            "data",
            exist_ok=True
        )

        error_file = (
            "data/gbhackers_wp_error.html"
        )

        with open(
            error_file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(response.text)

        print("")
        print(
            f"[DEBUG] Respuesta guardada en: "
            f"{error_file}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # INTENTAR INTERPRETAR JSON
    # --------------------------------------------------------

    try:

        data = response.json()

    except Exception as exc:

        print(
            "[ERROR] HTTP 200 pero la respuesta "
            "no pudo convertirse a JSON."
        )

        print(
            f"[ERROR] {exc}"
        )

        print("")
        print(response.text[:1000])

        sys.exit(1)

    # --------------------------------------------------------
    # MOSTRAR TIPO DE RESPUESTA
    # --------------------------------------------------------

    print(
        f"[SUCCESS] JSON recibido correctamente."
    )

    print(
        f"[+] Tipo Python recibido: "
        f"{type(data).__name__}"
    )

    # WordPress normalmente devuelve una lista.
    if isinstance(data, list):

        print(
            f"[+] Elementos recibidos: "
            f"{len(data)}"
        )

    elif isinstance(data, dict):

        print(
            f"[+] Claves principales: "
            f"{list(data.keys())}"
        )

    # --------------------------------------------------------
    # GUARDAR TODO, SIN MODIFICAR
    # --------------------------------------------------------

    os.makedirs(
        "data",
        exist_ok=True
    )

    output_file = (
        "data/gbhackers_wp_raw.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("")
    print(
        f"[SUCCESS] JSON completo guardado en:"
    )

    print(
        f"          {output_file}"
    )

    # --------------------------------------------------------
    # MOSTRAR INFORMACIÓN DEL PRIMER POST
    # --------------------------------------------------------

    if isinstance(data, list) and data:

        first = data[0]

        print("")
        print("=" * 70)
        print("PRIMER POST RECIBIDO")
        print("=" * 70)

        print("")
        print(
            f"ID: "
            f"{first.get('id', '')}"
        )

        print(
            f"Date: "
            f"{first.get('date', '')}"
        )

        print(
            f"Date GMT: "
            f"{first.get('date_gmt', '')}"
        )

        print(
            f"Slug: "
            f"{first.get('slug', '')}"
        )

        print(
            f"Status: "
            f"{first.get('status', '')}"
        )

        print(
            f"Link: "
            f"{first.get('link', '')}"
        )

        title = first.get(
            "title",
            {}
        )

        if isinstance(title, dict):

            print(
                f"Title: "
                f"{title.get('rendered', '')}"
            )

        print("")
        print(
            "[+] Campos disponibles en el post:"
        )

        print("")

        for key in first.keys():
            print(f" - {key}")

        print("")
        print("=" * 70)

    print("")
    print("############################################")
    print("#             TEST COMPLETADO              #")
    print("############################################")


if __name__ == "__main__":
    main()
