"""Geração dos valores simulados de ruído."""

import random

def generate_noise() -> float:
    """
    Gera uma medição simples de ruído em decibéis.
    Neste primeiro estágio a geração é propositalmente simples.
    O comportamento realista será implementado posteriormente.
    """

    return round(random.uniform(40.0, 80.0), 2)
