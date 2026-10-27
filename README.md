# clarus-data

Cópia de reserva dos **setores de risco geológico do SGB (Serviço Geológico do Brasil)** para
Porto Alegre, usada pelo app Clarus **somente quando a fonte oficial está indisponível**.

> Esta não é a fonte oficial. Os dados pertencem ao SGB e são consultados em
> [geoportal.sgb.gov.br](https://geoportal.sgb.gov.br/geosgb/). A cópia pode estar
> desatualizada em relação à fonte; o app sempre mostra a data da cópia quando a usa.

## Arquivos publicados

| Caminho | Conteúdo |
|---|---|
| [`sgb/porto-alegre/risk-sectors.json`](https://clarus-org.github.io/clarus-data/sgb/porto-alegre/risk-sectors.json) | Envelope versionado (`schemaVersion: 1`) com a resposta original do FeatureServer do SGB em `arcgis`, a data do download (`fetchedAt`), a contagem de setores e um `sha256` informativo |
| [`meta/status.json`](https://clarus-org.github.io/clarus-data/meta/status.json) | Última verificação (`lastCheckedAt`) e se os dados mudaram nela |

## Como a cópia é atualizada

O workflow [`refresh-sgb.yml`](.github/workflows/refresh-sgb.yml) roda todo dia às 06:00
(Brasília) e:

1. baixa os setores do SGB com a mesma consulta que o app usa;
2. valida a resposta e **recusa** resposta vazia, truncada (`exceededTransferLimit`), com setor sem polígono ou com
   queda maior que 20% no número de setores (testes em `scripts/sgb/test_update_sgb_snapshot.py`
   no repositório do app);
3. grava o arquivo, registra o batimento em `meta/status.json` e faz commit;
4. publica tudo no GitHub Pages.

Se a validação falhar, o job falha, a cópia anterior continua publicada e o GitHub envia e-mail.

### Rodar manualmente

```bash
gh workflow run refresh-sgb.yml -R clarus-org/clarus-data
# Queda legítima de mais de 20% nos setores:
gh workflow run refresh-sgb.yml -R clarus-org/clarus-data -f force=true
```

O script `scripts/update_sgb_snapshot.py` é cópia do original em `scripts/sgb/` (repositório
do app). Altere lá primeiro e copie para cá.

## Atribuição

Fonte dos dados: SGB — Serviço Geológico do Brasil, setorização de áreas de risco geológico.
