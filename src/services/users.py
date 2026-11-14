from database.models import UserGroupEnum, User


def is_regular_user(user: User) -> bool:
    """
    Check whether the user belongs to the regular user group.

    Requires the user's group relationship to be loaded.
    """
    return user.group.name == UserGroupEnum.USER
