# GHG API — FastAPI + LibreOffice

API de teste para usar a planilha GHG Protocol Brasil como motor de cálculo.

## O que mudou na versão 0.2

- LibreOffice fica iniciado e reutilizado entre requisições.
- Cada cálculo é feito por categoria.
- Resultados retornam somente a categoria solicitada.
- Mantido o endpoint antigo `/api/emissoes/calcular` para compatibilidade.

## Subir localmente

Coloque `ferramenta_ghg_protocol_v2026.0.1.xlsx` em `modelos/` e rode:

```bash
docker compose up --build
```

Abra `http://localhost:8000/docs`.

## Endpoints

### Emissões fugitivas

```http
POST /api/emissoes/calcular/emissoes-fugitivas
```

### Combustão estacionária

```http
POST /api/emissoes/calcular/combustao-estacionaria
```

### Combustão móvel

```http
POST /api/emissoes/calcular/combustao-movel
```

O corpo segue o formato:

```json
{
  "alteracoes": {
    "Emissões fugitivas": {
      "B61": "TESTE",
      "C61": "HFC-23",
      "E61": 5,
      "F61": 5,
      "G61": 5,
      "H61": 5,
      "I61": 5
    }
  }
}
```

A aba `Introdução` pode ser enviada junto se o cálculo depender desses dados.

## Teste com curl

```bash
curl -X POST http://localhost:8000/api/emissoes/calcular/emissoes-fugitivas ^
  -H "Content-Type: application/json" ^
  --data-binary "@tests/payload-emissoes-fugitivas-extintor.json"
```

No PowerShell, use `curl.exe` ou o Swagger em `/docs`.
