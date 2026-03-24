from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import logging
from pathlib import Path
import re
import hashlib
from datetime import datetime

# ========================== CONFIGURAÇÕES ==========================

# Pasta Downloads
PASTA_DOWNLOADS = Path.home() / "Downloads"

# Códigos a serem processados
CODIGOS = ["0000994402"]
#CODIGOS = ["0000938246"]

# Datas de busca (formato: DD/MM/AAAA)
DATA_INICIAL = "18/03/2026"
DATA_FINAL = "18/03/2026"

# Timeouts configuráveis
TIMEOUT_CURTO = 10
TIMEOUT_MEDIO = 20
TIMEOUT_LONGO = 40

# Controle de guias processadas
guias_por_paciente = {}
guias_processadas = set()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PASTA_DOWNLOADS / 'automacao_bradesco.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========================== EXCEÇÕES ==========================

class AutomacaoError(Exception):
    """Exceção base para erros de automação"""
    pass

class ElementoNaoEncontradoError(AutomacaoError):
    """Elemento não encontrado na página"""
    pass

# ========================== FUNÇÕES AUXILIARES ==========================

def limpar_nome_arquivo(nome):
    """Remove caracteres inválidos do nome do arquivo."""
    caracteres_invalidos = r'[<>:"/\\|?*]'
    nome_limpo = re.sub(caracteres_invalidos, '', nome)
    nome_limpo = ' '.join(nome_limpo.split())
    nome_limpo = nome_limpo[:100]
    return nome_limpo.strip() or "guia_sem_nome"


def aguardar_e_clicar(driver, by, value, timeout=TIMEOUT_MEDIO):
    """Aguarda elemento estar clicável e clica nele usando JavaScript."""
    try:
        elemento = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", elemento)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", elemento)
        return elemento
    except TimeoutException:
        raise ElementoNaoEncontradoError(f"Elemento nao encontrado: {by}={value}")


def verificar_e_tratar_erro_interno(driver, aba_trabalho):
    """
    Verifica se apareceu a página de Erro Interno do Bradesco e clica em Voltar.
    Returns: bool - True se encontrou e tratou erro, False caso contrário
    """
    try:
        # Verifica se está na URL de erro
        url_atual = driver.current_url
        if "erroAutenticacao" in url_atual or "ErroInterno" in url_atual:
            logger.warning("[!] Pagina de ERRO INTERNO detectada!")
            
            # Tenta clicar no botão Voltar
            try:
                botao_voltar = driver.find_element(By.XPATH, "//button[contains(@onclick, 'fnVoltar')]")
                if botao_voltar.is_displayed():
                    driver.execute_script("arguments[0].click();", botao_voltar)
                    logger.info("[OK] Botao 'Voltar' do erro clicado")
                    time.sleep(2)
                    
                    # Volta para aba de trabalho
                    driver.switch_to.window(aba_trabalho)
                    return True
            except NoSuchElementException:
                pass
        
        # Verifica se há texto "Erro Interno" na página
        try:
            erro_interno = driver.find_element(By.XPATH, "//*[contains(text(), 'Erro Interno')]")
            if erro_interno.is_displayed():
                logger.warning("[!] Texto 'Erro Interno' encontrado na pagina!")
                
                # Procura botão Voltar
                try:
                    botao_voltar = driver.find_element(By.XPATH, "//button[contains(@onclick, 'fnVoltar') or contains(text(), 'Voltar')]")
                    driver.execute_script("arguments[0].click();", botao_voltar)
                    logger.info("[OK] Botao 'Voltar' clicado")
                    time.sleep(2)
                    
                    driver.switch_to.window(aba_trabalho)
                    return True
                except NoSuchElementException:
                    logger.error("[X] Botao 'Voltar' nao encontrado")
        except NoSuchElementException:
            pass
        
        # Verifica mensagem específica de autenticação
        try:
            msg_erro = driver.find_element(By.XPATH, "//*[contains(text(), 'Falha de autenticação no filtro de usuário do sistema')]")
            if msg_erro.is_displayed():
                logger.warning("[!] Erro de autenticacao detectado!")
                
                # Clica em Voltar
                try:
                    botao_voltar = driver.find_element(By.XPATH, "//button[contains(text(), 'Voltar')]")
                    driver.execute_script("arguments[0].click();", botao_voltar)
                    logger.info("[OK] Botao 'Voltar' clicado")
                    time.sleep(2)
                    
                    driver.switch_to.window(aba_trabalho)
                    return True
                except:
                    pass
        except NoSuchElementException:
            pass
        
        return False
        
    except Exception as e:
        logger.debug(f"Erro ao verificar erro interno: {e}")
        return False

def verificar_e_fechar_modal_erro(driver):
    """Verifica e fecha modais de erro do Bradesco automaticamente."""
    try:
        seletores_modal = [
            "//button[contains(text(), 'Fechar')]",
            "//button[contains(text(), 'OK')]",
            "//button[contains(text(), 'Continuar')]",
            "//button[@class='close']",
            "//*[contains(@class, 'modal')]//button[@type='button']",
        ]
        
        for seletor in seletores_modal:
            try:
                botao_fechar = driver.find_element(By.XPATH, seletor)
                if botao_fechar.is_displayed():
                    try:
                        modal_parent = botao_fechar.find_element(By.XPATH, "./ancestor::div[contains(@class, 'modal') or contains(@class, 'dialog')][1]")
                        mensagem = modal_parent.text.strip()[:200]
                        logger.warning(f"[!] Modal de erro: {mensagem}")
                    except:
                        logger.warning(f"[!] Modal de erro detectado")
                    
                    driver.execute_script("arguments[0].click();", botao_fechar)
                    logger.info("[OK] Modal fechado automaticamente")
                    time.sleep(0.5)
                    return True
            except (NoSuchElementException, Exception):
                continue
        
        return False
        
    except Exception as e:
        logger.debug(f"Erro ao verificar modal: {e}")
        return False


def fechar_aba_about_blank(driver, aba_trabalho):
    """Fecha abas about:blank abertas pelo Chrome."""
    try:
        abas_atuais = driver.window_handles
        
        for aba in abas_atuais:
            if aba != aba_trabalho:
                try:
                    driver.switch_to.window(aba)
                    url_atual = driver.current_url
                    
                    if url_atual == "about:blank" or url_atual.startswith("about:"):
                        driver.close()
                        logger.info("   [i] Aba about:blank fechada")
                except Exception:
                    pass
        
        driver.switch_to.window(aba_trabalho)
        
    except Exception as e:
        logger.warning(f"Erro ao fechar abas: {e}")


def validar_formato_data(data):
    """Valida se a data está no formato DD/MM/AAAA."""
    if not data or len(data) != 10:
        return False
    
    try:
        partes = data.split('/')
        if len(partes) != 3:
            return False
        
        dia, mes, ano = partes
        if not (dia.isdigit() and mes.isdigit() and ano.isdigit()):
            return False
        
        dia, mes, ano = int(dia), int(mes), int(ano)
        
        if not (1 <= dia <= 31 and 1 <= mes <= 12 and 1900 <= ano <= 2100):
            return False
        
        return True
    except:
        return False


def gerar_id_unico_robusto(colunas, nome_beneficiario, indice):
    """
    Gera um ID único robusto usando hash de todos os campos disponíveis.
    
    Args:
        colunas: Lista de elementos td da linha
        nome_beneficiario: Nome do beneficiário
        indice: Índice da linha na tabela
    
    Returns:
        str: ID único com hash MD5
    """
    # Extrai TODOS os campos possíveis das colunas
    campos_id = []
    for idx in range(min(8, len(colunas))):
        try:
            texto = colunas[idx].text.strip()
            if texto and len(texto) > 0:
                campos_id.append(texto)
            else:
                campos_id.append(f"col{idx}_vazio")
        except:
            campos_id.append(f"col{idx}_erro")
    
    # Adiciona timestamp com microsegundos para garantir unicidade absoluta
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    
    # ID base com TODOS os campos + timestamp + índice
    id_base = "_".join(campos_id)
    id_completo = f"{id_base}_{indice}_{timestamp}"
    
    # Gera hash MD5 para evitar IDs muito longos
    id_hash = hashlib.md5(id_completo.encode('utf-8')).hexdigest()[:16]
    
    # Nome final: primeiros 20 chars do nome + hash
    nome_curto = nome_beneficiario[:20].strip()
    id_final = f"{nome_curto}_{id_hash}"
    
    return id_final, id_completo


# ========================== DOWNLOAD ==========================

def renomear_guia_sadt_imediato(nome_base, max_tentativas=20):
    """
    Renomeia GuiaSADT.pdf diretamente na pasta Downloads.
    O Chrome já baixou o arquivo instantaneamente.
    """
    # logger.info("   [.] Procurando GuiaSADT.pdf...")
    
    for tentativa in range(max_tentativas):
        try:
            arquivo_guia = PASTA_DOWNLOADS / "GuiaSADT.pdf"
            
            if arquivo_guia.exists():
                logger.info(f"   [OK] GuiaSADT.pdf encontrado! (tentativa {tentativa + 1})")
                time.sleep(0.2)
                
                # Valida PDF
                try:
                    with open(arquivo_guia, 'rb') as f:
                        header = f.read(4)
                        if not header.startswith(b'%PDF'):
                            logger.warning(f"   [!] Arquivo nao e PDF valido")
                            time.sleep(0.5)
                            continue
                except Exception as e:
                    logger.warning(f"   [!] Erro ao ler arquivo: {e}")
                    time.sleep(0.5)
                    continue
                
                # Controla numeração POR PACIENTE
                if nome_base not in guias_por_paciente:
                    guias_por_paciente[nome_base] = 0
                
                # Incrementa o contador deste paciente
                guias_por_paciente[nome_base] += 1
                numero_guia = guias_por_paciente[nome_base]
                
                # Nome final com numeração: NomePaciente_1.pdf, NomePaciente_2.pdf, etc
                nome_final = f"{nome_base}_{numero_guia}.pdf"
                destino = PASTA_DOWNLOADS / nome_final
                
                # PROTEÇÃO EXTRA: Se o arquivo já existir (não deveria), adiciona sufixo
                contador_extra = 1
                while destino.exists():
                    logger.warning(f"[!] Arquivo {nome_final} ja existe! Adicionando sufixo...")
                    nome_final = f"{nome_base}_{numero_guia}_v{contador_extra}.pdf"
                    destino = PASTA_DOWNLOADS / nome_final
                    contador_extra += 1
                
                #logger.info(f"   [.] Renomeando para: {nome_final}")
                
                # Renomeia (move na mesma pasta)
                for retry in range(5):
                    try:
                        arquivo_guia.rename(destino)
                        tamanho_kb = destino.stat().st_size / 1024
                        logger.info(f"   [OK] Renomeado com sucesso: {nome_final} ({tamanho_kb:.1f} KB)")
                        logger.info(f"   [i] Total de guias deste paciente: {numero_guia}")
                        return True
                    except PermissionError:
                        if retry < 4:
                            logger.info(f"   [.] Arquivo travado, retry {retry + 1}/5...")
                            time.sleep(0.5)
                        else:
                            logger.error(f"   [X] Nao foi possivel renomear (arquivo travado)")
                            return False
                    except Exception as e:
                        logger.error(f"   [X] Erro ao renomear: {e}")
                        return False
            
            time.sleep(0.5)
            
        except Exception as e:
            logger.debug(f"   Erro tentativa {tentativa + 1}: {e}")
            time.sleep(0.5)
    
    logger.warning(f"   [!] GuiaSADT.pdf nao encontrado apos {max_tentativas} tentativas")
    return False


# ========================== CHROME ==========================

def conectar_chrome_existente():
    """Conecta ao Chrome já aberto."""
    logger.info("[+] Conectando ao Chrome")

    try:
        chrome_options = Options()
        
        # ✅ SINTAXE CORRETA para Selenium 4+
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9223")
        
        # Configurações de download
        chrome_options.add_experimental_option('prefs', {
            "download.default_directory": str(PASTA_DOWNLOADS),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        })
        
        # Argumentos adicionais para estabilidade
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Configura download via CDP
        try:
            driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": str(PASTA_DOWNLOADS)
            })
            logger.info("[OK] Download automatico configurado")
        except Exception as e:
            logger.warning(f"[!] Aviso CDP: {e}")
        
        logger.info("[OK] Conectado com sucesso!")
        return driver
        
    except Exception as e:
        logger.error(f"[X] Erro ao conectar: {e}")
        logger.info("[i] Execute: chrome.exe --remote-debugging-port=9223")
        raise
    
def acessar_senha_web(driver):
    """Acessa Serviços > Senha Web."""
    # logger.info("\n >> Acessando Senha Web")
    
    if len(driver.window_handles) == 0:
        raise AutomacaoError("Chrome nao tem janelas abertas")
    
    driver.switch_to.window(driver.window_handles[0])
    
    url = "https://wwws.bradescosaude.com.br/PCBS-GerenciadorPortal/novaHomeSaudeReferenciado.do"
    driver.get(url)
    
    WebDriverWait(driver, TIMEOUT_LONGO).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    # logger.info("[OK] Pagina carregada")
    time.sleep(2)
    
    aguardar_e_clicar(driver, By.CSS_SELECTOR, "button.button_novo_menu.cortina-1")
    
    aguardar_e_clicar(driver, By.XPATH, "//div[@class='linha_novo_menu' and contains(text(), 'Senha Web')]")


def selecionar_codigo_e_continuar(driver, codigo):
    """Seleciona código e continua - VERSÃO ULTRA ROBUSTA."""
    # logger.info(f"\n>> Selecionando codigo {codigo}...")
    
    # Aguarda nova aba abrir
    WebDriverWait(driver, TIMEOUT_MEDIO).until(lambda d: len(d.window_handles) > 1)
    driver.switch_to.window(driver.window_handles[-1])
    
    # Aguarda página carregar completamente
    WebDriverWait(driver, TIMEOUT_MEDIO).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    # logger.info("   [.] Pagina carregada, aguardando interface...")
    
    # Aguarda o JavaScript de modernização decidir qual interface mostrar
    time.sleep(3)
    
    # FORÇA interface antiga (se existir sistema de modernização)
    
    # logger.info("   [.] Verificando e forcando interface antiga...")
    try:
        driver.execute_script("""
            try {
                if (typeof toggleStilos === 'function') {
                    toggleStilos(false);
                }
                $('#blocoFormularioOriginal').show();
                $('#modernizacaoContainer').hide();
                $('#modernizacaoIframe').hide();
            } catch(e) {
                console.log('Sem sistema de modernizacao ou ja na interface antiga');
            }
        """)
        time.sleep(1)
    except:
        pass
    
    # Localiza o select com múltiplas tentativas
    logger.info("   [.] Localizando select de codigo...")
    select_element = None
    
    for tentativa in range(3):
        try:
            select_element = WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.presence_of_element_located((By.ID, "comboReferenciado"))
            )
            
            # Verifica se está visível
            if not select_element.is_displayed():
                logger.warning(f"   [!] Select oculto (tentativa {tentativa + 1}/3), forcando display...")
                driver.execute_script("""
                    var select = document.getElementById('comboReferenciado');
                    if (select) {
                        select.style.display = 'block';
                        select.style.visibility = 'visible';
                        select.disabled = false;
                    }
                """)
                time.sleep(1)
            else:
                logger.info("   [OK] Select encontrado e visivel")
                break
                
        except Exception as e:
            logger.warning(f"   [!] Tentativa {tentativa + 1}/3 falhou: {e}")
            time.sleep(2)
    
    if not select_element:
        raise ElementoNaoEncontradoError("Select 'comboReferenciado' nao encontrado")
    
    # Scroll até o elemento
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", select_element)
    time.sleep(0.5)
    
    # === MÉTODO 1: JavaScript Puro (Mais Confiável) ===
    # logger.info(f"   [.] METODO 1: Selecionando via JavaScript")
    sucesso_js = False
    try:
        # Remove readonly/disabled se existir
        driver.execute_script("""
            var select = document.getElementById('comboReferenciado');
            select.removeAttribute('readonly');
            select.removeAttribute('disabled');
        """)
        
        # Seleciona o valor
        driver.execute_script(f"""
            var select = document.getElementById('comboReferenciado');
            select.value = '{codigo}';
            
            // Dispara TODOS os eventos possíveis
            var events = ['change', 'input', 'blur'];
            events.forEach(function(eventType) {{
                var event = new Event(eventType, {{ bubbles: true, cancelable: true }});
                select.dispatchEvent(event);
            }});
        """)
        time.sleep(0.5)
        
        # Verifica se selecionou
        valor_selecionado = driver.execute_script("return document.getElementById('comboReferenciado').value;")
        if valor_selecionado == codigo:
            # logger.info(f"   [OK] Codigo {codigo} selecionado")
            sucesso_js = True
        else:
            logger.warning(f"   [!] METODO 1 falhou. Valor: '{valor_selecionado}' != '{codigo}'")
    except Exception as e:
        logger.warning(f"   [!] METODO 1 exception: {e}")
    
    # # === MÉTODO 2: jQuery (Fallback 1) ===
    # if not sucesso_js:
    #     logger.info(f"   [.] METODO 2: Tentando via jQuery...")
    #     try:
    #         driver.execute_script(f"""
    #             $('#comboReferenciado').val('{codigo}').trigger('change').trigger('blur');
    #         """)
    #         time.sleep(0.5)
            
    #         valor_selecionado = driver.execute_script("return $('#comboReferenciado').val();")
    #         if valor_selecionado == codigo:
    #             logger.info(f"   [OK] METODO 2 funcionou! Codigo {codigo} selecionado")
    #             sucesso_js = True
    #         else:
    #             logger.warning(f"   [!] METODO 2 falhou. Valor: '{valor_selecionado}' != '{codigo}'")
    #     except Exception as e:
    #         logger.warning(f"   [!] METODO 2 exception: {e}")
    
    # # === MÉTODO 3: Selenium Select (Fallback 2) ===
    # if not sucesso_js:
    #     logger.info(f"   [.] METODO 3: Tentando via Selenium Select...")
    #     try:
    #         select_obj = Select(select_element)
    #         select_obj.select_by_value(codigo)
    #         time.sleep(0.5)
            
    #         valor_selecionado = select_obj.first_selected_option.get_attribute('value')
    #         if valor_selecionado == codigo:
    #             logger.info(f"   [OK] METODO 3! Codigo {codigo} selecionado")
    #             sucesso_js = True
    #         else:
    #             logger.warning(f"   [!] METODO 3 falhou. Valor: '{valor_selecionado}' != '{codigo}'")
    #     except Exception as e:
    #         logger.warning(f"   [!] METODO 3 exception: {e}")
    
    # # === MÉTODO 4: Click na option específica (Fallback 3) ===
    # if not sucesso_js:
    #     logger.info(f"   [.] METODO 4: Tentando clicar na option diretamente...")
    #     try:
    #         option_element = driver.find_element(By.XPATH, f"//option[@value='{codigo}']")
    #         driver.execute_script("arguments[0].selected = true;", option_element)
    #         driver.execute_script("""
    #             var select = document.getElementById('comboReferenciado');
    #             var event = new Event('change', {bubbles: true});
    #             select.dispatchEvent(event);
    #         """)
    #         time.sleep(0.5)
            
    #         valor_selecionado = driver.execute_script("return document.getElementById('comboReferenciado').value;")
    #         if valor_selecionado == codigo:
    #             logger.info(f"   [OK] METODO 4! Codigo {codigo} selecionado")
    #             sucesso_js = True
    #         else:
    #             logger.warning(f"   [!] METODO 4 falhou. Valor: '{valor_selecionado}' != '{codigo}'")
    #     except Exception as e:
    #         logger.warning(f"   [!] METODO 4 exception: {e}")
    
    # # Verificação final
    # if not sucesso_js:
    #     logger.error("[X] TODOS OS METODOS FALHARAM!")
    #     raise AutomacaoError(f"Impossivel selecionar codigo {codigo} - Todos os metodos falharam")
    
    # Debug: Mostra todas as options disponíveis
    # try:
    #     options = driver.execute_script("""
    #         var select = document.getElementById('comboReferenciado');
    #         var options = [];
    #         for (var i = 0; i < select.options.length; i++) {
    #             options.push(select.options[i].value + ': ' + select.options[i].text);
    #         }
    #         return options;
    #     """)
    #     logger.info(f"   [DEBUG] Options disponiveis: {options}")
    # except:
    #     pass
    
    time.sleep(1)
    
    # Clica no botão Continuar
#    logger.info("   [.] Clicando em 'Continuar'...")
    aguardar_e_clicar(driver, By.XPATH, "//button[contains(., 'Continuar')]")
#    logger.info("[OK] Botao 'Continuar' clicado")
    time.sleep(2)


def nova_consulta(driver, data_inicial, data_final):
    """Etapa 3: Clica em 'Nova Consulta' e faz a busca das guias."""
#    logger.info(f"\n[>>] ETAPA 3: Realizando nova consulta ({data_inicial} ate {data_final})...")
    
    # Aguarda estar na aba correta
    WebDriverWait(driver, TIMEOUT_MEDIO).until(lambda d: len(d.window_handles) >= 1)
    driver.switch_to.window(driver.window_handles[-1])
    
    try:
        # Aguarda e clica em "Nova Consulta"
        nova_consulta_btn = WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.element_to_be_clickable((By.XPATH, "//img[@alt='Nova Consulta' or @title='Nova Consulta']"))
        )
        driver.execute_script("arguments[0].click();", nova_consulta_btn)
#        logger.info("[OK] 'Nova Consulta' clicado")
        time.sleep(1)
        
        # Aguarda campos de data estarem disponíveis
        campo_data_inicio = WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located((By.ID, "periodoDe"))
        )
        driver.execute_script("arguments[0].value = '';", campo_data_inicio)
        driver.execute_script("arguments[0].value = arguments[1];", campo_data_inicio, data_inicial)
        logger.info(f"[OK] Data inicial: {data_inicial}")

        campo_data_fim = WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located((By.ID, "periodoAte"))
        )
        driver.execute_script("arguments[0].value = '';", campo_data_fim)
        driver.execute_script("arguments[0].value = arguments[1];", campo_data_fim, data_final)
        logger.info(f"[OK] Data final: {data_final}")
        
        # Aguarda e clica em "Consultar"
        consultar_btn = WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Consultar')]"))
        )
        driver.execute_script("arguments[0].click();", consultar_btn)
        # logger.info("[OK] Botao 'Consultar' clicado")

        # Aguarda indicador de carregamento aparecer e depois desaparecer
        loading_xpath = "//*[contains(@class, 'loading') or contains(@class, 'spinner') or contains(@class, 'loader')]"
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, loading_xpath))
            )
            logger.info("   [.] Detectado indicador de carregamento, aguardando...")
            WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.invisibility_of_element_located((By.XPATH, loading_xpath))
            )
        except TimeoutException:
            pass  # Indicador nao apareceu, continua direto para verificar tabela
        
        # Aguarda a tabela de resultados carregar
        try:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(
                EC.presence_of_element_located((By.XPATH, "//tr[@class='even' or @class='odd']"))
            )
            # logger.info("[OK] Resultados carregados")
        except TimeoutException:
            logger.warning("[!] Tabela nao encontrada, verificando iframe...")
            # Verifica se há um iframe
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                logger.info(f"   [i] Encontrado(s) {len(iframes)} iframe(s), tentando mudar para o primeiro...")
                driver.switch_to.frame(iframes[0])
                try:
                    WebDriverWait(driver, TIMEOUT_MEDIO).until(
                        EC.presence_of_element_located((By.XPATH, "//tr[@class='even' or @class='odd']"))
                    )
                    logger.info("[OK] Resultados encontrados dentro do iframe")
                except TimeoutException:
                    driver.switch_to.default_content()
                    logger.error("[X] Tabela nao encontrada nem no iframe")
                    logger.info(f"URL atual: {driver.current_url}")
                    raise
            else:
                logger.error("[X] Nenhum iframe encontrado e tabela nao carregou")
                logger.info(f"URL atual: {driver.current_url}")
                raise
        
    except (TimeoutException, NoSuchElementException) as e:
        logger.error(f"[X] Erro na consulta: {e}")
        raise


# ========================== PROCESSAMENTO ==========================

def processar_guia(driver, linha, indice, total, aba_trabalho):
    """Processa uma única guia com ID único robusto."""
    try:
        colunas = linha.find_elements(By.TAG_NAME, "td")
        
        # DEBUG: Mostra conteúdo das colunas
        # logger.info(f"\n[DEBUG] Linha {indice + 1} - Conteudo das colunas:")
        # for idx, col in enumerate(colunas[:8]):
        #     try:
        #         texto = col.text.strip()[:50]
        #         logger.info(f"   Coluna {idx}: '{texto}'")
        #     except:
        #         logger.info(f"   Coluna {idx}: [erro]")
        
        # VERIFICA SE A LINHA ESTÁ VAZIA (todas as colunas vazias)
        todas_vazias = True
        for col in colunas[:8]:
            try:
                if col.text.strip():
                    todas_vazias = False
                    break
            except:
                pass
        
        if todas_vazias:
            logger.warning(f"\n[{indice + 1}/{total}] *** PULANDO (LINHA VAZIA) ***")
            return True
        
        # Extrai nome (coluna 4)
        nome_beneficiario = "DESCONHECIDO"
        try:
            nome_beneficiario = colunas[4].text.strip()
            logger.info(f"   [DEBUG] Nome coluna 4: '{nome_beneficiario}'")
            
            if not nome_beneficiario or len(nome_beneficiario) < 3:
                logger.warning(f"   [!] Nome invalido, tentando outras colunas...")
                for idx in [3, 5, 6, 7]:
                    try:
                        nome_temp = colunas[idx].text.strip()
                        if nome_temp and len(nome_temp) > 3:
                            nome_beneficiario = nome_temp
                            logger.info(f"   [OK] Nome na coluna {idx}: {nome_beneficiario}")
                            break
                    except:
                        continue
        except Exception as e:
            logger.warning(f"   [!] Erro ao extrair nome: {e}")
        
        if not nome_beneficiario or len(nome_beneficiario) < 3:
            logger.warning(f"\n[{indice + 1}/{total}] *** PULANDO (SEM NOME VALIDO) ***")
            return True
        
        # ============================================
        # GERAÇÃO DE ID ÚNICO ROBUSTO (SOLUÇÃO 2)
        # ============================================
        id_final, id_completo = gerar_id_unico_robusto(colunas, nome_beneficiario, indice)
        
        # logger.info(f"   [DEBUG] ID único gerado: {id_final}")
        # logger.info(f"   [DEBUG] ID completo (primeiros 100 chars): {id_completo[:100]}...")
        
        # Verifica duplicação
        if id_final in guias_processadas:
            logger.warning(f"\n[{indice + 1}/{total}] *** PULANDO (JA PROCESSADA) ***")
            logger.info(f"   [i] ID duplicado: {id_final}")
            return True
        
        # Adiciona ao set de processadas
        guias_processadas.add(id_final)
        # logger.info(f"   [DEBUG] Guia adicionada ao set. Total processadas: {len(guias_processadas)}")
        
        nome_arquivo = limpar_nome_arquivo(nome_beneficiario)
        logger.info(f"\n{'='*60}")
        logger.info(f"[{indice + 1}/{total}] PROCESSANDO: {nome_beneficiario}")
        logger.info(f"   Arquivo: {nome_arquivo}")
        logger.info(f"   ID: {id_final}")
        logger.info(f"{'='*60}")
        
        verificar_e_fechar_modal_erro(driver)
        
        # Seleciona linha
        try:
            radio = colunas[0].find_element(By.CSS_SELECTOR, "input[type='radio'][name='codigoSolicitacao']")
        except:
            radio = linha.find_element(By.TAG_NAME, "input")
        
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", radio)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", radio)
#        logger.info("   [OK] Linha selecionada")
        time.sleep(0.5)
        
        verificar_e_fechar_modal_erro(driver)
        verificar_e_tratar_erro_interno(driver, aba_trabalho)
        
        # Clica Informações do Beneficiário
        aguardar_e_clicar(driver, By.CSS_SELECTOR, "img.btn_info_contrato[alt='Informações do Beneficiário']")
#        logger.info("   [i] 'Informacoes do Beneficiario' clicado")
        time.sleep(0.5)
        
        verificar_e_fechar_modal_erro(driver)
        verificar_e_tratar_erro_interno(driver, aba_trabalho)
        
        # Clica PDF (download INSTANTÂNEO)
        aguardar_e_clicar(driver, By.XPATH, "//button[contains(@onclick, 'carregarPDFtiss')]")
#        logger.info("   [i] Botao 'PDF' clicado - download INSTANTANEO")
        
        # Verifica erro antes de tentar download
        if verificar_e_tratar_erro_interno(driver, aba_trabalho):
            logger.warning("   [!] Erro interno apos clicar PDF, tentando novamente...")
            time.sleep(2)
            aguardar_e_clicar(driver, By.XPATH, "//button[contains(@onclick, 'carregarPDFtiss')]")
            logger.info("   [i] Tentativa 2: Botao 'PDF' clicado")
        
        # Renomeia IMEDIATAMENTE
        sucesso = renomear_guia_sadt_imediato(nome_arquivo)
        
        if not sucesso:
            logger.warning(f"   [X] Falha ao baixar PDF")
        else:
            logger.info(f"   [***] Guia salva com sucesso!")
        
        # Fecha about:blank
        time.sleep(0.5)
        fechar_aba_about_blank(driver, aba_trabalho)
        
        driver.switch_to.window(aba_trabalho)
        verificar_e_fechar_modal_erro(driver)
        verificar_e_tratar_erro_interno(driver, aba_trabalho)
        
        # Volta à tabela
        try:
            aguardar_e_clicar(driver, By.XPATH, "//button[contains(@onclick, 'fnVoltar')]", timeout=TIMEOUT_CURTO)
#            logger.info("   [<-] Voltou a tabela")
            time.sleep(1)
            
            verificar_e_fechar_modal_erro(driver)
            verificar_e_tratar_erro_interno(driver, aba_trabalho)
            
            WebDriverWait(driver, TIMEOUT_CURTO).until(
                EC.presence_of_element_located((By.XPATH, "//tr[@class='even' or @class='odd']"))
            )
        except Exception as e:
            logger.warning(f"   [!] Erro ao voltar: {e}")
            verificar_e_fechar_modal_erro(driver)
            verificar_e_tratar_erro_interno(driver, aba_trabalho)
        
        time.sleep(0.5)
        return True
        
    except Exception as e:
        logger.error(f"   [X] Erro: {type(e).__name__}: {str(e)}")
        try:
            verificar_e_fechar_modal_erro(driver)
            fechar_aba_about_blank(driver, aba_trabalho)
        except:
            pass
        return False


def verificar_e_recarregar_tabela(driver, total_esperado, data_inicial, data_final, aba_trabalho):
    """
    Verifica se o número de guias na tabela corresponde ao esperado.
    Se não corresponder, executa nova consulta.
    
    Returns: bool - True se tabela está OK ou foi recarregada com sucesso
    """
    try:
        driver.switch_to.window(aba_trabalho)
        
        # Conta guias atuais
        guias_atuais = driver.find_elements(
            By.XPATH,
            "//tr[(@class='even' or @class='odd') and td[contains(., 'Liberada')]]"
        )
        total_atual = len(guias_atuais)
        
        logger.info(f"[i] Verificacao: {total_atual}/{total_esperado} guias na tabela")
        
        # Se o número de guias mudou, recarrega
        if total_atual != total_esperado:
            logger.warning(f"[!] ALERTA: Numero de guias mudou! Esperado: {total_esperado}, Atual: {total_atual}")
            logger.info("[>>] Recarregando tabela com Nova Consulta...")
            
            # Executa nova consulta
            nova_consulta(driver, data_inicial, data_final)
            time.sleep(2)
            
            # Verifica se recarregou corretamente
            guias_recarregadas = driver.find_elements(
                By.XPATH,
                "//tr[(@class='even' or @class='odd') and td[contains(., 'Liberada')]]"
            )
            total_recarregado = len(guias_recarregadas)
            
            if total_recarregado == total_esperado:
                logger.info(f"[OK] Tabela recarregada com sucesso! {total_recarregado} guias")
                return True
            else:
                logger.warning(f"[!] Apos recarregar: {total_recarregado} guias (esperado: {total_esperado})")
                return True
        
        return True
        
    except Exception as e:
        logger.error(f"[X] Erro ao verificar tabela: {e}")
        return False


def carregar_todas_as_guias(driver):
    """Clica em 'Mais+' repetidamente até carregar todas as guias da tabela."""
    cliques = 0
    while True:
        try:
            btn_mais = WebDriverWait(driver, TIMEOUT_CURTO).until(
                EC.element_to_be_clickable((By.ID, "btnConsultarMais100A"))
            )
            total_antes = len(driver.find_elements(
                By.XPATH, "//tr[@class='even' or @class='odd']"
            ))
            driver.execute_script("arguments[0].click();", btn_mais)
            cliques += 1
            logger.info(f"[>>] Carregando mais guias... (clique {cliques})")

            # Aguarda novas linhas aparecerem
            WebDriverWait(driver, TIMEOUT_MEDIO).until(
                lambda d: len(d.find_elements(
                    By.XPATH, "//tr[@class='even' or @class='odd']"
                )) > total_antes
            )
        except TimeoutException:
            break

    total_final = len(driver.find_elements(
        By.XPATH, "//tr[@class='even' or @class='odd']"
    ))
    if cliques > 0:
        logger.info(f"[OK] Total de guias carregadas: {total_final} ({cliques} clique(s) em 'Mais+')")


def processar_guias_liberadas(driver, codigo, data_inicial, data_final):
    """Processa guias com status 'Liberada'."""
    logger.info("\n[>>] ETAPA 4: Processando guias 'Liberada'...")

    global guias_por_paciente, guias_processadas
    guias_por_paciente = {}
    guias_processadas = set()

    aba_trabalho = driver.window_handles[-1]
    driver.switch_to.window(aba_trabalho)

    verificar_e_fechar_modal_erro(driver)

    # Busca guias
    try:
        WebDriverWait(driver, TIMEOUT_CURTO).until(
            EC.presence_of_element_located((By.XPATH, "//tr[@class='even' or @class='odd']"))
        )
    except TimeoutException:
        logger.error("[X] Tabela nao encontrada")
        return

    # Carrega todas as páginas antes de processar
    carregar_todas_as_guias(driver)

    guias = driver.find_elements(
        By.XPATH,
        "//tr[(@class='even' or @class='odd') and td[contains(., 'Liberada')]]"
    )
    total_inicial = len(guias)
    
    if total_inicial == 0:
        logger.warning("[!] Nenhuma guia 'Liberada' encontrada")
        return
    
    logger.info(f"[i] {total_inicial} guia(s) 'Liberada' encontrada(s)")
    
    sucessos = 0
    tentativas_recarregar = 0
    max_tentativas_recarregar = 3
    
    i = 0
    while i < total_inicial:
        driver.switch_to.window(aba_trabalho)
        verificar_e_fechar_modal_erro(driver)
        
        # VERIFICAÇÃO: Antes de processar cada guia, verifica se a tabela está completa
        try:
            guias_atualizadas = driver.find_elements(
                By.XPATH,
                "//tr[(@class='even' or @class='odd') and td[contains(., 'Liberada')]]"
            )
            total_atual = len(guias_atualizadas)
            
            # Se o número de guias mudou, recarrega a tabela
            if total_atual != total_inicial:
                logger.warning(f"\n[!] INCONSISTENCIA DETECTADA!")
                logger.warning(f"    Esperado: {total_inicial} guias | Encontrado: {total_atual} guias")
                
                if tentativas_recarregar < max_tentativas_recarregar:
                    tentativas_recarregar += 1
                    logger.info(f"[>>] Tentativa {tentativas_recarregar}/{max_tentativas_recarregar}: Recarregando tabela...")
                    
                    if verificar_e_recarregar_tabela(driver, total_inicial, data_inicial, data_final, aba_trabalho):
                        logger.info("[OK] Tabela recarregada! Continuando do indice atual...")
                        tentativas_recarregar = 0
                        continue
                    else:
                        logger.error("[X] Falha ao recarregar tabela")
                        i += 1
                        continue
                else:
                    logger.error(f"[X] Limite de tentativas atingido. Pulando guia {i+1}")
                    tentativas_recarregar = 0
                    i += 1
                    continue
            
            # Verifica se o índice ainda é válido
            if i >= len(guias_atualizadas):
                logger.warning(f"   [!] Guia {i+1} nao encontrada no indice")
                i += 1
                continue
            
            linha = guias_atualizadas[i]
            
            if processar_guia(driver, linha, i, total_inicial, aba_trabalho):
                sucessos += 1
            
            time.sleep(1)
            i += 1
                
        except StaleElementReferenceException:
            logger.warning(f"   [!] Guia {i+1} stale, recarregando tabela...")
            if verificar_e_recarregar_tabela(driver, total_inicial, data_inicial, data_final, aba_trabalho):
                continue
            else:
                i += 1
                continue
        except Exception as e:
            logger.error(f"   [X] Erro na guia {i+1}: {e}")
            i += 1
            continue
    
    logger.info(f"\n[***] Concluido! {sucessos}/{total_inicial} baixadas")
    logger.info(f"[i] Guias unicas processadas: {len(guias_processadas)}")

# ========================== MAIN ==========================

def main():
    """Função principal."""
    print("=" * 60)
    print("AUTOMACAO BRADESCO SAUDE - DOWNLOAD DE GUIAS")
    print("=" * 60)
    
    # Usa as datas configuradas no início do código
    data_inicial = DATA_INICIAL
    data_final = DATA_FINAL
    
    # Validação de formato
    if not validar_formato_data(data_inicial) or not validar_formato_data(data_final):
        print("[X] Formato de data invalido nas configuracoes! Use DD/MM/AAAA")
        input("\nENTER para finalizar...")
        return
    
    logger.info(f"Periodo configurado: {data_inicial} ate {data_final}")
    
    driver = None
    try:
        driver = conectar_chrome_existente()
        acessar_senha_web(driver)
        
        for codigo in CODIGOS:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"[#] Codigo: {codigo}")
            logger.info(f"{'=' * 60}")
            
            selecionar_codigo_e_continuar(driver, codigo)
            nova_consulta(driver, data_inicial, data_final)
            processar_guias_liberadas(driver, codigo, data_inicial, data_final)
        
        print("\n" + "=" * 60)
        print("CONCLUIDO!")
        print(f"Arquivos salvos em: {PASTA_DOWNLOADS}")
        print("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("\n[!] Interrompido pelo usuario")
    except Exception as e:
        logger.error(f"\n[X] ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nENTER para finalizar...")

if __name__ == "__main__":
    main()