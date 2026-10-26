"""Conta bancária: estado e regras de negócio, sem entrada/saída ou arquivos."""

from decimal import Decimal, localcontext
from math import isfinite

from .exceptions import (
    InsufficientFundsError,
    InvalidAmountError,
    InvalidDataError,
)


class Account:
    """Encapsula o número da conta e as operações que podem alterar seu saldo."""

    def __init__(self, number: int, balance: float = 0.0):
        # Anotações de tipo não validam valores em tempo de execução.
        # bool também é um int em Python, mas não representa um número de conta.
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise InvalidDataError("O número da conta deve ser um inteiro positivo.")

        if isinstance(balance, bool) or not isinstance(balance, (int, float)):
            raise InvalidDataError("O saldo inicial deve ser um número finito não negativo.")

        try:
            initial_balance = float(balance)
        except OverflowError as error:
            raise InvalidDataError("O saldo inicial é grande demais.") from error

        # NaN e infinito não são saldos válidos, mesmo que não sejam negativos.
        if not isfinite(initial_balance) or initial_balance < 0:
            raise InvalidDataError("O saldo inicial deve ser um número finito não negativo.")

        # O prefixo __ aplica name mangling e evita acesso acidental ao estado.
        # A validação vem antes da atribuição: toda conta nasce válida.
        self.__number = number
        # Converter pelo texto evita carregar a aproximação binária do float.
        self.__balance = Decimal(str(balance))

    @property
    def number(self) -> int:
        """Permite consultar o número, sem oferecer um setter para alterá-lo."""
        return self.__number

    @property
    def balance(self) -> float:
        """Permite consultar o saldo; alterações passam por depósito ou saque."""
        # Mantém o contrato público e a compatibilidade com os números do JSON.
        return float(self.__balance)

    @staticmethod
    def __validate_amount(amount: float) -> Decimal:
        """Centraliza a mesma regra usada pelas duas operações."""
        # É estático porque a validação do valor não precisa acessar a conta.
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise InvalidAmountError("O valor deve ser um número finito positivo.")

        try:
            value = float(amount)
        except OverflowError as error:
            raise InvalidAmountError("O valor informado é grande demais.") from error

        if not isfinite(value) or value <= 0:
            raise InvalidAmountError("O valor deve ser um número finito positivo.")
        return Decimal(str(amount))

    def __calculate_balance(self, value: Decimal, *, subtract: bool = False) -> Decimal:
        """Calcula sem perder casas decimais, inclusive com valores de escalas distintas."""
        # O contexto padrão de Decimal tem precisão limitada. Ajustamos apenas
        # esta operação, reservando espaço para todos os dígitos e um transporte.
        highest_digit = max(self.__balance.adjusted(), value.adjusted())
        lowest_digit = min(
            self.__balance.as_tuple().exponent, value.as_tuple().exponent
        )
        with localcontext() as context:
            context.prec = max(28, highest_digit - lowest_digit + 2)
            if subtract:
                return self.__balance - value
            return self.__balance + value

    def deposit(self, amount: float) -> None:
        """Acrescenta um valor positivo ao saldo."""
        value = self.__validate_amount(amount)
        new_balance = self.__calculate_balance(value)
        if not isfinite(float(new_balance)):
            raise InvalidAmountError("O depósito ultrapassa o limite numérico do saldo.")
        self.__balance = new_balance

    def withdraw(self, amount: float) -> None:
        """Retira um valor positivo, desde que haja saldo suficiente."""
        value = self.__validate_amount(amount)
        if value > self.__balance:
            # A exceção específica explica a falha sem depender de uma tela.
            # O saldo ainda não foi alterado quando o erro é lançado.
            raise InsufficientFundsError("Saldo insuficiente para realizar o saque.")
        self.__balance = self.__calculate_balance(value, subtract=True)

    def __str__(self) -> str:
        """Define a representação textual com, no mínimo, quatro dígitos."""
        return f"{self.__number:04d}"
