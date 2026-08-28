"""Testes do carregador de clientes."""

from app.config_loader import find_institution, get_clients


def test_get_clients_not_empty():
    clients = get_clients()
    assert len(clients) >= 1


def test_find_institution_by_sigla():
    inst = find_institution("IFS")
    assert inst is not None
    assert inst["sigla"] == "IFS"


def test_find_institution_by_alias():
    inst = find_institution("sou do instituto federal sergipe")
    assert inst is not None
    assert inst["sigla"] == "IFS"
