

class SomethingWentWrong(Exception):
    pass


class UserEmailAlreadyExist(Exception):
    pass


class UserWithEmailDoesNotExist(Exception):
    pass


class GroupDoesNotExist(SomethingWentWrong):
    pass


class ProfileDoesNotExist(Exception):
    pass


class InvalidActivationToken(Exception):
    pass


class ActivationTokenExpired(Exception):
    pass


class AccountAlreadyActive(Exception):
    pass


class AccountNotActive(Exception):
    pass


class InvalidJWTToken(Exception):
    pass


class ExpiredJWTToken(Exception):
    pass


class InvalidUserCredentials(Exception):
    pass


class WrongOldPassword(Exception):
    pass


class InvalidPasswordResetToken(Exception):
    pass


class PasswordResetTokenExpired(Exception):
    pass
