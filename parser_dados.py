import pandas as pd
import glob
import os

def carregar_docentes(caminho_arquivo):
    """
    Lê o arquivo de docentes e extrai as restrições (Impedimentos e Preferências).
    """
    df_docentes = pd.read_csv(caminho_arquivo)
    
    # Filtra apenas as colunas úteis e remove linhas sem nome de servidor
    df_docentes = df_docentes[['Servidor', 'Área do Conhecimento', 'Observação']].dropna(subset=['Servidor'])
    
    docentes_dict = {}
    for _, row in df_docentes.iterrows():
        nome = str(row['Servidor']).strip()
        obs = str(row['Observação']).upper() if pd.notna(row['Observação']) else ""
        
        # Extração rudimentar de regras textuais para listas lógicas
        impedimentos = []
        preferencias = []
        
        if "IMPEDIMENTO:" in obs:
            linha_imp = [linha for linha in obs.split('\n') if "IMPEDIMENTO:" in linha][0]
            impedimentos = linha_imp.replace("IMPEDIMENTO:", "").strip().split('-')
            
        if "PREFERÊNCIA:" in obs or "PREFERENCIA:" in obs:
            linha_pref = [linha for linha in obs.split('\n') if "PREFER" in linha][0]
            preferencias = linha_pref.split(':')[1].strip().split('-')

        docentes_dict[nome] = {
            'area': row['Área do Conhecimento'],
            'impedimentos': [d.strip() for d in impedimentos if d.strip()],
            'preferencias': [d.strip() for d in preferencias if d.strip()],
            'texto_original': obs
        }
        
    return docentes_dict

def carregar_turmas(diretorio_csvs):
    """
    Varre os CSVs das turmas (Info e Edificações) e extrai a demanda de carga horária.
    """
    arquivos_turmas = glob.glob(os.path.join(diretorio_csvs, "*INFO*.csv")) + \
                      glob.glob(os.path.join(diretorio_csvs, "*EDF*.csv"))
    
    turmas_dict = {}
    
    for arquivo in arquivos_turmas:
        nome_turma = os.path.basename(arquivo).replace("Horário 2026 (1).xlsx - ", "").replace(".csv", "")
        
        # Lê pulando possíveis linhas em branco no final
        df_turma = pd.read_csv(arquivo).dropna(subset=['Disciplina', 'CH/S'])
        
        demandas = []
        for _, row in df_turma.iterrows():
            # Ignora linhas de totalizadores (ex: CH/S = 20 ou 39 sem disciplina)
            if pd.isna(row['Docente']):
                continue
                
            demandas.append({
                'disciplina': str(row['Disciplina']).strip(),
                'ch_semanal': int(row['CH/S']),
                'docente': str(row['Docente']).strip()
            })
            
        turmas_dict[nome_turma] = demandas
        
    return turmas_dict

if __name__ == "__main__":
    # Ajuste os caminhos conforme o diretório dos seus arquivos
    CAMINHO_DOCENTES = "Horário 2026 (1).xlsx - Docentes.csv"
    DIRETORIO_TURMAS = "./" # Diretório atual onde estão os CSVs das turmas
    
    print("--- Carregando Restrições de Docentes ---")
    docentes = carregar_docentes(CAMINHO_DOCENTES)
    print(f"{len(docentes)} docentes processados.")
    
    # Exemplo de saída do parser
    exemplo_prof = list(docentes.keys())[0]
    print(f"Exemplo {exemplo_prof}: {docentes[exemplo_prof]}")
    
    print("\n--- Carregando Demandas das Turmas ---")
    turmas = carregar_turmas(DIRETORIO_TURMAS)
    print(f"{len(turmas)} turmas processadas.")
    
    # Exemplo de saída de uma turma
    exemplo_turma = list(turmas.keys())[0]
    print(f"Exemplo {exemplo_turma}: {turmas[exemplo_turma][0]}")