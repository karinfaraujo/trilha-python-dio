from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from datetime import datetime, timezone
from typing import List

from models import Base, Usuario, Account, Transaction
from schemas import (
    UsuarioCreate,
    UsuarioResponse,
    AccountResponse,
    TransactionCreate,
    TransactionResponse,
)
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

# -----------------------------
# Configuração do Banco de Dados
# -----------------------------
DATABASE_URL = "sqlite+aiosqlite:///./banco_dados.db"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def criar_tabelas():
    """Cria as tabelas no banco de dados na inicialização."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# -----------------------------
# Inicialização da Aplicação
# -----------------------------
app = FastAPI(title="API Bancária Assíncrona com FastAPI")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@app.on_event("startup")
async def on_startup():
    """Cria as tabelas automaticamente ao iniciar a aplicação."""
    await criar_tabelas()


# -----------------------------
# Dependência: Usuário atual
# -----------------------------
async def get_current_user(token: str = Depends(oauth2_scheme)) -> int:
    """Retorna o ID do usuário autenticado a partir do token JWT."""
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


# -----------------------------
# Rotas de Usuários
# -----------------------------
@app.post("/usuarios/", response_model=UsuarioResponse)
async def criar_usuario(usuario: UsuarioCreate):
    async with async_session() as session:
        result = await session.execute(
            select(Usuario).where(Usuario.username == usuario.username)
        )
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Usuário já existe")

        novo_usuario = Usuario(
            username=usuario.username, password=hash_password(usuario.password)
        )
        session.add(novo_usuario)
        await session.commit()
        await session.refresh(novo_usuario)

        # Cria conta automaticamente ao registrar usuário
        conta = Account(user_id=novo_usuario.id, balance=0.0)
        session.add(conta)
        await session.commit()
        await session.refresh(conta)

        return novo_usuario


@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    async with async_session() as session:
        result = await session.execute(
            select(Usuario).where(Usuario.username == form_data.username)
        )
        usuario = result.scalars().first()
        if not usuario or not verify_password(form_data.password, usuario.password):
            raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

        token = create_access_token({"sub": str(usuario.id)})
        return {"access_token": token, "token_type": "bearer"}


# -----------------------------
# Rotas de Contas
# -----------------------------
@app.post("/contas/", response_model=AccountResponse)
async def criar_conta(current_user: int = Depends(get_current_user)):
    async with async_session() as session:
        nova_conta = Account(user_id=current_user, balance=0.0)
        session.add(nova_conta)
        await session.commit()
        await session.refresh(nova_conta)
        return nova_conta


# -----------------------------
# Rotas de Transações
# -----------------------------
@app.post("/transacoes/", response_model=TransactionResponse)
async def criar_transacao(
    transacao: TransactionCreate, current_user: int = Depends(get_current_user)
):
    async with async_session() as session:
        result = await session.execute(
            select(Account).where(Account.id == transacao.account_id)
        )
        conta = result.scalars().first()

        if not conta or conta.user_id != current_user:
            raise HTTPException(status_code=403, detail="Não autorizado")

        if transacao.amount <= 0:
            raise HTTPException(status_code=400, detail="O valor deve ser positivo")

        if transacao.type not in {"deposit", "withdrawal"}:
            raise HTTPException(status_code=400, detail="Tipo de transação inválido")

        if transacao.type == "withdrawal" and transacao.amount > conta.balance:
            raise HTTPException(status_code=400, detail="Saldo insuficiente")

        # Atualiza saldo da conta
        conta.balance += transacao.amount if transacao.type == "deposit" else -transacao.amount

        # Cria a transação
        nova_transacao = Transaction(
            account_id=conta.id,
            amount=transacao.amount,
            type=transacao.type,
            timestamp=datetime.now(timezone.utc),
        )

        session.add(nova_transacao)
        await session.commit()
        await session.refresh(nova_transacao)
        await session.refresh(conta)

        return nova_transacao


# -----------------------------
# Rotas de Extrato
# -----------------------------
@app.get("/contas/{user_id}/extrato", response_model=List[TransactionResponse])
async def extrato(user_id: int, current_user: int = Depends(get_current_user)):
    """Retorna o extrato (todas as transações) de todas as contas do usuário."""
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="Não autorizado")

    async with async_session() as session:
        result = await session.execute(select(Account.id).where(Account.user_id == user_id))
        account_ids = [row[0] for row in result.all()]

        if not account_ids:
            raise HTTPException(status_code=404, detail="Nenhuma conta encontrada")

        result = await session.execute(
            select(Transaction).where(Transaction.account_id.in_(account_ids))
        )
        transacoes = result.scalars().all()
        return transacoes
