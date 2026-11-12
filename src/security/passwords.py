from pwdlib import PasswordHash


pass_hash = PasswordHash.recommended()

def hash_password(raw_password: str) -> str:
    return pass_hash.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pass_hash.verify(raw_password, hashed_password)
