import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

# -----------------------------
# Configurações de segurança
# -----------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "chave_dev_insegura")  # 🔐 usar variável de ambiente em produção
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -----------------------------
# Funções utilitárias
# -----------------------------
def hash_password(password: str) -> str:
    """Gera um hash seguro para a senha do usuário."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token JWT com tempo de expiração."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodifica e valida um token JWT, verificando expiração e integridade."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
