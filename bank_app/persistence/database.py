"""Salva e reconstrói o banco em JSON usando a API pública do modelo."""

import json
from pathlib import Path

from ..domain.account import Account
from ..domain.bank import Bank


# Caminho estável: não depende da pasta de onde a aplicação foi executada.
DEFAULT_PATH = Path(__file__).resolve().with_name("bank.json")


class Database:
    """Converte o estado do banco para JSON e reconstrói seus objetos."""

    def __init__(self, path: Path = DEFAULT_PATH):
        self.__path = Path(path)

    @property
    def path(self) -> Path:
        """Permite consultar o caminho sem alterá-lo diretamente."""
        return self.__path

    def load(self) -> Bank:
        """Carrega o banco ou retorna um banco vazio se o arquivo não existir."""
        try:
            with self.__path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return Bank()

        bank = Bank()
        for holder_data in data:
            # Não escreve em atributos privados: o cadastro valida nome e CPF,
            # incluindo a unicidade do CPF entre os titulares carregados.
            holder = bank.create_holder(holder_data["name"], holder_data["cpf"])
            for account_data in holder_data["accounts"]:
                # Account valida número e saldo. Bank valida a unicidade global.
                account = Account(account_data["number"], account_data["balance"])
                bank.add_account(holder, account)
        return bank

    def save(self, bank: Bank) -> None:
        """Grava o estado atual completo, substituindo o conteúdo anterior."""
        # A leitura também usa a API pública: propriedades e geradores.
        data = [
            {
                "name": holder.name,
                "cpf": holder.cpf,
                "accounts": [
                    {"number": account.number, "balance": account.balance}
                    for account in holder.accounts()
                ],
            }
            for holder in bank.holders()
        ]
        with self.__path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
