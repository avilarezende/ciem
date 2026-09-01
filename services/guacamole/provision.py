"""Geração de user-mapping.xml do Guacamole a partir de config/targets.yaml."""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

# Permite execução direta ou como módulo
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from ciem_common.config_loader import _config_dir, load_auth_config  # noqa: E402
from ciem_common.targets_loader import TargetsConfig, load_targets_config  # noqa: E402

PROTOCOL_MAP = {
    "ssh": "ssh",
    "rdp": "rdp",
    "vnc": "vnc",
}


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _connection_xml(target, credential) -> str:
    protocol = PROTOCOL_MAP.get(target.protocol.lower(), target.protocol.lower())
    lines = [
        f'        <connection name="{_escape(target.name)}">',
        f"            <protocol>{_escape(protocol)}</protocol>",
        f'            <param name="hostname">{_escape(target.hostname)}</param>',
        f'            <param name="port">{target.port}</param>',
    ]

    if credential.username:
        lines.append(f'            <param name="username">{_escape(credential.username)}</param>')
    if credential.password:
        lines.append(f'            <param name="password">{_escape(credential.password)}</param>')
    if credential.ssh_key_path and protocol == "ssh":
        lines.append(
            f'            <param name="private-key">{_escape(credential.ssh_key_path)}</param>'
        )

    # Gravação de sessão (comandos SSH / vídeo RDP)
    lines.append('            <param name="recording-path">/recordings</param>')
    rec_name = "${GUAC_USERNAME}_${GUAC_DATE}_${GUAC_TIME}"
    lines.append(f'            <param name="recording-name">{rec_name}</param>')
    if protocol == "ssh":
        lines.append('            <param name="typescript-path">/recordings</param>')
        lines.append(f'            <param name="typescript-name">{rec_name}</param>')
        lines.append('            <param name="create-typescript-path">true</param>')

    lines.append("        </connection>")
    return "\n".join(lines)


def generate_user_mapping(
    targets_cfg: TargetsConfig | None = None,
    *,
    include_observers: bool = False,
) -> str:
    """Gera XML de user-mapping para guacamole-auth-file.

    Administradores CIEM recebem acesso a todos os alvos habilitados.
    Observadores recebem acesso somente leitura se ``include_observers=True``.
    """
    targets_cfg = targets_cfg or load_targets_config()
    auth_cfg = load_auth_config()
    enabled = targets_cfg.enabled_targets()

    connections = []
    for target in enabled:
        cred = targets_cfg.credential_for(target.id)
        connections.append(_connection_xml(target, cred))

    connections_block = (
        "\n".join(connections) if connections else "        <!-- Nenhum alvo habilitado -->"
    )

    users_xml: list[str] = []
    for user in auth_cfg.local_users:
        if not user.enabled:
            continue
        if user.role == "observer" and not include_observers:
            continue
        # Senha vazia = delegada ao proxy CIEM (SSO futuro); use hash ou env em produção
        users_xml.append(
            f'    <authorize username="{_escape(user.username)}" password="">'
            f"\n{connections_block}\n    </authorize>"
        )

    if not users_xml:
        users_xml.append(
            f'    <authorize username="guacadmin" password="">\n'
            f"{connections_block}\n    </authorize>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<user-mapping>\n'
        + "\n".join(users_xml)
        + "\n</user-mapping>\n"
    )


def generate_guacamole_properties() -> str:
    return "\n".join(
        [
            "guacd-hostname: guacd",
            "guacd-port: 4822",
            # SSO: autentica via header X-CIEM-User (definido pelo proxy após validação CIEM)
            (
                "auth-provider: "
                "net.sourceforge.guacamole.net.auth.header.HttpHeaderAuthenticationProvider"
            ),
            "http-auth-header.header: X-CIEM-User",
            # Conexões definidas em user-mapping.xml (extensão auth-file complementar)
            "user-mapping: /etc/guacamole/user-mapping.xml",
            "enable-websocket: true",
            "api-session-timeout: 60",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Provisiona Guacamole a partir de targets.yaml")
    parser.add_argument(
        "--config-path",
        default=str(_config_dir()),
        help="Diretório com targets.yaml (padrão: CONFIG_PATH)",
    )
    parser.add_argument(
        "--output",
        default="/etc/guacamole/user-mapping.xml",
        help="Caminho do user-mapping.xml gerado",
    )
    parser.add_argument(
        "--properties-output",
        default="/etc/guacamole/guacamole.properties",
        help="Caminho do guacamole.properties",
    )
    parser.add_argument(
        "--include-observers",
        action="store_true",
        help="Incluir observadores CIEM como usuários Guacamole",
    )
    args = parser.parse_args()

    import os

    os.environ["CONFIG_PATH"] = args.config_path

    from ciem_common.config_loader import clear_config_cache
    from ciem_common.targets_loader import clear_targets_cache

    clear_config_cache()
    clear_targets_cache()

    mapping = generate_user_mapping(include_observers=args.include_observers)
    properties = generate_guacamole_properties()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(mapping, encoding="utf-8")

    props = Path(args.properties_output)
    props.parent.mkdir(parents=True, exist_ok=True)
    props.write_text(properties, encoding="utf-8")

    targets = load_targets_config().enabled_targets()
    print(f"Guacamole provisionado: {len(targets)} alvo(s) → {output}")


if __name__ == "__main__":
    main()
