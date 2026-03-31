# Automação Guias Bradesco Saúde

Automatiza o download de guias SADT do portal Bradesco Saúde via Selenium, com controle de duplicatas por hash MD5.
---
## Requisitos

- Python 3.7+
- Google Chrome instalado
- Selenium (instalado via `requirements.txt`)

---

## Instalação

```bash
# Clone ou baixe o repositório, então instale as dependências:
pip install -r requirements.txt
```

O `requirements.txt` contém:

```
selenium
```

> O Selenium já inclui o ChromeDriver embutido (versão 4.x+). Não é necessário baixar o ChromeDriver separadamente.

---

## Como Usar

### Opção 1 — Via arquivo `.bat` (recomendado)

Dê dois cliques em **`iniciar.bat`** ou execute pelo CMD:

```cmd
iniciar.bat
```

O script faz automaticamente:
1. Abre o Chrome em modo debug na porta `9223` com perfil isolado
2. Aguarda você fazer login no portal Bradesco Saúde
3. Após pressionar ENTER, inicia a automação

### Opção 2 — Manual via CMD

```cmd
REM 1. Abra o Chrome com debug habilitado
chrome.exe --remote-debugging-port=9223 --user-data-dir="C:\temp\chrome"

REM 2. Faça login no portal Bradesco Saúde no Chrome que abriu

REM 3. Execute o script
python script2.py
```

---

## Configuração

Edite as constantes no início do `script2.py`:

```python
# Códigos dos prestadores a processar
CODIGOS = ["0000994402"]

# Período de busca (formato DD/MM/AAAA)
DATA_INICIAL = "18/03/2026"
DATA_FINAL   = "18/03/2026"

# Timeouts (em segundos)
TIMEOUT_CURTO = 10
TIMEOUT_MEDIO = 20
TIMEOUT_LONGO = 40
```

---

## Onde os arquivos são salvos

Os PDFs são salvos na pasta **Downloads** do usuário (`~/Downloads`), com nome no formato:

```
NOME_PACIENTE_1.pdf
NOME_PACIENTE_2.pdf
NOME_PACIENTE_3.pdf
```

O log de execução é salvo em:

```
~/Downloads/automacao_bradesco.log
```

---

## Sistema de ID Único (Anti-Duplicata)

Cada guia recebe um ID gerado a partir de:

- Conteúdo das 8 colunas da linha da tabela
- Timestamp com microsegundos
- Hash MD5 (16 caracteres)

```python
# Resultado: NomeCurto_a3f9e2b4c1d5e6f7
id_final = f"{nome_curto}_{id_hash}"
```

Guias já processadas na mesma execução são ignoradas automaticamente:

```log
*** PULANDO (JA PROCESSADA) ***
```

---

## Funções Principais

| Função | Descrição |
|---|---|
| `gerar_id_unico_robusto()` | Gera hash MD5 único por guia |
| `renomear_guia_sadt_imediato()` | Aguarda e renomeia `GuiaSADT.pdf` com nome do paciente |
| `verificar_e_tratar_erro_interno()` | Detecta erros do portal e clica em Voltar |
| `verificar_e_fechar_modal_erro()` | Fecha modais de erro automaticamente |
| `fechar_aba_about_blank()` | Fecha abas temporárias abertas pelo Chrome |
| `aguardar_e_clicar()` | Clica em elementos com scroll e retry |
| `validar_formato_data()` | Valida datas no formato DD/MM/AAAA |
| `limpar_nome_arquivo()` | Remove caracteres inválidos do nome do PDF |

---

## Logs

Exemplo de execução bem-sucedida:

```log
2026-03-18 14:30:25 - INFO - ============================================================
2026-03-18 14:30:25 - INFO - [1/3] PROCESSANDO: JOÃO DA SILVA
2026-03-18 14:30:25 - INFO -    ID: JOAO_DA_SILVA_a3f9e2b4c1d5
2026-03-18 14:30:26 - INFO -  [OK] Renomeado: JOAO_DA_SILVA_1.pdf (45.2 KB)
2026-03-18 14:30:26 - INFO -  [i] Total de guias do paciente: 1
```

Marcadores nos logs:

| Marcador | Significado |
|---|---|
| `[OK]` | Operação concluída com sucesso |
| `[i]` | Informação de progresso |
| `[!]` | Aviso (erro recuperável) |
| `[X]` | Erro crítico |
| `[DEBUG]` | Dados internos para diagnóstico |

---

## Troubleshooting

**Chrome não conecta:**
- Verifique se o Chrome abriu com a porta `9223`
- Use o `iniciar.bat` para garantir os parâmetros corretos

**`GuiaSADT.pdf` não encontrado:**
- O portal pode estar instável; o script tenta novamente na próxima execução
- Verifique se o download não foi bloqueado pelo Chrome

**Logs muito grandes:**
```python
# Altere o nível no script2.py:
logging.basicConfig(level=logging.WARNING)
```

**Python não encontrado (ao usar o .bat):**
- Instale o Python em [python.org](https://python.org) marcando a opção **"Add to PATH"**

---

## Checklist

Antes de executar:

- [ ] `requirements.txt` instalado (`pip install -r requirements.txt`)
- [ ] `CODIGOS` configurado em `script2.py`
- [ ] Datas configuradas em `DATA_INICIAL` e `DATA_FINAL`
- [ ] Espaço disponível na pasta Downloads

Após executar:

- [ ] Verificar `[***] Concluido! X/Y baixadas` no log
- [ ] Conferir PDFs na pasta Downloads
- [ ] Revisar o log em busca de `[X]` ou `[!]`

---

**Versão:** 2.0 | **Python:** 3.7+ | **Selenium:** 4.x
