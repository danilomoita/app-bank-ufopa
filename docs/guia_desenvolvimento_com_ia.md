# App Bank: guia de desenvolvimento com Engenharia de Prompts e revisão de código

**Disciplina:** Programação Orientada a Objetos — UFOPA  
**Público:** equipe do projeto  
**Data:** 26 de outubro de 2026  
**Escopo:** arquitetura, desenvolvimento incremental, prompts utilizados e estudo dos conceitos.

## Como utilizar este guia

Leia primeiro a estratégia e as responsabilidades de cada módulo. Depois, acompanhe os prompts na ordem em que foram utilizados, comparando cada solicitação com o código produzido. Finalize executando os testes e respondendo às perguntas de revisão sem consultar a IA.

O projeto foi construído em **seis etapas, com sete módulos principais**: a primeira etapa reuniu `exceptions.py` e `account.py`. Não houve geração de todo o sistema de uma única vez.

Os prompts registram a intenção de cada momento. A implementação final também incorpora correções descobertas nos testes e ajustes posteriores de organização e apresentação. Reutilizar o mesmo prompt não garante código idêntico: a equipe precisa fornecer o contexto, conferir os contratos e executar as verificações.

## 1. Visão geral da estratégia

### 1.1. Desenvolvimento por camadas

A sequência adotada foi:

```text
Modelo de domínio → Persistência JSON → Interface de terminal → Interface gráfica
```

Essa é a ordem de construção. As dependências do código seguem a separação abaixo:

```text
Terminal ─────┐
              ├── chama operações ──→ Modelo: Bank, Holder, Account
GUI ──────────┘
      │
      └── solicita salvar/carregar ─→ Database ─→ bank.json
                                         │
                                         └── usa a API pública do modelo
```

O modelo não depende da interface nem da persistência. Por isso, a mesma regra de saque é utilizada no terminal, na GUI e nos testes. O projeto adota separação de responsabilidades em camadas; não acrescenta uma camada de controlador ou serviços que não foi necessária ao escopo acadêmico.

| Camada | Responsabilidade | Limites |
| --- | --- | --- |
| Modelo | Representar entidades e preservar regras do banco | Não usa `print`, `input`, Tkinter ou arquivos |
| Persistência | Converter objetos para JSON e reconstruí-los | Não decide quando o usuário deve salvar nem exibe mensagens |
| Interfaces | Capturar entrada, apresentar resultados, chamar o modelo e solicitar salvamento | Não calculam saldo nem decidem se um saque é permitido |

### 1.2. Relação com os critérios de avaliação

| Critério | Peso | Como foi atendido no desenvolvimento |
| --- | --- | --- |
| A. Fluxo completo pelo terminal | 2 | Menus de titulares e contas, depósitos, saques, exclusão e salvamento |
| B. Fluxo completo pela GUI | 2 | Dois painéis, busca reativa, seleção, operações, confirmação de exclusão e status |
| C. Separação entre modelo e interface | 2 | As duas interfaces chamam as mesmas entidades e delegam arquivos a `Database` |
| D. Correção das regras do domínio | 4 | Validações, exceções e testes de casos válidos, inválidos e regressões |

Os testes fornecem evidências sobre os comportamentos implementados; não equivalem a uma garantia de nota nem cobrem todas as situações possíveis.

### 1.3. Conceitos de POO aplicados

| Conceito | Aplicação no App Bank |
| --- | --- |
| Encapsulamento | Número e saldo da conta ficam em atributos internos; operações passam por métodos |
| Propriedades | `number` e `balance` permitem leitura; nome e CPF possuem setters com validação |
| Associação | O titular conhece suas contas; a conta não conhece o titular |
| Herança | Exceções específicas herdam de `BankError`; `BankApp` herda de `tk.Tk` |
| Tratamento uniforme de subtipos | Um `except BankError` trata diferentes exceções bancárias |
| Funções como parâmetros | A interface reutiliza o fluxo de transação recebendo depósito ou saque como operação |
| Geradores | Titulares e contas são percorridos com `yield` e `yield from` |
| Injeção de dependência | Interfaces recebem o banco e a persistência, facilitando testes isolados |

Receber funções como parâmetros é uma forma de reutilização e composição de comportamento. Isso não deve ser confundido, por si só, com uma hierarquia de métodos sobrescritos.

O relacionamento titular–contas foi modelado como associação de posse em um único sentido, conforme a proposta do trabalho. Python não garante automaticamente exclusividade de posse ou destruição conjunta dos objetos. A equipe deve entender essas diferenças ao explicar o termo composição.

### 1.4. Engenharia de Prompts sem perder o controle

Cada solicitação de implementação delimitou cinco elementos:

1. **Contexto:** disciplina, entidades existentes e regras do documento.
2. **Escopo:** arquivo ou etapa que deveria ser implementado naquele momento.
3. **Contrato:** atributos, parâmetros, retornos e exceções esperados.
4. **Restrições:** domínio isolado, persistência separada e ausência de bibliotecas externas.
5. **Entrega verificável:** código comentado, explicação das decisões e testes.

O ciclo de trabalho foi: **especificar → gerar uma parte → ler e explicar → testar → corrigir → integrar → avançar**.

A IA auxiliou na implementação e na identificação de problemas. O controle humano consistiu em escolher o escopo, exigir justificativas, impedir a geração integral de uma vez e solicitar verificações antes da etapa seguinte.

Ao replicar o processo, a equipe deve revisar o que mudou antes de aceitar outra etapa. Se utilizar Git, faça commits pequenos após verificações aprovadas; essa é uma recomendação de continuidade, não uma afirmação de que o histórico do projeto já foi versionado dessa forma.

## 2. Passo a passo do desenvolvimento

### 2.1. Organização do projeto

Os arquivos de código foram separados dos documentos da disciplina:

```text
bank_app/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── account.py
│   ├── holder.py
│   └── bank.py
├── persistence/
│   ├── __init__.py
│   └── database.py
└── interfaces/
    ├── __init__.py
    ├── bank_terminal.py
    └── bank_gui.py
docs/
tests/
README.md
.gitignore
```

Os arquivos `__init__.py` identificam pacotes. As importações entre módulos respeitam essa estrutura. O `.gitignore` exclui arquivos gerados, ambientes locais e o JSON de dados da aplicação do versionamento.

### 2.2. Etapa 1 — Exceções e conta

#### `exceptions.py`

Foi criada a exceção base `BankError(Exception)`, com as subclasses:

| Exceção | Situação representada |
| --- | --- |
| `InvalidDataError` | Dado obrigatório ausente ou incompatível com a entidade |
| `InvalidAmountError` | Valor de depósito ou saque inválido |
| `InsufficientFundsError` | Saque superior ao saldo |
| `DuplicateHolderError` | CPF já cadastrado |
| `DuplicateAccountError` | Número de conta já utilizado |
| `HolderNotFoundError` | Titular não pertence ao banco |
| `AccountNotFoundError` | Conta não pertence ao titular consultado |

As exceções informam a falha sem determinar como ela será exibida. O terminal imprime a mensagem; a GUI apresenta uma caixa de diálogo. A herança permite tratamento comum por `BankError` e específico quando necessário.

#### `account.py`

Foi implementada a classe `Account`, com `__number` e `__balance` e propriedades somente leitura. O construtor valida o número inteiro positivo e o saldo inicial finito e não negativo.

`deposit()` exige valor positivo. `withdraw()` também verifica a disponibilidade do saldo. As validações acontecem antes da alteração do estado. O método `__str__()` apresenta o número com pelo menos quatro dígitos: `7` aparece como `0007`, sem truncar números maiores.

O prefixo `__` aplica *name mangling*: dificulta acesso acidental e colisões de nomes, mas não constitui uma barreira absoluta de segurança.

**Correção posterior:** os testes mostraram que `0.30 - 0.10` com `float` podia impedir um saque seguinte de `0.20`. O saldo passou a utilizar `Decimal` internamente, com precisão ajustada para a operação. A propriedade pública continua retornando `float`, preservando a compatibilidade com o JSON numérico.

Essa compatibilidade mantém uma limitação: a saída pública e o arquivo ainda estão sujeitos à precisão de `float` para números com muitos dígitos. A correção não converteu o projeto inteiro para uma API pública baseada em `Decimal`.

### 2.3. Etapa 2 — Titular e contas: `holder.py`

`Holder` representa nome, CPF e as contas de um titular. O construtor utiliza os próprios setters de nome e CPF, garantindo que as validações também sejam aplicadas na criação. Valores vazios, somente espaços ou de tipo inadequado são rejeitados.

As contas ficam no dicionário `_accounts`, indexado por número. Isso permite busca, inserção e exclusão por chave, com custo médio constante em condições usuais.

Os métodos públicos são:

- `add_account(account)`: inclui uma conta e rejeita número repetido no próprio titular.
- `get_account(account_number)`: retorna a conta ou lança `AccountNotFoundError`.
- `delete_account(account_number)`: remove a conta ou informa que ela não existe.
- `accounts()`: produz as contas com `yield from self._accounts.values()`.

Um único `_` indica uso interno por convenção. O gerador evita devolver diretamente o dicionário; contudo, as contas retornadas são os objetos originais, e não cópias imutáveis. Depósitos e saques continuam disponíveis nesses objetos.

### 2.4. Etapa 3 — Cadastro central: `bank.py`

`Bank` reúne os titulares e aplica regras que exigem conhecer todo o cadastro:

- Impedir CPF duplicado no cadastro.
- Conferir que o titular informado é o próprio objeto registrado no banco.
- Impedir número de conta duplicado entre diferentes titulares.
- Escolher o próximo número com o maior número existente mais um, ou 1 quando não houver contas.
- Criar contas com saldo zero.
- Produzir titulares e pesquisar nomes com geradores.

`filter_by_name()` utiliza comparação sem distinção de maiúsculas e minúsculas com `casefold()`. Texto vazio retorna todos os titulares.

**Contrato a observar:** na implementação atual, `create_account(holder)` retorna o `Holder`, como solicitado no prompt da etapa 3. A sugestão inicial do PDF previa retorno `Account`. Quem integrar novos módulos deve conferir o contrato real; não deve presumir que o retorno é a conta recém-criada.

**Numeração após exclusão:** o próximo número é recalculado a partir das contas que ainda existem. Excluir a conta de maior número pode permitir reutilizar esse número. Não foi implementado um contador histórico permanente.

**Correção posterior do CPF:** apenas validar o cadastro não bastava, porque o setter permitia alterar o CPF para outro já existente. Agora, `Bank` fornece uma função de validação ao criar `Holder`. O setter consulta essa função antes de mudar o atributo. Uma alteração recusada preserva o CPF anterior. `Holder` não precisa importar `Bank`, evitando dependência circular.

A verificação atual compara os CPFs como texto após remover espaços das extremidades. Ela não valida dígitos verificadores nem normaliza pontuação. Esses comportamentos não devem ser apresentados como funcionalidades já existentes.

### 2.5. Etapa 4 — Persistência: `database.py`

`Database` recebe um `Path` opcional. O padrão é `bank.json` ao lado de `database.py`, em `bank_app/persistence/`, sem depender da pasta de onde o programa é iniciado.

O método `save(bank)` percorre os geradores e consulta propriedades públicas para construir uma lista de dicionários. A gravação usa UTF-8 e `json.dump(..., ensure_ascii=False, indent=2)`.

Exemplo do formato:

```json
[
  {
    "name": "Maria Oliveira",
    "cpf": "111.111.111-11",
    "accounts": [
      {"number": 1, "balance": 1250.5}
    ]
  }
]
```

O método `load()` reconstrói o estado por etapas:

1. Lê o JSON; se o arquivo não existir, retorna `Bank()` vazio.
2. Cria um novo banco em memória.
3. Cadastra cada titular com `bank.create_holder(name, cpf)`.
4. Instancia cada `Account(number, balance)`.
5. Inclui cada conta com `bank.add_account(holder, account)`.
6. Retorna o banco reconstruído.

Nenhum atributo privado é preenchido diretamente pela persistência. Com isso, duplicatas e dados bancários inválidos também são recusados ao carregar. JSON com sintaxe inválida gera erro; não é silenciosamente tratado como banco vazio.

### 2.6. Etapa 5 — Terminal: `bank_terminal.py`

`BankTerminal` recebe `Bank` e `Database` no construtor. O ponto de entrada carrega o banco e fornece essas dependências.

A navegação utiliza três níveis:

```text
Menu principal → Buscar titular → Menu do titular
                                     └→ Listar/selecionar conta → Menu da conta
```

O terminal permite cadastrar titulares, pesquisar nomes, criar e excluir contas, depositar e sacar. O método genérico `choose()` devolve o objeto escolhido; entrada vazia ou inválida resulta em `None`.

A conversão numérica pertence à interface. Um texto como `25,50` passa pela substituição de vírgula por ponto antes de `float()`. `ValueError` recebe mensagem de entrada numérica inválida; `BankError` apresenta a explicação fornecida pelo modelo.

Após uma alteração aceita, a interface chama `database.save(bank)`. Se houver falha de gravação, informa que os dados estão em memória e permite tentar salvar novamente. Não informa que a operação foi persistida quando a gravação falhou.

### 2.7. Etapa 6 — GUI: `bank_gui.py`

`BankApp` herda de `tk.Tk` e recebe as mesmas dependências do terminal. A janela possui:

- Painel Titulares com busca em tempo real, `ttk.Treeview` e formulário de cadastro.
- Painel Contas com lista, criação e exclusão com confirmação.
- Campo de valor e botões de depósito e saque.
- Barra de status e mensagens por `messagebox.showerror()`.
- Atualização das listas e preservação da seleção após transações.
- Salvamento após alterações e recuperação quando a gravação falha.

Os botões chamam métodos do domínio. A GUI não compara valor de saque com saldo nem altera diretamente o saldo de uma conta.

Posteriormente, foi aplicada personalização com `ttk.Style`, tema padrão `clam` quando disponível, fontes da instalação, cabeçalho azul-escuro, linhas alternadas, resumo da conta e valores brasileiros. A formatação visual, por exemplo `R$ 1.250,50`, não muda o valor do modelo.

Não foi instalada nenhuma biblioteca externa. Tkinter precisa estar disponível na instalação de Python usada para executar a GUI.

### 2.8. Validação e correções ao longo do processo

| Marco registrado | Resultado |
| --- | --- |
| Primeira suíte integrada do domínio e persistência | 33 testes: 31 passaram; um falhou e outro terminou com erro |
| Após corrigir precisão monetária e alteração de CPF | 38 testes passaram |
| Após o terminal | 55 testes passaram |
| Após a GUI inicial | 71 testes passaram |
| Após os testes de fechamento e reabertura | 73 testes passaram |
| Após personalização e teste do resumo monetário | 74 testes passaram |

Os testes de reinicialização executam cada interface em processos independentes: cadastram um titular, criam uma conta, depositam `100,50` e `0.25`, encerram e verificam R$ 100,75 no JSON. Outro processo carrega esse estado, saca `0.25` e `0,50`, encerra e deixa R$ 100,00. Uma terceira abertura confirma os dados preservados.

Os testes usam dados fictícios e diretórios temporários. A GUI é testada com widgets reais e janela oculta.

**Inspeção visual:** a checagem dimensional em 1180 × 800 e 980 × 700 não detectou cortes nos rótulos avaliados nem componentes em `grid` fora dos limites. A avaliação por imagem continua pendente porque o recurso de captura de janela falhou. Não se deve confundir testes funcionais ou dimensionais com uma revisão visual completa.

## 3. Lista dos prompts utilizados

### Nota sobre a transcrição

Os blocos abaixo registram os prompts operacionais em ordem cronológica. O texto foi preservado; foram apenas removidos escapes de apresentação, como barras antes de acentos graves, quebras de linha artificiais e entidades HTML de espaço. Os títulos e objetivos das etapas aparecem nas explicações anteriores. Mensagens de simples confirmação foram omitidas, exceto quando autorizaram uma correção ou personalização. Trechos de mensagens maiores estão identificados como trechos.

### 3.1. Contextualização inicial

```text
Este projeto é um sistema bancário em Python para a disciplina de Programação Orientada a Objetos da UFOPA. O código deve seguir estritamente a arquitetura limpa definida no PDF: Modelo isolado (sem prints/inputs), Persistência em JSON separada, e Interfaces (Terminal e GUI). Aplicamos encapsulamento, propriedades, geradores e exceções customizadas.
```

Na definição do desenvolvimento por fases, foi estabelecido o seguinte limite. Este é um trecho literal daquela mensagem:

```text
Não quero que o código inteiro seja gerado de uma vez
```

### 3.2. Etapa 1 — `exceptions.py` e `account.py`

```text
Atue como um mentor de Programação Orientada a Objetos em Python. Estamos desenvolvendo a Parte 1 de um sistema bancário acadêmico.
Preciso que você escreva APENAS o código para dois arquivos, explicando o raciocínio de POO por trás deles:
1. `exceptions.py`: Contendo a exceção base `BankError(Exception)` e as subclasses exigidas: `InvalidDataError`, `InvalidAmountError`, `InsufficientFundsError`, `DuplicateHolderError`, `DuplicateAccountError`, `HolderNotFoundError`, `AccountNotFoundError` (todas herdando de BankError).
2. `account.py`: A classe `Account` que possui:
  - Atributos privados para número e saldo (`__number`, `__balance`, iniciando com saldo 0.0 por padrão).
  - Construtor `__init__(self, number: int, balance: float = 0.0)` que lança `InvalidDataError` se o número não for positivo ou se o saldo for negativo.
  - Propriedades somente leitura (`@property`) para `number` e `balance` (o saldo só muda via métodos).
  - Métodos `deposit(amount)` e `withdraw(amount)` com validações estritas (lançando `InvalidAmountError` se o valor não for positivo, e `InsufficientFundsError` se o saque exceder o saldo).
  - Método `__str__` formatando o número da conta com 4 dígitos (ex: 0007).

Por favor, forneça o código comentado.
```

**Por que esse prompt ajudou:** limitou a entrega, definiu a API e solicitou justificativas, permitindo revisar o primeiro núcleo de domínio antes de ampliar o sistema.

### 3.3. Organização da pasta

```text
Certo. Organiza a pasta do projeto para não ficar código misturado com outros arquivos.
Vamos seguir com boas práticas de programação
```

**Resultado:** código em pacotes, materiais da disciplina em `docs/`, README e exclusão de arquivos gerados por `.gitignore`.

### 3.4. Etapa 2 — `holder.py`

```text
Continuando o projeto do Banco em Python, agora vamos implementar o arquivo `holder.py`.
Relembrando as regras:
- O `Holder` representa um titular com nome, CPF e um dicionário interno privado `_accounts` onde a chave é o número da conta.
- `__init__(name: str, cpf: str)` começa sem contas e deve usar os setters de nome e CPF para validar na criação.
- Name e CPF devem ser propriedades (`@property` e `@*.setter`) que lançam `InvalidDataError` se forem vazios.
- Métodos obrigatórios: `add_account(account)` (lança `DuplicateAccountError` se já existir), `delete_account(account_number)` (lança `AccountNotFoundError`), `get_account(account_number)` (retorna a conta ou lança `AccountNotFoundError`), e o gerador `accounts(self)` usando `yield from self._accounts.values()`.

Escreva o código limpo de `holder.py` e explique brevemente por que usamos um gerador com `yield from` em vez de expor o dicionário de contas diretamente.
```

**Ponto de revisão:** o termo privado no prompt não muda a semântica de Python: `_accounts` é interno por convenção. O gerador não torna os objetos retornados imutáveis.

### 3.5. Etapa 3 — `bank.py`

```text
Vamos avançar para o arquivo `bank.py` do nosso app bank em Python.
O `Bank` é o cadastro central que gerencia os titulares e os números das contas globalmente.
Preciso que implemente:
- `__init__`: começa sem titulares.
- `create_holder(name, cpf) -> Holder`: cria e cadastra um titular (lança `DuplicateHolderError` se o CPF já existir).
- `_next_account_number() -> int`: método privado que calcula o próximo número (maior número existente + 1, ou 1 se não houver contas).
- `create_account(holder) -> Holder`: cria uma conta com saldo zero usando o próximo número e a adiciona ao titular.
- `add_account(holder, account)`: adiciona uma conta já existente a um titular (lança `HolderNotFoundError` se o titular não for do banco, e `DuplicateAccountError` se o número da conta já existir em qualquer titular do banco).
- Geradores `holders()` e `filter_by_name(name)` (case-insensitive, onde string vazia retorna todos).

Escreva o código de `bank.py` e explique por que a criação e validação global dos números de conta ficam no `Bank` e não direto no `Holder`.
```

**Ponto de revisão:** o retorno `Holder` pedido aqui é diferente do retorno `Account` sugerido inicialmente no PDF. Essa diferença foi identificada e comunicada, e a implementação seguiu o prompt. Uma equipe precisa discutir diferenças assim; elas não devem passar despercebidas.

### 3.6. Etapa 4 — `database.py`

```text
Agora precisamos implementar a camada de persistência no arquivo `database.py`.
Regras:
- Recebe um caminho de arquivo opcional (`path: Path`, por padrão `bank.json`).
- Método `load() -> Bank`: lê o JSON e reconstrói o banco utilizando estritamente os métodos públicos do `Bank` (`create_holder` e `add_account`), garantindo que o arquivo seja validado pelas regras de negócio ao carregar. Se o arquivo não existir, retorna um Bank vazio.
- Método `save(bank)`: grava todos os titulares e contas no arquivo JSON usando `json.dump(..., ensure_ascii=False, indent=2)` para manter os acentos legíveis.

Escreva o código de `database.py` e explique como o método `load` reconstrói o estado do banco instanciando as classes do modelo.
```

**Por que esse prompt ajudou:** proibiu reconstruir o estado por atalhos em atributos privados e reaproveitou as validações existentes.

### 3.7. Verificação antes das interfaces

```text
Vamos testar as fases de 1 a 4 antes de partir para a próxima fase, quero garantir que está tudo funcionando e que o entendimento do projeto está sendo bem sucedido
```

Após os testes revelarem os problemas, foi autorizado o ajuste:

```text
perfeito, pode implementar a correção antes de seguirmos
```

**Resultado:** uso interno de `Decimal`, proteção contra CPF duplicado pelo setter e testes de regressão. Os prompts originais de conta e titular não detalhavam essas soluções; elas surgiram da revisão baseada em evidências.

### 3.8. Etapa 5 — `bank_terminal.py`

```text
Estamos na fase 5 do nosso App Bank em Python: a implementação da interface de terminal (`bank_terminal.py`).
O modelo (Bank, Holder, Account, Database) e as exceções já estão prontos. A interface NÃO deve conter nenhuma regra de negócio, apenas capturar entradas, chamar os métodos do modelo, tratar erros e chamar o database.save(bank) após cada alteração.

Por favor, me ajude a implementar a classe `BankTerminal` com:
1. Injeção de dependência do `Bank` e do `Database` no construtor.
2. O método genérico `choose(items: list[T]) -> T | None` que exibe uma lista numerada e retorna o item escolhido ou None se o usuário der Enter/digitar inválido.
3. Os menus estruturados:
  - **Menu Principal:** Cadastrar titular novo ou buscar titular por parte do nome (Enter lista todos usando filter_by_name).
  - **Menu do Titular:** Listar contas, criar conta ou excluir conta pelo número.
  - **Menu da Conta:** Depositar ou sacar (aceitando vírgula ou ponto como separador decimal).
4. Tratamento de erros robusto: capturar `BankError` mostrando a mensagem para o usuário, e capturar `ValueError` separadamente (ex: "digite um valor numérico") quando o texto digitado não puder ser convertido para número.

Escreva o código completo e comentado de `bank_terminal.py`.
```

**Por que esse prompt ajudou:** descreveu o fluxo do usuário e os limites da interface, distinguindo erro de conversão de violação de regra bancária.

### 3.9. Etapa 6 — `bank_gui.py`

```text
Chegamos à fase final do projeto: a interface gráfica (`bank_gui.py`) usando Tkinter, correspondendo ao Critério B e C do trabalho.
Relembrando os requisitos do documento:
- A classe `BankApp` herda de `tk.Tk`.
- Layout dividido em dois painéis lado a lado:
  1. **Titulares:** Campo de busca (filtra a lista em tempo real), lista de titulares em um `ttk.Treeview`, e campos para cadastrar um titular novo (nome e CPF).
  2. **Contas:** Contas do titular selecionado, botões "Nova conta" e "Excluir conta" (com confirmação), e campo de valor com botões "Depositar" e "Sacar".
- Barra de status embaixo mostrando o resultado da última operação.
- Erros do banco exibidos em uma caixa de mensagem (`messagebox.showerror`).
- Chamada obrigatória de `database.save(bank)` após qualquer operação de modificação.

Por favor, implemente o código de `bank_gui.py` mantendo a separação estrita de responsabilidades (a interface só chama métodos do modelo e gerencia o layout/eventos).
```

**Por que esse prompt ajudou:** especificou os componentes e eventos sem transferir regras de negócio para os botões.

### 3.10. Reabertura e separador decimal

```text
**Teste a persistência após a interface:** Assim que terminar o terminal ou a GUI, faça algumas operações (criar titular, depositar), feche o programa e abra de novo. O arquivo `bank.json` deve refletir exatamente o estado anterior graças ao `database.load()`.

**Validação de vírgula/ponto:** No terminal e na GUI, lembre-se de tratar a substituição de vírgula por ponto (`amount.replace(',', '.')`) antes de converter para `float`, garantindo que o usuário possa digitar valores monetários no formato brasileiro sem que o programa quebre com `ValueError`.
```

**Resultado:** testes de reinicialização em processos independentes para as duas interfaces. A substituição suporta `1000,50` e `1000.50`, mas não a mistura de separador de milhar e decimal, como `1.000,50`.

### 3.11. Personalização sem dependências externas

```text
A interface ficou bem simples. Como podemos melhorar sem instalar nenhuma biblioteca? O professor deixou isso expressamente proibido porque quando ele for testar quer que o projeto rode sem problemas
```

Após a apresentação das melhorias propostas:

```text
Perfeito, vamos fazer a personalização
```

**Resultado:** personalização apenas com recursos padrão de Tkinter/ttk. A preservação dos testes funcionais permitiu alterar a apresentação sem modificar o domínio.

### 3.12. Inspeção posterior

```text
Termine a ispenção
```

**Resultado registrado:** checagem dimensional concluída nos dois tamanhos de janela; inspeção por imagem ainda pendente por falha da captura. A grafia acima foi mantida por ser uma transcrição do pedido.

## 4. Instruções de estudo e revisão da equipe

### 4.1. Preparação e execução

Utilize Python com suporte a Tkinter. Para executar a suíte atual, que utiliza `unittest.TestCase.enterContext`, utilize Python 3.11 ou superior. Os testes gráficos precisam de uma sessão gráfica disponível. Não é necessário instalar pacotes com `pip`.

Na raiz do projeto:

```powershell
# Interface de terminal
python -m bank_app.interfaces.bank_terminal

# Interface gráfica
python -m bank_app.interfaces.bank_gui

# Testes
python -B -m unittest discover -s tests -v
```

Terminal e GUI usam o mesmo arquivo de dados padrão. Execute uma interface por vez: o projeto não implementa sincronização entre sessões concorrentes nem mesclagem automática de gravações.

### 4.2. Roteiro de leitura

1. Leia `exceptions.py` e explique a hierarquia sem executar o projeto.
2. Leia `Account` e identifique todos os caminhos que alteram o saldo.
3. Leia `Holder` e desenhe a associação com as contas.
4. Leia `Bank` e separe validações locais de verificações globais.
5. Leia `Database.load()` e acompanhe a reconstrução de um JSON de exemplo.
6. Siga uma chamada de depósito do terminal até o modelo e o salvamento.
7. Repita o percurso a partir do botão da GUI e compare as duas interfaces.
8. Execute os testes e explique por que uma operação recusada não deve chamar `save()`.

### 4.3. Perguntas de fixação

#### Encapsulamento e propriedades

1. Por que `balance` não possui setter público?
2. Qual é a diferença entre `_accounts` e `__balance` em Python?
3. Por que anotar `number: int` não impede receber uma string em tempo de execução?
4. Por que o construtor de `Holder` utiliza os setters em vez de atribuir diretamente os atributos?
5. O que deve acontecer com o estado de uma conta quando um saque é recusado?

#### Associações e responsabilidades

6. Por que `Account` não precisa guardar uma referência a `Holder`?
7. Por que `Holder.add_account()` não consegue sozinho garantir a unicidade global dos números?
8. Como o banco distingue um titular registrado de outro objeto com nome e CPF iguais?
9. Qual é a consequência de adicionar contas diretamente pelo titular, ignorando o fluxo pelo banco?
10. Por que chamar essa associação de composição não significa que Python destrói automaticamente todas as contas ao remover uma referência ao titular?

#### Exceções e tratamento de erros

11. Qual é a vantagem de todas as exceções bancárias herdarem de `BankError`?
12. Como diferenciar `InvalidAmountError` de `InsufficientFundsError`?
13. Por que a interface trata `ValueError` separadamente de `BankError`?
14. Por que capturar indiscriminadamente qualquer exceção pode esconder um defeito de programação?
15. Por que um erro ao carregar o JSON não deve ser silenciosamente substituído por um banco vazio?

#### Geradores e coleções

16. O que muda em uma função quando ela contém `yield`?
17. Qual é a diferença entre retornar o dicionário e produzir suas contas com `yield from`?
18. Um gerador de contas fornece cópias dos objetos ou referências aos objetos originais?
19. O que acontece ao tentar percorrer novamente o mesmo gerador depois que ele foi consumido?
20. Qual a vantagem de indexar contas pelo número em um dicionário?

#### Persistência e interfaces

21. Por que `Database.load()` chama `create_holder()` e `add_account()`?
22. Qual é a diferença entre criar uma conta nova e reconstruir uma conta salva com número e saldo existentes?
23. Por que a decisão de quando salvar fica nas interfaces?
24. Se a alteração em memória funcionar e a gravação falhar, qual é o estado da aplicação?
25. Por que exibir `R$ 1.250,50` é tarefa de apresentação, enquanto impedir saldo negativo é tarefa do domínio?

#### Correções e controle da IA

26. Como um saldo em `float` provocou a falha dos saques de 0,10 e 0,20?
27. Por que `Decimal(str(valor))` é diferente de construir `Decimal` diretamente a partir de um `float`?
28. Por que apenas impedir CPF duplicado no cadastro era insuficiente?
29. Como a função de validação fornecida pelo banco preserva a independência de `Holder`?
30. Que diferença entre o prompt e a sugestão do PDF foi identificada em `create_account()`?
31. Por que repetir os mesmos prompts não garante uma implementação idêntica?
32. Por que testes passando não encerram automaticamente uma inspeção visual?

### 4.4. Respostas de referência para conferência

Depois da discussão, compare as respostas da equipe com estes pontos:

- **Encapsulamento:** a API pública direciona mudanças por caminhos que validam o estado. Prefixos de atributos não tornam um objeto inviolável.
- **Associação:** a navegação é titular → contas. A conta não precisa conhecer o titular para depositar ou sacar.
- **Unicidade:** o titular detecta duplicatas locais; o banco tem a visão necessária para detectar duplicatas globais. Ignorar o banco pode contornar essa garantia.
- **Geradores:** produzem elementos sob demanda e são consumidos durante a iteração. Não entregam a coleção interna, mas os objetos produzidos continuam mutáveis pela API pública.
- **Erros:** conversão inválida é problema de entrada; regra recusada é erro do domínio; falha de arquivo é problema de persistência. São situações distintas.
- **Persistência:** reconstruir pelas APIs públicas reaplica validações. Uma falha na gravação não desfaz automaticamente a alteração em memória.
- **Precisão:** `float` utiliza representação binária aproximada. `Decimal(str(valor))` utiliza a representação decimal textual recebida; não recupera informação que já tenha sido perdida em cálculos anteriores com `float`.
- **CPF:** o callback permite ao titular consultar uma regra global sem importar a classe do banco. A validação ocorre antes de alterar o atributo.
- **Engenharia de Prompts:** restrições explícitas, contratos pequenos e testes tornam os resultados revisáveis. A equipe continua responsável por entender e aceitar o código.

### 4.5. Exercícios práticos de revisão

| Exercício | Resultado esperado |
| --- | --- |
| Criar conta 7 e consultar `str(account)` | `0007` |
| Tentar atribuir diretamente à propriedade `balance` | `AttributeError` |
| Depositar zero ou valor negativo | `InvalidAmountError`, sem alteração do saldo |
| Sacar valor superior ao saldo | `InsufficientFundsError`, sem alteração do saldo |
| Cadastrar dois titulares com o mesmo CPF textual | `DuplicateHolderError` |
| Alterar um titular para o CPF de outro do mesmo banco | Exceção e preservação do CPF anterior |
| Adicionar o mesmo número de conta a titulares diferentes pelo banco | `DuplicateAccountError` |
| Criar conta para titular externo ao banco | `HolderNotFoundError` |
| Carregar JSON com conta de saldo negativo | `InvalidDataError` |
| Encerrar e reabrir após um depósito | Mesmo titular, conta e saldo carregados |
| Digitar `25,50` ou `25.50` em uma transação | Conversão aceita nas duas interfaces |
| Digitar texto no campo de valor | Mensagem de entrada inválida, sem alteração |

Realize os exercícios com dados fictícios ou arquivos temporários. Cada integrante deve conseguir localizar a validação correspondente e explicar por que ela está naquela camada.

### 4.6. Critérios para considerar uma etapa compreendida

Antes de avançar, cada integrante deve conseguir:

- Explicar a responsabilidade do módulo sem consultar a IA.
- Identificar suas dependências e os atributos que podem ser alterados.
- Demonstrar uma operação válida e uma operação recusada.
- Explicar as exceções e o estado que permanece após uma falha.
- Conferir se o código corresponde ao contrato do prompt e aos requisitos.
- Executar os testes relevantes e interpretar uma falha.

Se alguém não conseguir explicar uma decisão, a etapa deve ser revisada antes de se acrescentar outra funcionalidade. O objetivo é que a equipe domine tanto o processo de solicitar código quanto o código que aceitou.

## Referências internas

- `app_bank.pdf`: especificação acadêmica do sistema.
- `Critérios_de_avaliação_do_projeto.txt`: critérios e pesos da avaliação.
- `README.md`, na raiz: organização, execução e limitações atuais.
- `tests/`: cenários automatizados que documentam o comportamento esperado.
- `inspecao_interface.md`: resultado da checagem dimensional e limite da inspeção por imagem.
- Histórico desta conversa: origem dos prompts transcritos neste guia.
