import os
from collections import OrderedDict

import click
import yaml
from flask.cli import with_appcontext

from app.app import db
from app.con_sqlalchemy import Module, Permission, Role, RolePermission, User
from app.utils import hash_bcrypt


DEFAULT_SEED_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "seeds",
    "permissions.yml",
)


def _ordered_dump(data, stream=None, **kwargs):
    class _Dumper(yaml.SafeDumper):
        pass

    def _dict_repr(dumper, d):
        return dumper.represent_mapping("tag:yaml.org,2002:map", d.items())

    _Dumper.add_representer(OrderedDict, _dict_repr)
    return yaml.dump(data, stream, Dumper=_Dumper, sort_keys=False, **kwargs)


def _export_to_dict():
    modules = db.session.query(Module).order_by(Module.level, Module.sort_order, Module.module_id).all()
    id_to_code = {m.module_id: m.module_code for m in modules}

    out = []
    for m in modules:
        perms = (
            db.session.query(Permission)
            .filter(Permission.module_id == m.module_id)
            .order_by(Permission.method)
            .all()
        )
        entry = OrderedDict()
        entry["code"] = m.module_code
        entry["name"] = m.module_name
        entry["parent_code"] = id_to_code.get(m.parent_id) if m.parent_id else None
        entry["level"] = m.level
        entry["sort_order"] = m.sort_order
        entry["permissions"] = [
            OrderedDict(
                [
                    ("method", p.method),
                    ("code", p.permission_code),
                    ("description", p.description),
                ]
            )
            for p in perms
        ]
        out.append(entry)
    return {"modules": out}


def _apply_from_dict(payload, prune=False):
    modules = payload.get("modules", []) or []

    yml_module_codes = {m["code"] for m in modules}
    existing = {m.module_code: m for m in db.session.query(Module).all()}

    code_to_module = {}
    for entry in modules:
        code = entry["code"]
        m = existing.get(code)
        if m is None:
            m = Module(module_code=code)
            db.session.add(m)
        m.module_name = entry.get("name") or code
        m.level = entry.get("level") or 1
        m.sort_order = entry.get("sort_order")
        code_to_module[code] = (m, entry.get("parent_code"))

    db.session.flush()

    for code, (m, parent_code) in code_to_module.items():
        if parent_code:
            parent = code_to_module.get(parent_code, (None, None))[0] or existing.get(parent_code)
            if parent is None:
                raise click.ClickException(f"parent_code '{parent_code}' not found for module '{code}'")
            m.parent_id = parent.module_id
        else:
            m.parent_id = None

    db.session.flush()

    yml_pairs = set()
    for entry in modules:
        module = code_to_module[entry["code"]][0]
        existing_perms = {
            p.method: p
            for p in db.session.query(Permission).filter(Permission.module_id == module.module_id).all()
        }
        for perm in entry.get("permissions", []) or []:
            method = perm["method"]
            yml_pairs.add((module.module_id, method))
            p = existing_perms.get(method)
            if p is None:
                p = Permission(module_id=module.module_id, method=method)
                db.session.add(p)
            p.permission_code = perm.get("code") or f"{module.module_code}.{method}"
            p.description = perm.get("description")

    if prune:
        for m in db.session.query(Module).all():
            if m.module_code in yml_module_codes:
                continue
            db.session.delete(m)
        for p in db.session.query(Permission).all():
            if (p.module_id, p.method) not in yml_pairs:
                db.session.delete(p)

    db.session.commit()


BOOTSTRAP_USERNAME = "jaoaurai798"


def _apply_bootstrap(payload):
    exists = db.session.query(User).filter(User.username == BOOTSTRAP_USERNAME).first()
    if exists:
        return

    bootstrap = payload.get("bootstrap") or {}
    roles_data = bootstrap.get("roles") or []
    user_data = bootstrap.get("user") or {}

    # upsert roles by role_code
    role_code_to_obj = {}
    for rd in roles_data:
        role = db.session.query(Role).filter(Role.role_code == rd["role_code"]).first()
        if role is None:
            role = Role(
                role_code=rd["role_code"],
                role_name=rd["role_name"],
                description=rd.get("description"),
                active_flag=rd.get("active_flag", True),
            )
            db.session.add(role)
        else:
            role.role_name = rd["role_name"]
            role.active_flag = rd.get("active_flag", True)
        role_code_to_obj[rd["role_code"]] = (role, rd.get("grant_all_permissions", False))

    db.session.flush()

    all_permissions = db.session.query(Permission).all()
    perm_code_to_obj = {p.permission_code: p for p in all_permissions}

    for rd in roles_data:
        role, grant_all = role_code_to_obj[rd["role_code"]]
        existing_rp = {
            rp.permission_id
            for rp in db.session.query(RolePermission).filter(RolePermission.role_id == role.role_id).all()
        }
        if grant_all:
            target_perms = all_permissions
        else:
            codes = rd.get("permissions") or []
            target_perms = [perm_code_to_obj[c] for c in codes if c in perm_code_to_obj]

        for perm in target_perms:
            if perm.permission_id in existing_rp:
                continue
            db.session.add(RolePermission(
                role_id=role.role_id,
                permission_id=perm.permission_id,
                active_flag=True,
            ))

    db.session.flush()

    # create bootstrap user
    role_code = user_data.get("role_code")
    role_obj = role_code_to_obj.get(role_code, (None, False))[0] if role_code else None
    if role_obj is None:
        raise click.ClickException(f"Bootstrap user role_code '{role_code}' not found in bootstrap.roles")

    new_user = User(
        username=BOOTSTRAP_USERNAME,
        password=hash_bcrypt(user_data["password"]),
        role_id=role_obj.role_id,
        is_active=True,
    )
    db.session.add(new_user)
    db.session.commit()
    click.echo(f"Bootstrap: created user '{BOOTSTRAP_USERNAME}' with role '{role_code}'")


def register_permission_cli(app):
    @app.cli.command("seed-export")
    @click.option("--path", "path", default=DEFAULT_SEED_PATH, show_default=True)
    @with_appcontext
    def seed_export(path):
        """Dump m_module and m_permission to YAML seed file. Preserves existing bootstrap section."""
        data = _export_to_dict()

        existing_bootstrap = None
        if os.path.exists(path):
            with open(path) as f:
                existing = yaml.safe_load(f) or {}
            existing_bootstrap = existing.get("bootstrap")

        if existing_bootstrap:
            data["bootstrap"] = existing_bootstrap

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            _ordered_dump(data, f, default_flow_style=False, allow_unicode=True)
        click.echo(f"Exported {len(data['modules'])} modules to {path}")

    @app.cli.command("seed-apply")
    @click.option("--path", "path", default=DEFAULT_SEED_PATH, show_default=True)
    @click.option("--prune", is_flag=True, help="Delete modules/permissions not present in seed file")
    @with_appcontext
    def seed_apply(path, prune):
        """Upsert m_module and m_permission from YAML seed file. Natural keys: module_code, (module_id, method)."""
        if not os.path.exists(path):
            raise click.ClickException(f"Seed file not found: {path}")
        with open(path) as f:
            payload = yaml.safe_load(f) or {}
        try:
            _apply_from_dict(payload, prune=prune)
            _apply_bootstrap(payload)
        except Exception:
            db.session.rollback()
            raise
        click.echo(f"Applied seed from {path} (prune={prune})")
