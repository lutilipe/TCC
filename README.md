# EVRP Solver - General Variable Neighborhood Search (GVNS)

Este projeto implementa um solver para o problema EVRP (Electric Vehicle Routing Problem) usando o algoritmo GVNS (General Variable Neighborhood Search).

## Funcionalidades

- **Heurística Construtiva**: Gera soluções iniciais viáveis
- **Busca Local**: Implementa operadores de busca local (2-opt, realocação de recarga, reinserção)
- **Algoritmo GVNS**: Metaheurística para otimização multi-objetivo
- **Processamento em Lote**: Capacidade de processar múltiplas instâncias automaticamente

## Como Usar

### Processar uma única instância
```bash
python src/main.py
# ou
python src/main.py ./data/100/datos-19-N100.txt
```

### Processar todas as instâncias
```bash
python src/main.py --all
```

### Processar instância específica
```bash
python src/main.py ./data/200/datos-15-N200.txt
```

## Estrutura do Projeto

```
TCC/
├── data/                    # Instâncias do problema
│   ├── 100/               # Instâncias com 100 nós
│   ├── 200/               # Instâncias com 200 nós
│   └── 400/               # Instâncias com 400 nós
├── output/                 # Resultados das execuções
├── src/
│   ├── EVRP/              # Implementação do algoritmo
│   ├── utils/             # Utilitários
│   └── main.py            # Arquivo principal
└── assets/                # Imagens e recursos
```

## Saídas

### Para execução única:
- `gvns_solutions.txt`: Soluções encontradas
- `assets/solution.png`: Visualização da melhor solução

### Para execução em lote (`--all`):
- `output/{instancia}_solutions.txt`: Soluções para cada instância
- `output/{instancia}_plot.png`: Visualização da melhor solução de cada instância

## Parâmetros do Algoritmo

- `ns`: Número de soluções por busca local (padrão: 5)
- `na`: Tamanho máximo do arquivo A (padrão: 50)
- `ls_max_iter`: Máximo de tentativas de busca local (padrão: 10)
- `max_pert`: Máximo de perturbações 2-opt (padrão: 3)
- `max_evaluations`: Máximo de avaliações (padrão: 80)

## Dependências

- Python 3.7+
- matplotlib
- numpy

## Execução

1. Clone o repositório
2. Instale as dependências: `pip install matplotlib numpy`
3. Execute: `python src/main.py --all` para processar todas as instâncias
