"""
Role-based access control for VoxCraft.

Roles mirror commercial plans + staff:
  free      — anonymous or logged-in without a valid license
  pro       — Pro license
  pro_plus  — Pro+ license
  admin     — session admin_authed (staff); stacks on top of plan role

Permissions are checked with can("permission") / require_permission("…").
Plan detection still comes from licensing (get_plan / is_pro); this module
only centralizes *what each role may do* so routes and templates share one map.
"""
from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable, Set

# ---- Role hierarchy (higher includes lower for plan roles) ----
ROLE_FREE = "free"
ROLE_PRO = "pro"
ROLE_PRO_PLUS = "pro_plus"
ROLE_ADMIN = "admin"

# Ordered plan strength for "at least plan X"
_PLAN_RANK = {
    ROLE_FREE: 0,
    ROLE_PRO: 1,
    ROLE_PRO_PLUS: 2,
}

# Permission → minimum plan role required (admin always passes via ROLE_ADMIN)
# free-tier features that anyone can hit (subject to quotas elsewhere) are
# listed with ROLE_FREE so can() is honest in templates.
PERMISSIONS = {
    # Core product
    "tts.generate": ROLE_FREE,
    "tts.all_voices": ROLE_PRO,
    "tts.batch": ROLE_FREE,  # free has line limits enforced in route
    "tools.basic": ROLE_FREE,
    "tools.unlimited": ROLE_PRO,
    # Pro features
    "redub.use": ROLE_PRO,
    "ads.skip": ROLE_PRO,
    # Pro+ features
    "clone.use": ROLE_PRO_PLUS,
    "music.use": ROLE_PRO_PLUS,
    # Account
    "account.view": ROLE_FREE,  # still needs login; decorator stacks
    "account.api_keys": ROLE_FREE,
    # Staff
    "admin.access": ROLE_ADMIN,
    "admin.limits": ROLE_ADMIN,
    "admin.licenses": ROLE_ADMIN,
    "admin.users": ROLE_ADMIN,
    "admin.errors": ROLE_ADMIN,
}

# Human labels for upgrade messages
_PERM_LABELS = {
    "redub.use": "Video Redub",
    "clone.use": "Voice Cloning",
    "music.use": "AI Music",
    "tts.all_voices": "all voices",
    "tools.unlimited": "unlimited audio tools",
    "ads.skip": "an ad-free experience",
    "admin.access": "the admin panel",
}


def plan_role(plan: str) -> str:
    """Normalize license plan string to a role id."""
    p = (plan or "").strip().lower()
    if p == ROLE_PRO_PLUS:
        return ROLE_PRO_PLUS
    if p == ROLE_PRO:
        return ROLE_PRO
    return ROLE_FREE


def roles_for(*, plan: str = "", is_admin: bool = False) -> Set[str]:
    """Active roles for this request. Admin is additive, not a plan."""
    roles = {plan_role(plan)}
    # Higher plan implies lower plan role for permission checks
    rank = _PLAN_RANK.get(plan_role(plan), 0)
    if rank >= _PLAN_RANK[ROLE_PRO]:
        roles.add(ROLE_PRO)
    if rank >= _PLAN_RANK[ROLE_PRO_PLUS]:
        roles.add(ROLE_PRO_PLUS)
    if is_admin:
        roles.add(ROLE_ADMIN)
    # Everyone has free
    roles.add(ROLE_FREE)
    return roles


def permission_min_role(permission: str) -> str:
    return PERMISSIONS.get(permission, ROLE_ADMIN)


def roles_grant(roles: Iterable[str], permission: str) -> bool:
    """True if any role in `roles` is enough for `permission`."""
    need = permission_min_role(permission)
    role_set = set(roles)
    if need == ROLE_ADMIN:
        return ROLE_ADMIN in role_set
    if ROLE_ADMIN in role_set:
        return True  # staff bypass for product perms
    need_rank = _PLAN_RANK.get(need, 99)
    best = max((_PLAN_RANK.get(r, 0) for r in role_set), default=0)
    return best >= need_rank


def permission_label(permission: str) -> str:
    return _PERM_LABELS.get(permission, permission)


def upgrade_hint(permission: str) -> str:
    need = permission_min_role(permission)
    label = permission_label(permission)
    if need == ROLE_PRO_PLUS:
        return f"{label} requires Pro+. Upgrade to unlock."
    if need == ROLE_PRO:
        return f"{label} requires Pro. Upgrade to unlock."
    if need == ROLE_ADMIN:
        return "Admin access required."
    return "You do not have access to this feature."
