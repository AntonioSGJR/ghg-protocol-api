from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .utils import CELLS, calcular_emissao, get_result_cells, validar_categoria


BASE_DIR = Path(__file__).resolve().parent.parent
MODELO = BASE_DIR / "modelos" / "ferramenta_ghg_protocol_v2026.0.1.xlsx"

app = FastAPI(
    title="GHG Protocol - Motor de Cálculo",
    version="0.2.0",
    description="API para cálculo de emissões usando a planilha GHG Protocol Brasil.",
)


class CalculoRequest(BaseModel):
    alteracoes: dict[str, dict[str, Any]] = Field(
        ...,
        description="Mapa de abas -> células -> valores. Pode conter Introdução e a categoria calculada.",
    )


@app.get("/")
def root():
    return {"status": "ok", "service": "ghg-calculator", "version": app.version}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "modelo_existe": MODELO.exists(),
        "modelo": MODELO.name,
        "categorias": list(CELLS),
    }


@app.get("/api/emissoes/categorias")
def categorias():
    return {
        "categorias": [
            {"slug": "emissoes-fugitivas", "nome": "Emissões fugitivas"},
            {"slug": "combustao-estacionaria", "nome": "Combustão estacionária"},
            {"slug": "combustao-movel", "nome": "Combustão móvel"},
            {"slug": "energia-eletrica", "nome": "En. elétrica (localização)"},
            {"slug": "emissao-casa-trabalho", "nome": "Emissões casa-trabalho"},
            {"slug": "viagens-negocios", "nome": "Viagens a Negócios"},

        ]
    }


SLUG_TO_SHEET = {
    "emissoes-fugitivas": "Emissões fugitivas",
    "combustao-estacionaria": "Combustão estacionária",
    "combustao-movel": "Combustão móvel",
    "energia-eletrica": "En. elétrica (localização)",
    "emissao-casa-trabalho": "Emissões casa-trabalho",
    "viagens-negocios": "Viagens a Negócios",
}


@app.post("/api/emissoes/calcular/{slug}")
def calcular_categoria(slug: str, request: CalculoRequest):
    categoria = SLUG_TO_SHEET.get(slug)
    if not categoria:
        raise HTTPException(status_code=404, detail=f"Categoria '{slug}' não encontrada.")

    if not MODELO.exists():
        raise HTTPException(status_code=500, detail=f"Planilha modelo não encontrada: {MODELO}")

    # Garante que o request realmente contém a categoria solicitada.
    try:
        validar_categoria(categoria)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with TemporaryDirectory() as temp_dir:
        arquivo_resultado = Path(temp_dir) / "resultado.xlsx"
        try:
            calcular_emissao(MODELO, arquivo_resultado, request.alteracoes)
            resultados = get_result_cells(arquivo_resultado, categoria)

            return {
                "status": "sucesso",
                "categoria": categoria,
                "resultados": resultados,
            }
        except FileNotFoundError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Erro durante o cálculo: {exc}") from exc


# Mantido para compatibilidade com o teste anterior.
@app.post("/api/emissoes/calcular")
def calcular_compat(request: CalculoRequest):
    if not request.alteracoes:
        raise HTTPException(status_code=400, detail="Nenhuma alteração foi enviada.")

    categorias_presentes = [sheet for sheet in CELLS if sheet in request.alteracoes]
    if not categorias_presentes:
        raise HTTPException(status_code=400, detail="Nenhuma categoria de cálculo foi enviada.")

    # O endpoint antigo continua funcionando, mas agora calcula as categorias uma a uma internamente.
    resultados = {}
    for categoria in categorias_presentes:
        with TemporaryDirectory() as temp_dir:
            arquivo_resultado = Path(temp_dir) / "resultado.xlsx"
            calcular_emissao(MODELO, arquivo_resultado, request.alteracoes)
            resultados[categoria] = get_result_cells(arquivo_resultado, categoria)

    return {"status": "sucesso", "resultados": resultados}
