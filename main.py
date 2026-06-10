import os
import shutil
from automatizar_excel import extrair_abas_excel  # Nome real do seu script
from parser_dados import carregar_docentes, carregar_turmas
from motor_matematico import resolver_horario_estruturado
from exportador_excel import exportar_para_excel

def limpar_ambiente_antigo():
    print("[LIMPEZA] Faxinando arquivos de execuções anteriores...")
    
    # 1. Pastas de CSVs temporários
    pastas_temporarias = ['csv_gerados', 'csv_extraidos']
    for pasta in pastas_temporarias:
        if os.path.exists(pasta):
            shutil.rmtree(pasta)  # Deleta a pasta inteira e tudo dentro
            print(f" -> Pasta temporária '{pasta}/' removida.")
            
    # 2. Arquivos Excel de saída antigos
    arquivos_saida = ['Horarios_Turmas_2026.xlsx', 'Horarios_Docentes_2026.xlsx']
    for arquivo in arquivos_saida:
        if os.path.exists(arquivo):
            os.remove(arquivo)  # Deleta o arquivo físico
            print(f" -> Arquivo antigo '{arquivo}' excluído.")

def main():
    print("="*50)
    print("      INICIANDO PIPELINE DE HORÁRIOS 2026")
    print("="*50)
    
    # Executa a limpeza antes de qualquer outra ação
    limpar_ambiente_antigo()
    print("\n[PRONTO] Ambiente limpo. Iniciando processamento dos novos dados...")

    # 1. Extração dos novos dados (Cria as pastas temporárias do zero)
    # (Ajuste o nome da função/parâmetros conforme o seu automatizar_excel.py)
    extrair_dados_excel('Horário 2026 (1).xlsx') 

    # 2. Carga dos dados estruturados
    docentes = carregar_docentes()
    turmas = carregar_turmas()

    # 3. Resolução Matemática
    solver, status, alocacoes, dias_semana = resolver_horario_estruturado(docentes, turmas)

    # 4. Exportação Visual Nova (Garante arquivos 100% novos e limpos)
    if alocacoes:
        exportar_para_excel(solver, alocacoes, dias_semana, docentes, turmas)
        print("\n[FIM] Processo concluído com sucesso!")
    else:
        print("\n[ERRO] Não foi possível exportar os horários.")

if __name__ == "__main__":
    main()