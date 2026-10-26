"""Cadastro central de titulares e controle global dos números de conta."""

from collections.abc import Generator

from .account import Account
from .exceptions import (
    DuplicateAccountError,
    DuplicateHolderError,
    HolderNotFoundError,
    InvalidDataError,
)
from .holder import Holder


class Bank:
    """Coordena os titulares e as contas sem depender de interfaces ou arquivos."""

    def __init__(self):
        self.__holders: list[Holder] = []

    def create_holder(self, name: str, cpf: str) -> Holder:
        """Valida e cadastra um titular, rejeitando um CPF já cadastrado."""
        # Holder valida os campos e remove espaços nas extremidades.
        # A comparação usa o CPF já tratado para não aceitar duplicatas por espaços.
        holder = Holder(name, cpf, cpf_validator=self.__validate_holder_cpf)
        self.__holders.append(holder)
        return holder

    def __validate_holder_cpf(self, holder: Holder, cpf: str) -> None:
        """Valida a unicidade tanto no cadastro quanto nas alterações pelo setter."""
        if any(
            existing is not holder and existing.cpf == cpf
            for existing in self.__holders
        ):
            raise DuplicateHolderError("Já existe um titular com o CPF informado.")

    def _next_account_number(self) -> int:
        """Calcula o maior número atual mais um, ou 1 quando não há contas."""
        # O prefixo _ identifica um método interno por convenção em Python.
        numbers = (
            account.number
            for holder in self.__holders
            for account in holder.accounts()
        )
        return max(numbers, default=0) + 1

    def create_account(self, holder: Holder) -> Holder:
        """Cria uma conta com saldo zero e retorna o titular que a recebeu."""
        account = Account(self._next_account_number())
        # Toda inclusão passa pela mesma verificação global de add_account.
        self.add_account(holder, account)
        return holder

    def add_account(self, holder: Holder, account: Account) -> None:
        """Inclui uma conta existente, garantindo titular válido e número único."""
        # Mesmo nome e CPF não bastam: deve ser o próprio objeto cadastrado.
        if not any(existing is holder for existing in self.__holders):
            raise HolderNotFoundError("O titular informado não pertence a este banco.")
        if not isinstance(account, Account):
            raise InvalidDataError("A conta informada deve ser uma instância de Account.")
        if any(
            existing.number == account.number
            for registered_holder in self.__holders
            for existing in registered_holder.accounts()
        ):
            raise DuplicateAccountError(
                f"Já existe uma conta com o número {account.number:04d} neste banco."
            )
        holder.add_account(account)

    def holders(self) -> Generator[Holder, None, None]:
        """Produz os titulares sem expor a lista interna."""
        yield from self.__holders

    def filter_by_name(self, name: str) -> Generator[Holder, None, None]:
        """Produz titulares cujo nome contém o texto, sem distinguir maiúsculas."""
        search = name.casefold()
        for holder in self.__holders:
            if search in holder.name.casefold():
                yield holder
