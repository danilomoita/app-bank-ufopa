"""Titular e suas contas, sem dependência de interfaces ou persistência."""

from __future__ import annotations

from collections.abc import Callable, Generator

from .account import Account
from .exceptions import (
    AccountNotFoundError,
    DuplicateAccountError,
    InvalidDataError,
)


class Holder:
    """Representa um titular e permite navegar dele para suas contas."""

    def __init__(
        self,
        name: str,
        cpf: str,
        *,
        cpf_validator: Callable[[Holder, str], None] | None = None,
    ):
        # Uma função fornecida pelo banco verifica a unicidade global.
        # Holder não precisa importar Bank nem conhecer seu cadastro.
        self.__cpf_validator = cpf_validator
        # Os setters garantem as mesmas validações na criação e na alteração.
        self.name = name
        self.cpf = cpf
        # O prefixo _ indica uso interno por convenção em Python.
        # Cada titular possui seu próprio dicionário, indexado pelo número.
        self._accounts: dict[int, Account] = {}

    @property
    def name(self) -> str:
        """Nome do titular."""
        return self.__name

    @name.setter
    def name(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise InvalidDataError("O nome do titular é obrigatório e deve ser um texto.")
        self.__name = value.strip()

    @property
    def cpf(self) -> str:
        """CPF do titular, preservando sua formatação."""
        return self.__cpf

    @cpf.setter
    def cpf(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise InvalidDataError("O CPF do titular é obrigatório e deve ser um texto.")
        cpf = value.strip()
        if self.__cpf_validator is not None:
            self.__cpf_validator(self, cpf)
        # Só altera o estado depois que todas as validações tiverem passado.
        self.__cpf = cpf

    def add_account(self, account: Account) -> None:
        """Adiciona uma conta sem substituir outra com o mesmo número."""
        if not isinstance(account, Account):
            raise InvalidDataError("A conta informada deve ser uma instância de Account.")
        if account.number in self._accounts:
            raise DuplicateAccountError(
                f"O titular já possui a conta {account.number:04d}."
            )
        # A unicidade dos números entre titulares será responsabilidade de Bank.
        self._accounts[account.number] = account

    def delete_account(self, account_number: int) -> None:
        """Exclui uma conta do titular ou informa que ela não existe."""
        if account_number not in self._accounts:
            raise AccountNotFoundError(
                f"O titular não possui a conta de número {account_number}."
            )
        del self._accounts[account_number]

    def get_account(self, account_number: int) -> Account:
        """Busca a conta diretamente pela chave do dicionário."""
        if account_number not in self._accounts:
            raise AccountNotFoundError(
                f"O titular não possui a conta de número {account_number}."
            )
        return self._accounts[account_number]

    def accounts(self) -> Generator[Account, None, None]:
        """Produz as contas uma a uma, sem devolver o dicionário interno."""
        yield from self._accounts.values()
