from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./banco_dados.db"

engine = create_async_engine(DATABASE_URL, echo=True)

# Criando sessão assíncrona com nome compatível com main.py
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Função para injetar sessão nas rotas
async def get_db():
    async with async_session() as session:
        yield session