# main.py
import os

# Importações dos nossos módulos
from automatizar_excel import extrair_abas_excel
from parser_dados import carregar_docentes, carregar_turmas
from motor_matematico import resolver_horario_estruturado
from exportador_excel import exportar_horarios

# Nome do arquivo base
ARQUIVO_EXCEL = "Horário 2026 (1).xlsx"
PASTA_CSVS = "./csv_gerados"

def executar_pipeline():
    print("="*50)
    print(" SISTEMA DE GERAÇÃO DE HORÁRIOS ")
    print("="*50)

    # ---------------------------------------------------------
    # FASE 1: INGESTÃO E PREPARAÇÃO DOS DADOS
    # ---------------------------------------------------------
    print("\n[FASE 1] Preparando dados...")
    # 1.1 Transforma o Excel em múltiplos CSVs
    extrair_abas_excel(ARQUIVO_EXCEL, pasta_destino=PASTA_CSVS)

    # 1.2 O Parser lê a pasta de CSVs recém-criada
    print("\nA ler CSVs e montar dicionários...")
    caminho_docentes = os.path.join(PASTA_CSVS, "Docentes.csv")
    docentes = carregar_docentes(caminho_docentes)
    turmas = carregar_turmas(PASTA_CSVS)
    print(f"Pronto! {len(docentes)} docentes e {len(turmas)} turmas mapeados para o Solver.")

    # ---------------------------------------------------------
    # FASE 2: MOTOR MATEMÁTICO (OR-TOOLS)
    # ---------------------------------------------------------
    print("\n[FASE 2] Iniciando o Motor de Resolução...")
    solver, status, alocacoes, dias = resolver_horario_estruturado(docentes, turmas)

    # ---------------------------------------------------------
    # FASE 3: EXPORTAÇÃO
    # ---------------------------------------------------------
    if solver: # Se o horário foi resolvido com sucesso (Optimal ou Feasible)
        print("\n[FASE 3] Gerando planilhas de saída...")
        exportar_horarios(solver, alocacoes)
        print("\n[CONCLUÍDO] Processo finalizado com sucesso. Verifique os ficheiros Excel gerados.")
    else:
        print("\n[ERRO] O algoritmo não conseguiu fechar o horário.")
        print("Ação recomendada: Verifique se as restrições de impedimentos dos docentes não estão a inviabilizar a carga horária exigida.")

if __name__ == "__main__":
    executar_pipeline()