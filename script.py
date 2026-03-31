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

PASTA_DOWNLOADS = Path.home() / "Downloads"

CODIGOS = ["0000994402"]

DATA_INICIAL = "19/02/2026"
DATA_FINAL = "19/02/2026"

# Timeouts reduzidos para maior agilidade
TIMEOUT_CURTO = 7
TIMEOUT_MEDIO = 15
TIMEOUT_LONGO = 25

# Sleeps configuráveis (centralizados para fácil ajuste)
SLEEP_MINIMO = 0.1
SLEEP_CURTO = 0.2
SLEEP_MEDIO = 0.5
SLEEP_LONGO = 1.0

# Controle de guias processadas
guias_por_paciente = {}
guias_processadas = set()

# Logging
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
    pass

class ElementoNaoEncontradoError(AutomacaoError):
    pass

# ========================== FUNÇÕES AUXILIARES ==========================

def limpar_nome_arquivo(nome):
    nome_limpo = re.sub(r'[<>:"/\\|?*]', '', nome)
    nome_limpo = ' '.join(nome_limpo.split())
    return (nome_limpo[:100].strip()) or "guia_sem_nome"


def aguardar_e_clicar(driver, by, value, timeout=None):
    if timeout is None:
        timeout = TIMEOUT_MEDIO
    try:
        elemento = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elemento)
        driver.execute_script("arguments[0].click();", elemento)
        return elemento
    except TimeoutException:
        raise ElementoNaoEncontradoError(f"Elemento nao encontrado: {by}={value}")


def verificar_saude_pagina(driver, aba_trabalho):
    """Verificação unificada de erros (interno + modais)."""
    try:
        url_atual = driver.current_url
        if "erroAutenticacao" in url_atual or "ErroInterno" in url_atual:
            logger.warning("Erro interno detectado na URL")
            try:
                botao = driver.find_element(By.XPATH,
                    "//button[contains(@onclick,'fnVoltar') or contains(text(),'Voltar')]")
                if botao.is_displayed():
                    driver.execute_script("arguments[0].click();", botao)
                    time.sleep(SLEEP_LONGO)
                    driver.switch_to.window(aba_trabalho)
                    return True
            except NoSuchElementException:
                pass

        for texto_erro in ['Erro Interno', 'Falha de autenticação no filtro']:
            try:
                elem = driver.find_element(By.XPATH, f"//*[contains(text(), '{texto_erro}')]")
                if elem.is_displayed():
                    logger.warning(f"Erro: '{texto_erro}'")
                    try:
                        botao = driver.find_element(By.XPATH,
                            "//button[contains(@onclick,'fnVoltar') or contains(text(),'Voltar')]")
                        driver.execute_script("arguments[0].click();", botao)
                        time.sleep(SLEEP_LONGO)
                        driver.switch_to.window(aba_trabalho)
                        return True
                    except NoSuchElementException:
                        pass
            except NoSuchElementException:
                continue

        for seletor in [
            "//button[contains(text(),'Fechar')]",
            "//button[contains(text(),'OK')]",
            "//button[contains(text(),'Continuar')]",
            "//button[@class='close']",
        ]:
            try:
                botao = driver.find_element(By.XPATH, seletor)
                if botao.is_displayed():
                    logger.warning("Modal de erro fechado")
                    driver.execute_script("arguments[0].click();", botao)
                    time.sleep(SLEEP_CURTO)
                    return True
            except NoSuchElementException:
                continue

        return False
    except Exception:
        return False


def fechar_aba_about_blank(driver, aba_trabalho):
    try:
        for aba in driver.window_handles:
            if aba != aba_trabalho:
                try:
                    driver.switch_to.window(aba)
                    if driver.current_url.startswith("about:"):
                        driver.close()
                except Exception:
                    pass
        driver.switch_to.window(aba_trabalho)
    except Exception:
        pass


def validar_formato_data(data):
    if not data or len(data) != 10:
        return False
    try:
        partes = data.split('/')
        if len(partes) != 3:
            return False
        dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
        return 1 <= dia <= 31 and 1 <= mes <= 12 and 1900 <= ano <= 2100
    except:
        return False


def gerar_id_unico_robusto(colunas, nome_beneficiario, indice):
    campos_id = []
    for idx in range(min(8, len(colunas))):
        try:
            texto = colunas[idx].text.strip()
            campos_id.append(texto if texto else f"col{idx}_vazio")
        except:
            campos_id.append(f"col{idx}_erro")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    id_completo = f"{'_'.join(campos_id)}_{indice}_{timestamp}"
    id_hash = hashlib.md5(id_completo.encode('utf-8')).hexdigest()[:16]
    id_final = f"{nome_beneficiario[:20].strip()}_{id_hash}"
    return id_final, id_completo


def _extrair_nome(colunas, linha=None):
    """Extrai nome do beneficiário. Tenta colunas primeiro, depois onclick do radio."""
    # Método 1: Texto das colunas
    for idx in [4, 3, 5, 6, 7]:
        try:
            nome = colunas[idx].text.strip()
            if nome and len(nome) > 3:
                return nome
        except:
            continue

    # Método 2: Extrair do atributo onclick do radio (mais confiável)
    try:
        radio = (linha or colunas[0]).find_element(By.CSS_SELECTOR, "input[type='radio']")
        onclick = radio.get_attribute("onclick") or ""
        match = re.search(r"nomeSegurado=([^&]+)", onclick)
        if match:
            nome = match.group(1).strip()
            if nome and len(nome) > 3:
                return nome
    except:
        pass

    return "DESCONHECIDO"


# ========================== DOWNLOAD ==========================

def renomear_guia_sadt_imediato(nome_base, max_tentativas=30):
    arquivo_guia = PASTA_DOWNLOADS / "GuiaSADT.pdf"

    for tentativa in range(max_tentativas):
        try:
            if arquivo_guia.exists() and arquivo_guia.stat().st_size > 100:
                try:
                    with open(arquivo_guia, 'rb') as f:
                        if not f.read(4).startswith(b'%PDF'):
                            time.sleep(SLEEP_MINIMO)
                            continue
                except (PermissionError, IOError):
                    time.sleep(SLEEP_MINIMO)
                    continue

                if nome_base not in guias_por_paciente:
                    guias_por_paciente[nome_base] = 0
                guias_por_paciente[nome_base] += 1
                numero_guia = guias_por_paciente[nome_base]

                nome_final = f"{nome_base}_{numero_guia}.pdf"
                destino = PASTA_DOWNLOADS / nome_final

                contador_extra = 1
                while destino.exists():
                    nome_final = f"{nome_base}_{numero_guia}_v{contador_extra}.pdf"
                    destino = PASTA_DOWNLOADS / nome_final
                    contador_extra += 1

                for retry in range(5):
                    try:
                        arquivo_guia.rename(destino)
                        tamanho_kb = destino.stat().st_size / 1024
                        return True, nome_final, tamanho_kb, numero_guia
                    except PermissionError:
                        time.sleep(SLEEP_CURTO)
                    except Exception as e:
                        logger.error(f"Erro ao renomear: {e}")
                        return False, None, 0, 0

                return False, None, 0, 0

            time.sleep(0.15)
        except Exception:
            time.sleep(0.15)

    return False, None, 0, 0


# ========================== CHROME ==========================

def conectar_chrome_existente():
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9223")
        chrome_options.add_experimental_option('prefs', {
            "download.default_directory": str(PASTA_DOWNLOADS),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        })
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=chrome_options)

        try:
            driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": str(PASTA_DOWNLOADS)
            })
        except Exception:
            pass

        logger.info("Chrome conectado")
        return driver
    except Exception as e:
        logger.error(f"Falha ao conectar: {e}")
        logger.error("Execute: chrome.exe --remote-debugging-port=9223")
        raise


def acessar_senha_web(driver):
    if len(driver.window_handles) == 0:
        raise AutomacaoError("Chrome nao tem janelas abertas")

    driver.switch_to.window(driver.window_handles[0])
    driver.get("https://wwws.bradescosaude.com.br/PCBS-GerenciadorPortal/novaHomeSaudeReferenciado.do")

    WebDriverWait(driver, TIMEOUT_LONGO).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    aguardar_e_clicar(driver, By.CSS_SELECTOR, "button.button_novo_menu.cortina-1")
    aguardar_e_clicar(driver, By.XPATH, "//div[@class='linha_novo_menu' and contains(text(), 'Senha Web')]")
    logger.info("Senha Web acessada")


def selecionar_codigo_e_continuar(driver, codigo):

    WebDriverWait(driver, TIMEOUT_MEDIO).until(lambda d: len(d.window_handles) > 1)
    driver.switch_to.window(driver.window_handles[-1])
    WebDriverWait(driver, TIMEOUT_MEDIO).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

    try:
        driver.execute_script("""
            try {
                if (typeof toggleStilos === 'function') toggleStilos(false);
                $('#blocoFormularioOriginal').show();
                $('#modernizacaoContainer, #modernizacaoIframe').hide();
            } catch(e) {}
        """)
    except:
        pass

    select_element = WebDriverWait(driver, TIMEOUT_MEDIO).until(
        EC.presence_of_element_located((By.ID, "comboReferenciado"))
    )

    if not select_element.is_displayed():
        driver.execute_script("""
            var s = document.getElementById('comboReferenciado');
            if(s){s.style.display='block';s.style.visibility='visible';s.disabled=false;}
        """)

    # JS puro
    sucesso = driver.execute_script(f"""
        var s = document.getElementById('comboReferenciado');
        s.removeAttribute('readonly'); s.removeAttribute('disabled');
        s.value = '{codigo}';
        ['change','input','blur'].forEach(function(t){{
            s.dispatchEvent(new Event(t, {{bubbles:true, cancelable:true}}));
        }});
        return s.value === '{codigo}';
    """)

    # Fallback jQuery
    if not sucesso:
        try:
            sucesso = driver.execute_script(f"""
                $('#comboReferenciado').val('{codigo}').trigger('change').trigger('blur');
                return $('#comboReferenciado').val() === '{codigo}';
            """)
        except:
            pass

    # Fallback Selenium
    if not sucesso:
        try:
            Select(select_element).select_by_value(codigo)
            sucesso = True
        except:
            pass

    if not sucesso:
        raise AutomacaoError(f"Impossivel selecionar codigo {codigo}")

    logger.info(f"Codigo {codigo} selecionado")
    aguardar_e_clicar(driver, By.XPATH, "//button[contains(., 'Continuar')]")

    WebDriverWait(driver, TIMEOUT_MEDIO).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def nova_consulta(driver, data_inicial, data_final):
    logger.info(f"Consultando {data_inicial} a {data_final}...")

    driver.switch_to.window(driver.window_handles[-1])

    nova_btn = WebDriverWait(driver, TIMEOUT_MEDIO).until(
        EC.element_to_be_clickable((By.XPATH, "//img[@alt='Nova Consulta' or @title='Nova Consulta']"))
    )
    driver.execute_script("arguments[0].click();", nova_btn)

    # Preenche datas via JS (campos podem estar ocultos pela modernização)
    WebDriverWait(driver, TIMEOUT_MEDIO).until(
        EC.presence_of_element_located((By.ID, "periodoDe"))
    )
    driver.execute_script(f"""
        var de = document.getElementById('periodoDe');
        var ate = document.getElementById('periodoAte');
        [de, ate].forEach(function(el) {{
            el.removeAttribute('readonly');
            el.removeAttribute('disabled');
            el.style.display = 'block';
            el.style.visibility = 'visible';
        }});
        de.value = '{data_inicial}';
        ate.value = '{data_final}';
        ['change','input','blur'].forEach(function(t) {{
            de.dispatchEvent(new Event(t, {{bubbles:true}}));
            ate.dispatchEvent(new Event(t, {{bubbles:true}}));
        }});
    """)

    consultar_btn = WebDriverWait(driver, TIMEOUT_MEDIO).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Consultar')]"))
    )
    driver.execute_script("arguments[0].click();", consultar_btn)

    try:
        loading = driver.find_elements(By.XPATH,
            "//*[contains(@class,'loading') or contains(@class,'spinner') or contains(@class,'loader')]")
        if loading:
            WebDriverWait(driver, TIMEOUT_MEDIO).until(EC.invisibility_of_element(loading[0]))
    except:
        pass

    try:
        WebDriverWait(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located((By.XPATH, "//tr[@class='even' or @class='odd']"))
        )
    except TimeoutException:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            driver.switch_to.frame(iframes[0])
            try:
                WebDriverWait(driver, TIMEOUT_MEDIO).until(
                    EC.presence_of_element_located((By.XPATH, "//tr[@class='even' or @class='odd']"))
                )
            except TimeoutException:
                driver.switch_to.default_content()
                raise
        else:
            raise

    logger.info("Resultados carregados")


# ========================== PROCESSAMENTO ==========================

def processar_guia(driver, linha, indice, total, aba_trabalho):
    try:
        colunas = linha.find_elements(By.TAG_NAME, "td")

        # Extrai nome PRIMEIRO para sempre logar
        nome_beneficiario = _extrair_nome(colunas, linha)
        nome_arquivo = limpar_nome_arquivo(nome_beneficiario)

        # --- LINHA 1: Início do processamento (sempre aparece) ---
        logger.info(f"[{indice+1}/{total}] {nome_beneficiario}")

        if not nome_beneficiario or nome_beneficiario == "DESCONHECIDO" or len(nome_beneficiario) < 3:
            logger.info(f"  PULADA (sem nome valido)")
            return True

        # ID único
        id_final, _ = gerar_id_unico_robusto(colunas, nome_beneficiario, indice)
        if id_final in guias_processadas:
            logger.info(f"  PULADA (ja processada)")
            return True
        guias_processadas.add(id_final)

        verificar_saude_pagina(driver, aba_trabalho)

        # Seleciona radio
        try:
            radio = colunas[0].find_element(By.CSS_SELECTOR, "input[type='radio'][name='codigoSolicitacao']")
        except:
            radio = linha.find_element(By.TAG_NAME, "input")

        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", radio
        )
        time.sleep(SLEEP_CURTO)

        # Info Beneficiário
        aguardar_e_clicar(driver, By.CSS_SELECTOR, "img.btn_info_contrato[alt='Informações do Beneficiário']")
        time.sleep(SLEEP_CURTO)

        if verificar_saude_pagina(driver, aba_trabalho):
            # Erro após clicar Info Beneficiário - precisa recomeçar esta guia
            logger.warning(f"  Erro apos Info Beneficiario, retentando guia...")
            time.sleep(SLEEP_LONGO)
            # Re-seleciona radio e tenta novamente
            try:
                driver.switch_to.window(aba_trabalho)
                WebDriverWait(driver, TIMEOUT_CURTO).until(
                    EC.presence_of_element_located((By.XPATH, "//tr[@class='even' or @class='odd']"))
                )
                # Re-busca a linha e radio
                guias_retry = driver.find_elements(By.XPATH,
                    "//tr[(@class='even' or @class='odd') and td[contains(., 'Liberada')]]")
                if indice < len(guias_retry):
                    linha_retry = guias_retry[indice]
                    colunas_retry = linha_retry.find_elements(By.TAG_NAME, "td")
                    try:
                        radio_retry = colunas_retry[0].find_element(By.CSS_SELECTOR, "input[type='radio'][name='codigoSolicitacao']")
                    except:
                        radio_retry = linha_retry.find_element(By.TAG_NAME, "input")
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", radio_retry
                    )
                    time.sleep(SLEEP_CURTO)
                    aguardar_e_clicar(driver, By.CSS_SELECTOR, "img.btn_info_contrato[alt='Informações do Beneficiário']")
                    time.sleep(SLEEP_CURTO)
                    if verificar_saude_pagina(driver, aba_trabalho):
                        logger.error(f"  Erro persistente, pulando guia")
                        return False
                else:
                    logger.error(f"  Linha nao encontrada no retry")
                    return False
            except Exception as e:
                logger.error(f"  Falha no retry: {e}")
                return False

        # PDF
        try:
            aguardar_e_clicar(driver, By.XPATH, "//button[contains(@onclick, 'carregarPDFtiss')]")
        except ElementoNaoEncontradoError:
            logger.error(f"  Botao PDF nao encontrado, pulando guia")
            return False

        if verificar_saude_pagina(driver, aba_trabalho):
            logger.warning(f"  Erro apos PDF, repetindo...")
            time.sleep(SLEEP_LONGO)
            try:
                aguardar_e_clicar(driver, By.XPATH, "//button[contains(@onclick, 'carregarPDFtiss')]")
            except ElementoNaoEncontradoError:
                logger.error(f"  Botao PDF nao encontrado no retry")
                return False

        # Renomeia
        sucesso, nome_final, tamanho_kb, numero_guia = renomear_guia_sadt_imediato(nome_arquivo)

        # --- LINHA 2: Resultado do download ---
        if sucesso:
            logger.info(f"  OK: {nome_final} ({tamanho_kb:.1f} KB) - guia #{numero_guia}")
        else:
            logger.error(f"  FALHA no download do PDF")

        # Limpa e volta
        fechar_aba_about_blank(driver, aba_trabalho)
        driver.switch_to.window(aba_trabalho)

        try:
            aguardar_e_clicar(driver, By.XPATH, "//button[contains(@onclick, 'fnVoltar')]", timeout=TIMEOUT_CURTO)
            WebDriverWait(driver, TIMEOUT_CURTO).until(
                EC.presence_of_element_located((By.XPATH, "//tr[@class='even' or @class='odd']"))
            )
        except Exception:
            verificar_saude_pagina(driver, aba_trabalho)

        time.sleep(SLEEP_CURTO)
        return True

    except Exception as e:
        # --- LINHA 3 (só em caso de erro): Detalhes do erro ---
        logger.error(f"  ERRO: {type(e).__name__}: {e}")
        try:
            verificar_saude_pagina(driver, aba_trabalho)
            fechar_aba_about_blank(driver, aba_trabalho)
        except:
            pass
        return False


def verificar_e_recarregar_tabela(driver, total_esperado, data_inicial, data_final, aba_trabalho):
    try:
        driver.switch_to.window(aba_trabalho)
        guias = driver.find_elements(By.XPATH,
            "//tr[(@class='even' or @class='odd') and td[contains(., 'Liberada')]]")

        if len(guias) != total_esperado:
            logger.warning(f"Tabela inconsistente ({len(guias)} vs {total_esperado}), recarregando...")
            nova_consulta(driver, data_inicial, data_final)
            time.sleep(SLEEP_LONGO)
            return True
        return True
    except Exception as e:
        logger.error(f"Erro ao verificar tabela: {e}")
        return False


def processar_guias_liberadas(driver, codigo, data_inicial, data_final):
    global guias_por_paciente, guias_processadas
    guias_por_paciente = {}
    guias_processadas = set()

    aba_trabalho = driver.window_handles[-1]
    driver.switch_to.window(aba_trabalho)

    try:
        WebDriverWait(driver, TIMEOUT_CURTO).until(
            EC.presence_of_element_located((By.XPATH, "//tr[@class='even' or @class='odd']"))
        )
    except TimeoutException:
        logger.error("Tabela nao encontrada")
        return

    guias = driver.find_elements(By.XPATH,
        "//tr[(@class='even' or @class='odd') and td[contains(., 'Liberada')]]")
    total_inicial = len(guias)

    if total_inicial == 0:
        logger.warning("Nenhuma guia 'Liberada' encontrada")
        return

    logger.info(f"{total_inicial} guia(s) 'Liberada' encontrada(s)")

    sucessos = 0
    falhas = 0
    tentativas_recarregar = 0
    i = 0

    while i < total_inicial:
        driver.switch_to.window(aba_trabalho)

        try:
            guias_atualizadas = driver.find_elements(By.XPATH,
                "//tr[(@class='even' or @class='odd') and td[contains(., 'Liberada')]]")
            total_atual = len(guias_atualizadas)

            if total_atual != total_inicial:
                if tentativas_recarregar < 3:
                    tentativas_recarregar += 1
                    if verificar_e_recarregar_tabela(driver, total_inicial, data_inicial, data_final, aba_trabalho):
                        tentativas_recarregar = 0
                        continue
                i += 1
                continue

            if i >= len(guias_atualizadas):
                i += 1
                continue

            if processar_guia(driver, guias_atualizadas[i], i, total_inicial, aba_trabalho):
                sucessos += 1
            else:
                falhas += 1

            time.sleep(SLEEP_CURTO)
            i += 1

        except StaleElementReferenceException:
            logger.warning(f"Stale na guia {i+1}, recarregando tabela...")
            if verificar_e_recarregar_tabela(driver, total_inicial, data_inicial, data_final, aba_trabalho):
                continue
            i += 1
        except Exception as e:
            logger.error(f"Erro guia {i+1}: {e}")
            falhas += 1
            i += 1

    # Resumo final
    logger.info("=" * 50)
    logger.info(f"RESULTADO: {sucessos} OK | {falhas} falhas | {total_inicial} total")
    logger.info("=" * 50)


# ========================== MAIN ==========================

def main():
    print("=" * 50)
    print("AUTOMACAO BRADESCO SAUDE - DOWNLOAD DE GUIAS")
    print("=" * 50)

    if not validar_formato_data(DATA_INICIAL) or not validar_formato_data(DATA_FINAL):
        print("[X] Formato de data invalido! Use DD/MM/AAAA")
        input("\nENTER para finalizar...")
        return

    logger.info(f"Periodo: {DATA_INICIAL} a {DATA_FINAL}")

    driver = None
    try:
        driver = conectar_chrome_existente()
        acessar_senha_web(driver)

        for codigo in CODIGOS:
            logger.info(f"Codigo: {codigo}")
            selecionar_codigo_e_continuar(driver, codigo)
            nova_consulta(driver, DATA_INICIAL, DATA_FINAL)
            processar_guias_liberadas(driver, codigo, DATA_INICIAL, DATA_FINAL)

        print(f"\nConcluido! Arquivos em: {PASTA_DOWNLOADS}")

    except KeyboardInterrupt:
        logger.warning("Interrompido pelo usuario")
    except Exception as e:
        logger.error(f"ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()

    input("\nENTER para finalizar...")

if __name__ == "__main__":
    main()