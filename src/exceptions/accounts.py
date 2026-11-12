

class SomethingWentWrong(Exception):
    pass


class UserEmailAlreadyExist(Exception):
    pass


class GroupDoesNotExist(SomethingWentWrong):
    pass
