from enum import StrEnum


class PgErrorCode(StrEnum):
    UNIQUE_VIOLATION = "23505"
    FOREIGN_KEY_VIOLATION = "23503"
    NOT_NULL_VIOLATION = "23502"
    CHECK_VIOLATION = "23514"


class CartBaseError(Exception):
    pass


class DBError(CartBaseError):
    pass


class EntityNotFound(DBError):
    pass


class EntityAlreadyExists(DBError):
    pass
