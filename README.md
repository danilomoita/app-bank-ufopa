# App Bank — UFOPA

Sistema bancário acadêmico desenvolvido em Python para a disciplina de
**Programação Orientada a Objetos da UFOPA**, com interfaces de terminal e
gráfica usando o mesmo modelo de domínio e persistência em JSON.

**Somente biblioteca padrão do Python. Nenhum pacote externo é necessário.**

## Funcionalidades

- Cadastro de titulares com nome e CPF e pesquisa por parte do nome.
- Várias contas por titular, com numeração controlada pelo banco.
- Depósitos, saques e exclusão de contas.
- Validação de valores, saldo disponível, contas e CPFs duplicados.
- Salvamento após alterações e recuperação do estado ao reabrir.
- Terminal com menus e GUI com busca reativa, seleção de contas e barra de status.
- Valores de entrada com vírgula ou ponto decimal: `25,50` ou `25.50`.

## Requisitos

- **Python 3.11 ou superior**, incluindo a biblioteca padrão.
- **Tkinter/Tcl/Tk** disponível na instalação de Python, para a GUI.
- Uma sessão gráfica disponível para a GUI e seus testes.
- Git para clonar o repositório.

Não é necessário executar `pip install` nem criar um `requirements.txt` vazio.
O terminal pode ser executado sem abrir uma janela gráfica.

Confira a versão do Python:

```shell
python --version
```

Para verificar Tkinter, execute:

```shell
python -m tkinter
```

Uma pequena janela de demonstração deve aparecer. Feche-a antes de iniciar o
App Bank. Se Tkinter não estiver disponível, ajuste a instalação de Python
para incluir Tcl/Tk. Esse componente acompanha muitas distribuições de Python,
mas não todas; ele não é instalado com `pip`.

No Windows, caso `python` não seja reconhecido, use `py -3` no lugar de `python`.
Em ambientes que usam `python3`, substitua o comando da mesma forma.

## Clonar e executar

O endereço abaixo corresponde ao repositório definido para publicação:

```shell
git clone https://github.com/danilomoita/app-bank-ufopa.git
cd app-bank-ufopa
```

Execute os comandos abaixo **na raiz do projeto**, onde está este README.
Os módulos pertencem a um pacote Python e devem ser iniciados com `-m`.

### Interface de terminal

```shell
python -m bank_app.interfaces.bank_terminal
```

1. Cadastre um titular com nome e CPF.
2. Use Buscar titular; Enter no campo de busca lista todos.
3. Selecione o titular pelo índice exibido e crie uma conta.
4. Liste e selecione uma conta para depositar ou sacar.
5. Use `0` para voltar de um menu ou sair no menu principal.

A exclusão solicita o número bancário da conta, não o índice da lista.
Entradas não numéricas e erros de negócio possuem mensagens distintas.

### Interface gráfica

```shell
python -m bank_app.interfaces.bank_gui
```

- **Titulares:** busca enquanto digita, lista e formulário de cadastro.
- **Contas:** contas do titular selecionado, criação e exclusão com confirmação.
- **Movimentações:** campo de valor, depósitos e saques.
- **Resumo:** número da conta e saldo em formato brasileiro, como `R$ 1.250,50`.
- **Status:** resultado da operação, erros e alterações ainda não gravadas.

A GUI utiliza `tkinter`, `ttk.Style`, fontes padrão e o tema `clam` quando
disponível no próprio Tk. Não depende de temas, fontes ou imagens baixados.

| Atalho | Ação |
| --- | --- |
| `Ctrl+F` | Focar a busca e selecionar o texto |
| `Ctrl+N` | Focar o nome do novo titular |
| `Ctrl+S` | Solicitar salvamento |
| `Enter` no nome | Passar ao CPF |
| `Enter` no CPF | Solicitar cadastro |
| `Enter` na lista de contas | Focar o valor, com uma conta selecionada |
| `Esc` na busca | Limpar o filtro |
| `Tab` | Percorrer campos e botões |

## Arquitetura e organização

O projeto aplica separação de responsabilidades em três camadas:

```text
Interfaces: Terminal / GUI
    ├── chamam operações → Modelo de domínio
    └── solicitam salvar/carregar → Persistência → bank.json
                                       └── utiliza a API pública do modelo
```

| Camada | Arquivos | Responsabilidade |
| --- | --- | --- |
| Modelo | `exceptions.py`, `account.py`, `holder.py`, `bank.py` | Entidades, regras e exceções; sem `print`, `input`, Tkinter ou arquivos |
| Persistência | `database.py` | Salvar JSON e reconstruir objetos pelas APIs públicas |
| Interfaces | `bank_terminal.py`, `bank_gui.py` | Entrada, apresentação, eventos, erros e solicitação de salvamento |

```text
app-bank-ufopa/
├── bank_app/
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   ├── account.py
│   │   ├── holder.py
│   │   └── bank.py
│   ├── persistence/
│   │   ├── __init__.py
│   │   └── database.py
│   └── interfaces/
│       ├── __init__.py
│       ├── bank_terminal.py
│       └── bank_gui.py
├── docs/
│   ├── screenshots/
│   ├── app_bank.pdf
│   ├── Critérios_de_avaliação_do_projeto.txt
│   ├── guia_desenvolvimento_com_ia.md
│   ├── inspecao_interface.md
│   └── publicar_no_github.md
├── tests/
│   ├── test_domain_and_persistence.py
│   ├── test_bank_terminal.py
│   ├── test_bank_gui.py
│   └── test_interface_restart.py
├── .gitignore
└── README.md
```

O encapsulamento usa atributos internos e propriedades. As exceções derivam
de `BankError`. `holders()`, `accounts()` e `filter_by_name()` são geradores.
A associação navega do titular para suas contas; a conta não guarda titular.

## Persistência dos dados

O arquivo padrão é criado automaticamente no primeiro salvamento:

```text
bank_app/persistence/bank.json
```

Na primeira execução, a ausência do arquivo resulta em banco vazio.
`Database.load()` reconstrói titulares com `Bank.create_holder()` e contas
com `Account()` e `Bank.add_account()`, reaplicando as validações do modelo.

Após cada alteração aceita, as interfaces chamam `database.save(bank)`.
Em caso de falha ao gravar, os dados ficam em memória e a opção Salvar
novamente permite nova tentativa. O JSON não é versionado no GitHub;
cada clone começa com seus próprios dados locais.

Execute uma interface por vez. O projeto não sincroniza sessões concorrentes
que gravam no mesmo arquivo.

## Testes

```shell
python -B -m unittest discover -s tests -v
```

Na última execução registrada, **74 testes passaram**:

| Área | Testes |
| --- | --- |
| Domínio, persistência e arquitetura | 38 |
| Terminal | 17 |
| GUI | 17 |
| Fechamento e reabertura em processos independentes | 2 |

Os testes usam `unittest`, arquivos temporários e dados fictícios. A GUI é
testada com widgets reais em janelas ocultas, sem diálogos interativos.
Os testes de reinicialização verificam o estado persistido depois de encerrar
e iniciar novos processos, incluindo entradas com vírgula e ponto.

Para testar somente domínio e persistência, sem abrir Tkinter:

```shell
python -B -m unittest discover -s tests -p test_domain_and_persistence.py -v
```

## Demonstração visual

As capturas serão adicionadas pela equipe em **`docs/screenshots/`**.
Use dados fictícios e os seguintes nomes sugeridos:

| Arquivo | Conteúdo |
| --- | --- |
| `terminal.png` | Menu e uma operação concluída no terminal |
| `gui.png` | Janela com titular, conta e saldo selecionados |

Depois de salvar as imagens, descomente os blocos abaixo. Eles ficam
comentados até existirem imagens, evitando links quebrados:

<!-- Remova os marcadores de comentário quando as capturas existirem.
### Terminal
![Interface de terminal do App Bank](docs/screenshots/terminal.png)

### Interface gráfica
![Interface gráfica do App Bank](docs/screenshots/gui.png)
-->

Consulte também [as orientações para capturas](docs/screenshots/README.md).
Não são necessárias imagens para executar a aplicação.

## Notas para estudo e manutenção

- O saldo é calculado internamente com `Decimal`; a propriedade pública e o
  JSON continuam numéricos com `float`, sujeitos à sua precisão para números
  com muitos dígitos.
- A unicidade do CPF considera o texto após remover espaços nas extremidades.
  Não há validação de dígitos verificadores nem normalização de pontuação.
- `Bank.create_account(holder)` retorna o titular, conforme o contrato adotado.
- A numeração é o maior número de conta existente mais um. Não há contador
  histórico para números de contas excluídas.
- Valores aceitam `1000,50` ou `1000.50`; `1.000,50` não é aceito.

O histórico da inspeção dimensional e o limite da avaliação visual por imagem
estão registrados em [inspecao_interface.md](docs/inspecao_interface.md).

## Documentação da equipe

- [Guia de desenvolvimento com IA e prompts utilizados](docs/guia_desenvolvimento_com_ia.md)
- [Como publicar e atualizar o projeto no GitHub](docs/publicar_no_github.md)
- [Especificação da disciplina](docs/app_bank.pdf)
- [Critérios de avaliação](docs/Critérios_de_avaliação_do_projeto.txt)

Para contribuir, trabalhe em uma branch própria, mantenha as regras no domínio
e execute os testes antes de propor uma alteração. Não adicione dependências
externas: a execução deve continuar usando somente a biblioteca padrão.
