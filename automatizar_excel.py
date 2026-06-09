import os
import pandas as pd

def extrair_abas_excel(caminho_excel, pasta_destino="./csv_extraidos"):
    """
    Lê um arquivo Excel (.xlsx) e salva cada aba como um arquivo .csv individual.
    """
    # Cria a pasta de destino se ela não existir
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
        print(f"Diretório criado: {pasta_destino}")
        
    print(f"Lendo o arquivo Excel: {caminho_excel}...")
    # O ExcelFile permite ler a estrutura do arquivo sem carregar tudo na memória imediatamente
    excel = pd.ExcelFile(caminho_excel)
    
    print(f"Abas encontradas no arquivo: {excel.sheet_names}\n")
    
    for nome_aba in excel.sheet_names:
        # Opcional: Ignorar abas irrelevantes ou automáticas (ex: Página7)
        if nome_aba.lower().startswith("página") or nome_aba.lower().startswith("pagina"):
            print(f"[-] Ignorando aba auxiliar: {nome_aba}")
            continue
            
        print(f"[+] Processando aba: {nome_aba}")
        
        # Lê os dados da aba atual
        df = excel.parse(nome_aba)
        
        # Monta o nome do arquivo CSV de saída de forma limpa
        nome_arquivo_csv = f"{nome_aba}.csv"
        caminho_completo_saida = os.path.join(pasta_destino, nome_arquivo_csv)
        
        # Salva em CSV com codificação UTF-8-SIG (garante compatibilidade com acentos e caracteres especiais)
        df.to_csv(caminho_completo_saida, index=False, encoding='utf-8-sig')
        
    print(f"\n[Sucesso] Todos os arquivos CSV foram gerados na pasta: {pasta_destino}")

if __name__ == "__main__":
    # Nome do arquivo que você carregou no ambiente
    ARQUIVO_EXCEL = "Horário 2026 (1).xlsx"
    
    # Executa a extração automatizada
    extrair_abas_excel(ARQUIVO_EXCEL)