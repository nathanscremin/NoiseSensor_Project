"""Responsável pela conexão com o PostgreSQL."""

import os
import psycopg
from dotenv import load_dotenv

# Carrega as variáveis definidas no arquivo .env.
load_dotenv()

def create_connection() -> psycopg.Connection:
    """
    Cria uma conexão com o PostgreSQL usando as configurações
    definidas nas variáveis de ambiente.
    """

    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
