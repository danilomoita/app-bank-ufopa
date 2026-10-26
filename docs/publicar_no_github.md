# Publicar o App Bank no GitHub

Este roteiro usa o repositório `danilomoita/app-bank-ufopa` e a branch `main`.
Os comandos da primeira publicação pressupõem uma pasta sem repositório Git
inicializado e um repositório remoto vazio. Se o projeto já tiver commits ou
remoto configurado, confira o estado existente antes de repetir a preparação.

## 1. Conferir ferramentas

```shell
git --version
python --version
```

No Windows, se necessário, substitua `python` por `py -3`. Git deve estar
instalado e disponível no PATH; se acabou de instalá-lo, reabra o terminal.

## 2. Criar o repositório remoto vazio

No GitHub, crie um repositório chamado **app-bank-ufopa**, na conta
**danilomoita**, com visibilidade **pública**, conforme definido para o projeto.
Como README e `.gitignore` já existem localmente, não inicialize o remoto
com README, `.gitignore` ou licença nessa etapa. Isso evita históricos iniciais
independentes.

Não é preciso criar outro repositório se ele já foi publicado. Nesse caso,
use o fluxo de atualização da seção 7.

## 3. Acessar a pasta local

Abra um terminal na pasta que contém `bank_app/`, `docs/`, `tests/` e README.
Para o caminho atual no Windows/PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\USER\Desktop\UFOPA - B.I.A\2 SEMESTRE\POO EM PYTHON\POO - App Bank (UFOPA)'
```

## 4. Inicializar e configurar a autoria

```shell
git init
git branch -M main
git config user.name "danilomoita"
git config user.email "136601200+danilomoita@users.noreply.github.com"
```

O nome pode ser substituído pelo nome de exibição desejado. O endereço
`noreply` identifica a conta sem publicar o e-mail pessoal. As configurações
acima valem somente para este repositório; não alteram a configuração global.
Configurar autoria não autentica o envio ao GitHub.

## 5. Conferir e criar o primeiro commit

```shell
git status --short --untracked-files=all
git check-ignore bank_app/persistence/bank.json
python -B -m unittest discover -s tests -v
git add .
git diff --cached --stat
git diff --cached --name-only
git commit -m "feat: implementa App Bank com dominio, JSON, terminal e GUI"
```

Antes do commit, confira se os arquivos adicionados são código, testes e
documentação. `bank.json`, ambientes virtuais, caches e configurações pessoais
devem ficar de fora. Se um arquivo já estiver versionado, adicioná-lo ao
`.gitignore` não o remove automaticamente do histórico.

Os testes gráficos exigem Tkinter e uma sessão gráfica disponível. Não há
instalação de pacotes externos para executar o projeto ou os testes.

## 6. Conectar e enviar

```shell
git remote add origin https://github.com/danilomoita/app-bank-ufopa.git
git remote -v
git push -u origin main
```

`origin` identifica o remoto. `-u` associa a branch local à remota para
permitir os próximos envios com `git push`.

Se `origin` já existir, confira a URL; não repita `remote add`. Quando for
realmente necessário ajustar o destino:

```shell
git remote set-url origin https://github.com/danilomoita/app-bank-ufopa.git
```

A conexão do GitHub no aplicativo, a sessão do navegador e as credenciais do
Git local são acessos distintos. Se o Git solicitar autenticação, conclua o
fluxo do Git Credential Manager no navegador. A senha da conta não é aceita
como senha para operações Git por HTTPS. Não coloque tokens em comandos,
arquivos do projeto ou URLs do remoto.

## 7. Atualizações posteriores

```shell
git status
git add .
git diff --cached --stat
git commit -m "docs: atualiza orientacoes do projeto"
git push
```

Para compartilhar mudanças de código com revisão da equipe:

```shell
git switch -c melhoria-descricao
# Edite os arquivos e execute os testes.
git add .
git commit -m "feat: descreve a melhoria"
git push -u origin melhoria-descricao
```

Depois, abra um pull request para `main`. Escolha um nome de branch e uma
mensagem de commit que descrevam a alteração efetivamente realizada.

## 8. Clonar para o professor ou equipe

```shell
git clone https://github.com/danilomoita/app-bank-ufopa.git
cd app-bank-ufopa
python -m bank_app.interfaces.bank_terminal
```

Para abrir a GUI, encerre o terminal do banco e execute:

```shell
python -m bank_app.interfaces.bank_gui
```

Não copie o ambiente virtual de outro computador. O projeto usa somente a
biblioteca padrão e cada clone cria seu próprio `bank.json` ao salvar.

## Referências oficiais

- [Publicar código local no GitHub](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)
- [Credenciais do Git e Git Credential Manager](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git)
- [Autenticação para operações Git por HTTPS](https://docs.github.com/en/get-started/git-basics/why-is-git-always-asking-for-my-credentials)
