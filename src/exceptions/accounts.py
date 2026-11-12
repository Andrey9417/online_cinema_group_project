

class SomethingWentWrong(Exception):
    pass


class UserEmailAlreadyExist(Exception):
    pass


class GroupDoesNotExist(SomethingWentWrong):
    pass


class InvalidActivationToken(Exception):
    pass


class ActivationTokenExpired(Exception):
    pass


class AccountAlreadyActive(Exception):
    pass
