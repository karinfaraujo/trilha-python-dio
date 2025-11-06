from pydantic import BaseModel
from datetime import datetime

# -----------------------------
# Usuário
# -----------------------------
class UsuarioCreate(BaseModel):
    """Schema para criação de um novo usuário."""
    username: str
    password: str


class UsuarioResponse(BaseModel):
    """Schema de resposta de um usuário."""
    id: int
    username: str

    class Config:
        orm_mode = True


# -----------------------------
# Conta
# -----------------------------
class AccountResponse(BaseModel):
    """Schema de resposta de uma conta bancária."""
    id: int
    user_id: int
    balance: float

    class Config:
        orm_mode = True


# -----------------------------
# Transação
# -----------------------------
class TransactionCreate(BaseModel):
    """Schema para criação de uma transação (depósito ou saque)."""
    account_id: int
    amount: float
    type: str  # 'deposit' ou 'withdrawal'


class TransactionResponse(BaseModel):
    """Schema de resposta de uma transação."""
    id: int
    account_id: int
    amount: float
    type: str
    timestamp: datetime  

    class Config:
        orm_mode = True
