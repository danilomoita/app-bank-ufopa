"""Menus de terminal: entrada, apresentação e coordenação das operações."""

from collections.abc import Callable
from typing import TypeVar

from ..domain.account import Account
from ..domain.bank import Bank
from ..domain.exceptions import BankError
from ..domain.holder import Holder
from ..persistence.database import Database


# TypeVar permite reutilizar choose para titulares, contas ou outros objetos.
T = TypeVar("T")


class BankTerminal:
    """Apresenta o banco sem implementar regras de negócio ou acessar arquivos."""

    def __init__(self, bank: Bank, database: Database):
        # Injeção de dependência: quem inicia a aplicação fornece os objetos.
        # O construtor não carrega arquivos nem cria outro cadastro.
        self.bank = bank
        self.database = database
        self._unsaved_changes = False

    def choose(self, items: list[T]) -> T | None:
        """Retorna o objeto escolhido, ou None para lista vazia/cancelamento/erro."""
        if not items:
            print("Nenhum item encontrado.")
            return None

        for index, item in enumerate(items, start=1):
            # Rótulos pertencem à apresentação; não alteram os objetos do modelo.
            if isinstance(item, Holder):
                label = f"{item.name} — CPF: {item.cpf}"
            elif isinstance(item, Account):
                label = f"Conta {item} — Saldo: R$ {item.balance:.2f}"
            else:
                label = str(item)
            print(f"{index}. {label}")

        text = input("Escolha um item (Enter para voltar): ").strip()
        if not text:
            return None
        try:
            index = int(text)
        except ValueError:
            print("Escolha inválida. Digite um valor numérico inteiro.")
            return None
        if not 1 <= index <= len(items):
            print("Escolha inválida.")
            return None
        return items[index - 1]

    def save(self) -> bool:
        """Solicita a gravação à persistência e informa se ela foi concluída."""
        try:
            self.database.save(self.bank)
        except OSError as error:
            self._unsaved_changes = True
            print(f"A alteração não foi salva: {error}")
            print("Os dados estão em memória. Use 'Salvar novamente' antes de sair.")
            return False
        self._unsaved_changes = False
        return True

    def _execute_change(self, operation: Callable[[], object], message: str) -> None:
        """Executa uma alteração e salva somente se a operação for aceita."""
        try:
            operation()
        except BankError as error:
            # O modelo fornece a mensagem e decide quais operações são válidas.
            print(f"Erro do banco: {error}")
        except ValueError:
            # Conversão da entrada é responsabilidade da interface, não do modelo.
            print("Digite um valor numérico válido.")
        else:
            self._unsaved_changes = True
            if self.save():
                print(message)

    def run(self) -> None:
        """Mantém o menu principal ativo até a saída ou interrupção da entrada."""
        try:
            while True:
                print("\n=== Banco App ===")
                print("1. Cadastrar titular")
                print("2. Buscar titular")
                print("3. Salvar novamente")
                print("0. Sair")
                option = input("Opção: ").strip()
                if option == "1":
                    self.create_holder_screen()
                elif option == "2":
                    self.search_holder_screen()
                elif option == "3":
                    if self.save():
                        print("Dados salvos.")
                elif option == "0":
                    if self._unsaved_changes and not self.save():
                        continue
                    print("Até logo!")
                    return
                else:
                    print("Opção inválida.")
        except (EOFError, KeyboardInterrupt):
            # Encerra sem traceback; tenta preservar alterações ainda pendentes.
            print("\nEntrada encerrada.")
            if self._unsaved_changes and not self.save():
                print("Atenção: as alterações em memória serão perdidas ao encerrar.")

    def create_holder_screen(self) -> None:
        """Captura os campos e delega ao banco o cadastro e suas validações."""
        name = input("Nome: ")
        cpf = input("CPF: ")
        self._execute_change(
            lambda: self.bank.create_holder(name, cpf),
            "Titular cadastrado e dados salvos.",
        )

    def search_holder_screen(self) -> None:
        """Pesquisa pelo gerador do modelo; texto vazio produz todos os titulares."""
        name = input("Parte do nome (Enter para listar todos): ")
        holder = self.choose(list(self.bank.filter_by_name(name)))
        if holder is not None:
            self.holder_menu(holder)

    def holder_menu(self, holder: Holder) -> None:
        """Exibe as operações disponíveis para o titular selecionado."""
        while True:
            print(f"\n=== Titular: {holder.name} — CPF: {holder.cpf} ===")
            print("1. Listar contas e selecionar uma conta")
            print("2. Criar conta")
            print("3. Excluir conta pelo número")
            print("0. Voltar")
            option = input("Opção: ").strip()
            if option == "1":
                self.list_accounts_screen(holder)
            elif option == "2":
                self._execute_change(
                    lambda: self.bank.create_account(holder),
                    "Conta criada e dados salvos.",
                )
            elif option == "3":
                self.delete_account_screen(holder)
            elif option == "0":
                return
            else:
                print("Opção inválida.")

    def list_accounts_screen(self, holder: Holder) -> None:
        """Lista as contas e abre o menu da conta selecionada."""
        account = self.choose(list(holder.accounts()))
        if account is not None:
            self.account_menu(account)

    def delete_account_screen(self, holder: Holder) -> None:
        """Converte o número digitado e solicita a exclusão ao titular."""
        text = input("Número da conta a excluir: ")
        self._execute_change(
            lambda: holder.delete_account(int(text)),
            "Conta excluída e dados salvos.",
        )

    def account_menu(self, account: Account) -> None:
        """Exibe saldo e oferece depósito ou saque, sem calcular valores."""
        while True:
            print(f"\n=== Conta {account} — Saldo: R$ {account.balance:.2f} ===")
            print("1. Depositar")
            print("2. Sacar")
            print("0. Voltar")
            option = input("Opção: ").strip()
            if option == "1":
                self.transaction_screen(account.deposit, "Depósito")
            elif option == "2":
                self.transaction_screen(account.withdraw, "Saque")
            elif option == "0":
                return
            else:
                print("Opção inválida.")

    def transaction_screen(self, operation: Callable[[float], None], label: str) -> None:
        """Converte o valor e chama o método recebido, seja depósito ou saque."""
        text = input(f"{label} — valor: ").strip()
        self._execute_change(
            lambda: operation(float(text.replace(",", "."))),
            f"{label} realizado e dados salvos.",
        )


def main() -> int:
    """Monta as dependências e inicia o terminal com os dados carregados."""
    database = Database()
    try:
        bank = database.load()
    except (BankError, OSError, ValueError, TypeError, KeyError) as error:
        # Nunca troca silenciosamente um arquivo inválido por um banco vazio.
        print(f"Não foi possível carregar o banco: {error}")
        return 1
    BankTerminal(bank, database).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
