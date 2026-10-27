# Lustre Detail

Sistema desktop de gestão para estética automotiva, feito **somente com Python + CustomTkinter + Pillow**
(sem sidebar: toda a navegação fica na barra superior). Tema escuro grafite com um único destaque âmbar.

## Instalação e execução (Windows 10/11)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
Requer Python 3.10+ (com Tkinter, incluso no instalador oficial do python.org).

## Fontes (opcional)
Veja `assets/fonts/LEIA-ME.txt`. Sem os `.ttf`, usa Segoe UI / Bahnschrift como fallback.

## Estrutura
```
main.py                 janela, navegação, atalhos, tratamento de erros
components/             widgets reutilizáveis (TopNav, DataTable, VehicleMap, diálogos, toast...)
pages/                  Dashboard, Agenda, Serviços, Clientes, Veículos, Estoque, Financeiro
data/models.py          entidades (dataclasses)   data/mock_data.py  dados de DEMONSTRAÇÃO
data/repository.py      regras de negócio + persistência JSON
utils/                  cores, tema, fontes, ícones (Pillow), car_drawing (mapa do carro), formatação
tests/                  testes automatizados
```
Extras além da estrutura sugerida: `components/widgets.py`, `data_table.py`, `dialogs.py`,
`appointment_actions.py`, `utils/car_drawing.py`, `utils/data_labels.py` (justificativa: evitar repetição
e manter o desenho do carro testável sem interface).

## Persistência
Arquivo único `lustre_detail.json` em `%APPDATA%\LustreDetail\` (altere com a variável `LUSTRE_DATA_DIR`).
Gravação atômica; arquivo corrompido é preservado como `*.corrupt-<data>` e o sistema reinicia com a demonstração.
Erros inesperados vão para `error.log` na mesma pasta. **Todos os dados iniciais são fictícios** (menu do
avatar: restaurar demonstração / limpar tudo).

## Funcionalidades implementadas
- **Dashboard**: Operação agora (progresso +25%, concluir), mapa do veículo interativo (hover/clique filtra
  serviços por região; pontos nas regiões em serviço), 4 indicadores calculados dos dados, próximos agendamentos.
- **Agenda**: busca, filtros por data (chips ou data específica) e status, novo/editar/cancelar (com confirmação),
  iniciar, avançar, concluir, registrar pagamento. Valida data, horário, funcionamento, **capacidade simultânea real**
  e conflito do mesmo veículo.
- **Clientes / Veículos**: CRUD, busca, detalhes, histórico de serviços do veículo, placa Mercosul e antiga,
  placa/telefone únicos. Exclusão bloqueada quando há histórico (cliente pode ser inativado).
- **Serviços**: catálogo (preço/duração só aqui; agendamentos guardam uma "foto" do preço), ativar/desativar.
- **Estoque**: produtos, entradas, saídas (não excede o disponível), histórico, aviso de estoque baixo.
- **Financeiro**: receitas, despesas, saldo, serviços pagos/pendentes, filtros por período e forma de pagamento.
  Valores previstos **não** entram como recebidos; pagamento de serviço gera a receita uma única vez.
- Barra superior: busca global, notificações reais (estoque baixo, pagamentos pendentes, próximo atendimento),
  menu do usuário (configurações de capacidade/horário, sobre, restaurar/limpar dados).
- Atalhos: `Ctrl+N` novo agendamento, `Ctrl+F` busca da página (ou global), `Esc` fecha menus/diálogos.

## Pendências e limitações
- Sem login/múltiplos usuários (nome "Admin" fixo); sem impressão, relatórios ou gráficos.
- "Veículos prontos" = serviços concluídos hoje (não há controle de retirada).
- Entrada de estoque não gera despesa automaticamente; dinheiro em centavos (sem casas fracionárias).
- Sem ícone próprio de janela; barra de título nativa.
- Mapa do veículo: um modelo genérico de carro (sem variação por tipo de veículo).

## Testes
```bash
python -m unittest discover -s tests -v      # regras de negócio (24 testes)
python tests/ui_smoke_test.py                # fumaça da interface com widgets simulados
```
**Importante:** o `ui_smoke_test` usa widgets *falsos* e apenas confirma que o código monta e executa sem
erros de nome/argumento. **Não foi feito teste visual** da janela real: aparência, espaçamentos, DPI e
redimensionamento precisam ser conferidos no Windows. Ajustes de tamanho provavelmente serão necessários.
