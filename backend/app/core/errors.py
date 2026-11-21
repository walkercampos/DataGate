"""Erros de negócio: mensagem pensada para o usuário final, sem detalhes internos."""


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NaoEncontrado(AppError):
    status_code = 404


class Conflito(AppError):
    status_code = 409


class NaoAutorizado(AppError):
    status_code = 401


class Proibido(AppError):
    status_code = 403
