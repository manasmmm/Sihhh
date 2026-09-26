"""
summary_text / fisherman message template (spec Section 8.4).

Templates live in i18n/<lang>.json (keys "summary.*"), so adding a coastal
language only needs one new JSON file.
"""
import glob
import json
import os
from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Optional

import config


def _i18n_mtime(lang: str) -> float:
    p = os.path.join(config.I18N_DIR, f"{lang}.json")
    return os.path.getmtime(p) if os.path.exists(p) else 0.0


@lru_cache(maxsize=32)
def _load(lang: str, _mtime: float) -> Dict[str, str]:
    p = os.path.join(config.I18N_DIR, f"{lang}.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_strings(lang: str) -> Dict[str, str]:
    """Strings for `lang`, falling back to English for missing keys."""
    base = dict(_load(config.DEFAULT_LANGUAGE, _i18n_mtime(config.DEFAULT_LANGUAGE)))
    if lang != config.DEFAULT_LANGUAGE:
        base.update(_load(lang, _i18n_mtime(lang)))
    return base


def available_languages() -> List[dict]:
    out = []
    for p in sorted(glob.glob(os.path.join(config.I18N_DIR, "*.json"))):
        code = os.path.splitext(os.path.basename(p))[0]
        s = _load(code, _i18n_mtime(code))
        out.append({"code": code, "name": s.get("_language_name", code), "status": s.get("_status", "final")})
    return out


def _num(v, strings) -> str:
    if v is None:
        return strings["summary.not_available"]
    return str(int(round(float(v))))


def _depth(v, strings) -> str:
    if v is None:
        return strings["summary.not_available"]
    return strings["summary.depth"].format(value=_num(v, strings))


def _date(iso: Optional[str], strings) -> str:
    if not iso:
        return strings["summary.not_available"]
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        return iso


def build_summary(row: dict, lang: str = config.DEFAULT_LANGUAGE, species: Optional[dict] = None) -> str:
    s = load_strings(lang)
    ssf = row.get("subsurface_front")
    if ssf is None:
        front_sentence = s["summary.front_na"]
    else:
        front_sentence = s["summary.front_yes"] if ssf else s["summary.front_no"]

    direction = row.get("direction") or ""
    level = row.get("confidence_level") or "not_available"

    text = s["summary.template"].format(
        dist_from=_num(row.get("dist_from_km"), s),
        dist_to=_num(row.get("dist_to_km"), s),
        direction=s.get(f"direction.{direction}", direction),
        landmark=row.get("landmark", ""),
        bearing=_num(row.get("bearing_deg"), s),
        sea_from=_num(row.get("sea_depth_from_m"), s),
        sea_to=_num(row.get("sea_depth_to_m"), s),
        d20=_depth(row.get("d20_m"), s),
        mld=_depth(row.get("mld_m"), s),
        front_sentence=front_sentence,
        confidence_level=s.get(f"confidence.{level}", level),
        valid_upto=_date(row.get("valid_upto"), s),
    )
    if species and species.get("configured"):
        if row.get("gear_depth_from_m") is not None:
            text += " " + s["summary.gear"].format(
                species=s.get(f"species.{species['name']}", species["name"]),
                gear_from=_num(row.get("gear_depth_from_m"), s),
                gear_to=_num(row.get("gear_depth_to_m"), s),
            )
        else:
            text += " " + s["summary.gear_none"].format(species=s.get(f"species.{species['name']}", species["name"]))
    return text
