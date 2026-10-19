"""Envio del resumen semanal a un canal de Microsoft Teams (Workflows con webhook).

La URL del webhook vive en la variable de entorno TEAMS_WEBHOOK_URL (produccion, secreto
del repositorio) o en config/interno.yaml (pruebas locales, fuera de git). Si no hay URL no
se envia nada, y un fallo de red nunca detiene el pipeline.
"""

import os
from pathlib import Path

import requests

from src.utils import config
from src.utils.logs import obtener_logger
from src.visual import graficos as G

log = obtener_logger("teams")
TIMEOUT_SEGUNDOS = 15
NOMBRE_IMAGEN = "grafico_{semana}.png"


def url_webhook():
    """URL del webhook: variable de entorno o config/interno.yaml."""
    return os.environ.get("TEAMS_WEBHOOK_URL") or config.interno().get("teams_webhook_url")


def nombre_pdf(semana):
    """Nombre del PDF semanal, igual que en src/report."""
    return f"{config.proyecto()['slug']}_{semana}.pdf"


def url_release(semana, nombre, repositorio=None):
    """URL publica de un archivo del Release de la semana. GitHub Actions define GITHUB_REPOSITORY."""
    repositorio = repositorio or os.environ.get("GITHUB_REPOSITORY", "")
    if not repositorio:
        return None
    return f"https://github.com/{repositorio}/releases/download/semana-{semana}/{nombre}"


def generar_imagen(resumen, narrativa, destino=None):
    """PNG del grafico de precio por hora de la semana, listo para subir al Release."""
    destino = Path(destino or config.DIR_REPORTS / NOMBRE_IMAGEN.format(semana=resumen.semana))
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig = G.perfil_horario(resumen.perfil_cmg, narrativa.titulos_graficos["precios_perfil"])
    destino.write_bytes(G.a_png(fig).getvalue())
    log.info("Imagen de la semana guardada en %s", destino.name)
    return destino


def construir_tarjeta(resumen, narrativa, imagen_url=None, dashboard_url=None, pdf_url=None):
    """Tarjeta Adaptive Card: titulares, imagen opcional y botones opcionales."""
    cuerpo = [
        {"type": "TextBlock", "text": f"Cuánto COESta · {resumen.texto_semana} ({resumen.semana})",
         "weight": "Bolder", "size": "Medium", "wrap": True},
    ]
    if resumen.es_preliminar:
        cuerpo.append({"type": "TextBlock", "text": "Datos preliminares del COES.", "isSubtle": True, "wrap": True})
    if imagen_url:
        cuerpo.append({"type": "Image", "url": imagen_url, "altText": "Precio promedio por hora de la semana",
                       "size": "Stretch"})
    cuerpo += [{"type": "TextBlock", "text": f"• {titular}", "wrap": True} for titular in narrativa.titulares]
    cuerpo.append({"type": "TextBlock", "text": config.proyecto()["aviso"].strip(),
                   "size": "Small", "isSubtle": True, "wrap": True})
    contenido = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": cuerpo,
    }
    acciones = []
    if dashboard_url:
        acciones.append({"type": "Action.OpenUrl", "title": "Abrir dashboard", "url": dashboard_url})
    if pdf_url:
        acciones.append({"type": "Action.OpenUrl", "title": "Descargar PDF", "url": pdf_url})
    if acciones:
        contenido["actions"] = acciones
    return {
        "type": "message",
        "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": contenido}],
    }


def enviar(resumen, narrativa, imagen_url=None, dashboard_url=None, pdf_url=None, url=None):
    """Publica la tarjeta en el canal. Devuelve True si Teams acepto el mensaje."""
    url = url or url_webhook()
    if not url:
        log.info("No hay URL de Teams configurada: no se envia nada")
        return False
    tarjeta = construir_tarjeta(resumen, narrativa, imagen_url, dashboard_url, pdf_url)
    try:
        respuesta = requests.post(url, json=tarjeta, timeout=TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
    except requests.RequestException as error:
        # El texto del error incluye la URL del webhook, que es un secreto: solo se registra el tipo
        log.error("No se pudo enviar el resumen a Teams (%s)", type(error).__name__)
        return False
    log.info("Resumen de %s enviado a Teams", resumen.semana)
    return True
