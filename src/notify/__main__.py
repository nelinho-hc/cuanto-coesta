"""Linea de comandos de la notificacion a Teams. Usa datos ya procesados (no descarga nada).

Uso (en GitHub Actions, despues de publicar el Release):
  python -m src.notify imagen --semana 2026-W41    # imprime la ruta del PNG
  python -m src.notify enviar --semana 2026-W41    # envia la tarjeta al canal
"""

import argparse
import os
import sys

from src.analysis import calcular_resumen
from src.narrative import generar_narrativa
from src.notify import teams
from src.utils.logs import configurar_logging


def main(argv=None):
    parser = argparse.ArgumentParser(description="Notificacion semanal a Teams")
    parser.add_argument("accion", choices=["imagen", "enviar"])
    parser.add_argument("--semana", required=True, help="AAAA-Www")
    args = parser.parse_args(argv)
    configurar_logging()
    resumen = calcular_resumen(args.semana)
    narrativa = generar_narrativa(resumen)
    if args.accion == "imagen":
        print(teams.generar_imagen(resumen, narrativa))
        return 0
    imagen_url = teams.url_release(args.semana, teams.NOMBRE_IMAGEN.format(semana=args.semana))
    pdf_url = teams.url_release(args.semana, teams.nombre_pdf(args.semana))
    dashboard_url = os.environ.get("TEAMS_DASHBOARD_URL") or None
    teams.enviar(resumen, narrativa, imagen_url=imagen_url, dashboard_url=dashboard_url, pdf_url=pdf_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
