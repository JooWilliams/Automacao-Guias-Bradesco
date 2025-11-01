# 🏥 Automação de Download de Guias - Bradesco Saúde

> Um robô inteligente que baixa automaticamente suas guias do portal Bradesco Saúde, salvando horas de trabalho manual!

---

## 📖 A História Por Trás do Projeto

Imagine ter que entrar no portal do Bradesco Saúde todos os dias e baixar dezenas (ou centenas!) de guias médicas, uma por uma. Clicar, esperar carregar, salvar, renomear... e repetir isso 100 vezes. 😫

Foi exatamente isso que motivou a criação desta automação! O que antes levava horas, agora leva minutos. O robô faz todo o trabalho chato enquanto você toma um café. ☕

---

## ✨ O Que Este Robô Faz?

- 🔐 Conecta-se ao seu Chrome já logado (sem precisar de senha!)
- 📅 Busca guias por período (você escolhe as datas)
- 🔍 Encontra todas as guias com status "Liberada"
- 📥 Baixa os PDFs automaticamente
- 📝 Renomeia os arquivos com o nome do beneficiário
- 🔄 Se o site "travar", ele recarrega e continua de onde parou
- 🛡️ Evita baixar a mesma guia duas vezes
- 📊 Mostra logs detalhados de tudo que está fazendo

---

## 🚀 Como Usar (Passo a Passo)

### 1️⃣ Preparação Inicial

#### **Instale o Python** (se ainda não tiver)
- Baixe em: [python.org](https://www.python.org/downloads/)
- Durante a instalação, marque "Add Python to PATH" ✅

#### **Instale as Bibliotecas Necessárias**
Abra o terminal (CMD ou PowerShell) e digite:

```bash
pip install selenium
```

#### **Instale o ChromeDriver**
O Selenium precisa do ChromeDriver para controlar o Chrome:
- Baixe em: [chromedriver.chromium.org](https://chromedriver.chromium.org/downloads)
- Escolha a versão compatível com seu Chrome
- Extraia e coloque na mesma pasta do script

---

### 2️⃣ Configuração do Código

Abra o arquivo Python e ajuste estas linhas:

```python
# Códigos dos convênios que você quer processar
CODIGOS = ["0000994402"]  # Coloque seu(s) código(s) aqui
```

Se você tem mais de um código, adicione assim:
```python
CODIGOS = ["0000994402", "0000123456", "0000789012"]
```

---

### 3️⃣ Executando a Automação

#### **Passo 1: Abra o Chrome em Modo Debug**
No terminal (CMD), digite:

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\selenium-chrome"
```

> 💡 **Dica:** Crie um arquivo `.bat` com esse comando para facilitar!

#### **Passo 2: Faça Login no Portal**
No Chrome que abriu:
1. Acesse o portal Bradesco Saúde
2. Faça login normalmente
3. **Deixe essa janela aberta!** O robô vai usar essa sessão

#### **Passo 3: Execute o Script**
Em outro terminal, na pasta do script:

```bash
python automacao_bradesco.py
```

#### **Passo 4: Informe as Datas**
O script vai perguntar:
```
Data inicial (DD/MM/AAAA): 01/11/2024
Data final (DD/MM/AAAA): 30/11/2024
```

#### **Passo 5: Relaxe! ☕**
O robô vai fazer todo o resto! Você pode acompanhar pelos logs.

---

## 🎬 Como Funciona Por Dentro?

### **Etapa 1: Conexão** 🔌
```
[+] Conectando ao Chrome existente...
[OK] Conectado com sucesso!
```
O robô conecta ao Chrome que você já abriu e logou.

---

### **Etapa 2: Navegação** 🧭
```
[>>] ETAPA 1: Acessando 'Servicos' > 'Senha Web'...
[OK] Menu 'Servicos' aberto
[OK] 'Senha Web' clicado
```
Navega automaticamente pelos menus do portal.

---

### **Etapa 3: Seleção de Código** 🔑
```
[>>] ETAPA 2: Selecionando codigo 0000994402...
[OK] Codigo 0000994402 selecionado
[OK] Botao 'Continuar' clicado
```
Seleciona o convênio correto.

---

### **Etapa 4: Nova Consulta** 📅
```
[>>] ETAPA 3: Realizando nova consulta (01/11/2024 ate 30/11/2024)...
[OK] 'Nova Consulta' clicado
[OK] Data inicial: 01/11/2024
[OK] Data final: 30/11/2024
[OK] Botao 'Consultar' clicado
[OK] Resultados carregados
```
Busca as guias no período que você escolheu.

---

### **Etapa 5: Processamento** 🔄
```
[i] 100 guia(s) 'Liberada' encontrada(s)

============================================================
[1/100] PROCESSANDO: JOAO SILVA
   Arquivo: JOAO_SILVA
============================================================
   [OK] Linha selecionada
   [i] 'Informacoes do Beneficiario' clicado
   [i] Botao 'PDF' clicado - download INSTANTANEO
   [OK] GuiaSADT.pdf encontrado!
   [OK] Renomeado: JOAO_SILVA_1.pdf (145.3 KB)
   [***] Guia salva com sucesso!
   [<-] Voltou a tabela
```

Para cada guia, o robô:
1. Seleciona a linha
2. Clica em "Informações do Beneficiário"
3. Clica em "PDF"
4. Captura o download instantâneo
5. Renomeia com o nome do paciente
6. Volta para a tabela
7. Vai para a próxima!

---

### **Etapa 6: Proteção Contra Erros** 🛡️

Se o site "perder" guias da tabela:

```
[!] INCONSISTENCIA DETECTADA!
    Esperado: 100 guias | Encontrado: 87 guias

[>>] Tentativa 1/3: Recarregando tabela...
[>>] ETAPA 3: Realizando nova consulta (01/11/2024 ate 30/11/2024)...
[OK] Tabela recarregada! Continuando do indice atual...

[39/100] PROCESSANDO: ANA LIMA ✅
```

O robô:
- Detecta que algo deu errado
- Recarrega a tabela automaticamente
- Continua de onde parou (não perde progresso!)

---

## 📂 Onde os Arquivos São Salvos?

Os PDFs vão para sua pasta **Downloads** com nomes organizados:

```
📁 Downloads/
   📄 JOAO_SILVA_1.pdf
   📄 JOAO_SILVA_2.pdf
   📄 MARIA_SANTOS_1.pdf
   📄 PEDRO_COSTA_1.pdf
   ...
```

Se o mesmo paciente tiver várias guias, elas são numeradas automaticamente!

---

## 🎯 Recursos Especiais

### 🔢 **Numeração Inteligente**
Se "João Silva" tem 3 guias, você terá:
- `JOAO_SILVA_1.pdf`
- `JOAO_SILVA_2.pdf`
- `JOAO_SILVA_3.pdf`

### 🚫 **Anti-Duplicação**
O robô lembra quais guias já baixou. Mesmo se você rodar o script de novo, ele não baixa duplicados!

### 📝 **Log Completo**
Tudo é registrado no arquivo `automacao_bradesco.log` na pasta Downloads.

### 🔄 **Auto-Recuperação**
Se o site travar ou dar erro, o robô tenta:
1. Fechar popups de erro
2. Recarregar a página
3. Continuar de onde parou

---

## ⚙️ Configurações Avançadas

### **Alterar Timeouts**
Se sua internet é lenta, aumente os tempos de espera:

```python
TIMEOUT_CURTO = 10   # Era 10, tente 15
TIMEOUT_MEDIO = 20   # Era 20, tente 30
TIMEOUT_LONGO = 30   # Era 30, tente 45
```

### **Alterar Pasta de Downloads**
Por padrão usa `C:\Users\SeuUsuario\Downloads`. Para mudar:

```python
PASTA_DOWNLOADS = Path("C:/MinhaPasta/Guias")
```

### **Processar Múltiplos Códigos**
```python
CODIGOS = [
    "0000994402",
    "0000123456",
    "0000789012"
]
```

O robô vai processar todos, um por vez!

---

## 🐛 Solução de Problemas

### ❌ "Chrome não tem janelas abertas"
**Solução:** Abra o Chrome com o comando debug antes de rodar o script.

### ❌ "Elemento não encontrado"
**Solução:** O site pode ter mudado. Verifique se você está logado e na página correta.

### ❌ "GuiaSADT.pdf não encontrado"
**Solução:** 
- Verifique se o Chrome está configurado para baixar PDFs automaticamente
- Certifique-se de que a pasta Downloads existe

### ❌ "Timeout: Tabela não carregou"
**Solução:** Sua internet pode estar lenta. Aumente o `TIMEOUT_MEDIO` para 30 ou 40.

---

## 📊 Estatísticas de Uso

Depois de terminar, você verá:

```
[***] Concluido! 98/100 baixadas
[i] Guias unicas processadas: 98

============================================================
CONCLUIDO!
Arquivos salvos em: C:\Users\SeuNome\Downloads
============================================================
```

Isso significa:
- ✅ 98 guias baixadas com sucesso
- ❌ 2 guias tiveram erro (podem estar já baixadas ou inacessíveis)
- 📁 Tudo salvo na pasta Downloads

---

## 🎓 Dicas de Uso

### 💡 **Melhor Horário**
Rode a automação fora do horário de pico (antes das 8h ou após 18h) para evitar lentidão do site.

### 💡 **Períodos Menores**
Em vez de buscar 1 mês inteiro, divida em períodos menores (1 semana) para mais estabilidade.

### 💡 **Mantenha o Chrome Aberto**
Não feche o Chrome durante a automação! Deixe minimizado se quiser.

### 💡 **Acompanhe os Logs**
Fique de olho no terminal. Se aparecer muitos erros seguidos, pare (Ctrl+C) e tente novamente.

---

## 🔒 Segurança

✅ **Seus dados estão seguros:**
- O script não envia nada para fora
- Usa sua sessão já logada do Chrome
- Não guarda senhas
- Todo o processamento é local

---

## 🤝 Contribuições

Este projeto nasceu da necessidade real de automatizar um trabalho repetitivo. Se você tiver sugestões de melhorias:

1. Teste a mudança
2. Documente o que fez
3. Compartilhe! 🚀

---

## 📞 Precisa de Ajuda?

Se encontrar problemas:
1. Verifique se seguiu todos os passos
2. Leia a seção "Solução de Problemas"
3. Verifique o arquivo `automacao_bradesco.log`
4. Teste com um período menor (1 dia) primeiro

---

## 🎉 Aproveite!

Agora você tem um assistente robótico que trabalha para você! 

Enquanto ele baixa as guias, você pode:
- ☕ Tomar um café
- 📧 Responder emails
- 🚶 Dar uma volta
- 😴 Ou só descansar!

**Tempo economizado = Qualidade de vida! 🌟**

---

## 📝 Notas da Versão

**Versão Atual: 2.0**

### ✨ Novidades:
- ✅ Busca por período com datas personalizadas
- ✅ Auto-recuperação quando o site perde guias
- ✅ Sistema anti-duplicação melhorado
- ✅ Logs mais detalhados e amigáveis
- ✅ Tratamento robusto de erros
- ✅ Download instantâneo e renomeação automática

### 🔧 Correções:
- 🐛 Corrigido problema de abas about:blank
- 🐛 Melhorado tratamento de erros internos do Bradesco
- 🐛 Corrigido loop infinito em caso de falha

---

**Desenvolvido com ❤️ para facilitar a vida de quem trabalha com guias médicas**

*Última atualização: Outubro 2024*