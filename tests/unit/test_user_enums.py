from database.models import GenderEnum, UserGroupEnum


def test_user_group_values():
    assert {g.value for g in UserGroupEnum} == {"user", "moderator", "admin"}


def test_gender_values():
    assert {g.value for g in GenderEnum} == {"man", "woman"}
