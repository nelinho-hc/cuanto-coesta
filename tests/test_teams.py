from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests

from src.notify import teams

RESUMEN = SimpleNamespace(semana="2026-W41", texto_semana="Semana cara", es_preliminar=True)
NARRATIVA = SimpleNamespace(titulares=["Semana cara: el costo marginal subió 32.2%"])


@pytest.fixture
def sin_configuracion(monkeypatch):
    """Sin URL en variables de entorno ni en config/interno.yaml, sea cual sea el equipo."""
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(teams.config, "interno", lambda: {})


def test_sin_url_no_envia(monkeypatch, sin_configuracion):
    post = MagicMock()
    monkeypatch.setattr(teams.requests, "post", post)
    assert teams.enviar(RESUMEN, NARRATIVA) is False
    post.assert_not_called()


def test_envia_tarjeta_al_webhook(monkeypatch, sin_configuracion):
    post = MagicMock(return_value=MagicMock(status_code=202))
    monkeypatch.setattr(teams.requests, "post", post)
    assert teams.enviar(RESUMEN, NARRATIVA, url="https://ejemplo.invalido/webhook") is True
    contenido = post.call_args.kwargs["json"]["attachments"][0]["content"]
    assert contenido["type"] == "AdaptiveCard"


def test_tarjeta_con_imagen_y_botones():
    tarjeta = teams.construir_tarjeta(RESUMEN, NARRATIVA, imagen_url="https://ejemplo.invalido/g.png",
                                      dashboard_url="https://ejemplo.invalido/app",
                                      pdf_url="https://ejemplo.invalido/r.pdf")
    contenido = tarjeta["attachments"][0]["content"]
    assert any(bloque["type"] == "Image" for bloque in contenido["body"])
    assert [a["title"] for a in contenido["actions"]] == ["Abrir dashboard", "Descargar PDF"]


def test_tarjeta_sin_imagen_ni_botones():
    contenido = teams.construir_tarjeta(RESUMEN, NARRATIVA)["attachments"][0]["content"]
    assert "actions" not in contenido
    assert not any(bloque["type"] == "Image" for bloque in contenido["body"])


def test_error_de_red_no_detiene(monkeypatch, sin_configuracion):
    monkeypatch.setattr(teams.requests, "post", MagicMock(side_effect=requests.ConnectionError("sin red")))
    assert teams.enviar(RESUMEN, NARRATIVA, url="https://ejemplo.invalido/webhook") is False


def test_url_release_con_repositorio(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "dueno/repo")
    assert teams.url_release("2026-W41", "a.pdf") == \
        "https://github.com/dueno/repo/releases/download/semana-2026-W41/a.pdf"


def test_url_release_sin_repositorio(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert teams.url_release("2026-W41", "a.pdf") is None
