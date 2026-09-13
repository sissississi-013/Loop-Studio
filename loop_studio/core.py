"""Versioned projects and validated timeline operations, independent of models/UI."""
from __future__ import annotations
import copy
import json
import math
import re
import threading
import uuid
from pathlib import Path


class Conflict(ValueError):
    pass


def ident():
    return uuid.uuid4().hex[:16]


def number(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} must be between {low} and {high}")
    return float(value)


DEFAULT_STYLE = {"aspect": "landscape", "look": "natural", "title": "", "title_size": 64,
                 "source_volume": 1.0, "music_volume": 0.18, "music": "none",
                 "font": "sans", "title_position": "top-left", "title_background": False}


def validate(project):
    assets = project["assets"]
    if len([a for a in assets.values() if a.get("kind", "clip") == "clip"]) > 10:
        raise ValueError("Projects support up to ten video clips")
    if sum(a["duration"] for a in assets.values() if a.get("kind", "clip") == "clip") > 600.1:
        raise ValueError("Projects support ten minutes of source footage")
    if len([a for a in assets.values() if a.get("kind") == "reference"]) > 3:
        raise ValueError("Projects support up to three references")
    seen = set()
    for shot in project["timeline"]:
        if shot["id"] in seen:
            raise ValueError("Duplicate shot identifier")
        seen.add(shot["id"])
        asset = assets.get(shot["asset_id"])
        if not asset or asset.get("kind", "clip") != "clip":
            raise ValueError("Shot must reference a project video clip")
        start = number(shot["start"], 0, asset["duration"], "Trim start")
        end = number(shot["end"], 0, asset["duration"], "Trim end")
        if end - start < .25:
            raise ValueError("Shots must be at least 0.25 seconds")
        number(shot.get("volume", 1), 0, 2, "Shot volume")
        if not isinstance(shot.get("locked", False), bool):
            raise ValueError("Lock must be a boolean")
        if len(shot.get("caption", "")) > 300:
            raise ValueError("Shot captions are limited to 300 characters")
    if len(project["timeline"]) > 100:
        raise ValueError("Timeline supports up to 100 shots")
    if sum(s["end"] - s["start"] for s in project["timeline"]) > 600.1:
        raise ValueError("Timeline is limited to ten minutes")
    style = project["style"]
    if style["aspect"] not in ("landscape", "portrait", "square"):
        raise ValueError("Unknown aspect ratio")
    if style["look"] not in ("natural", "warm", "cool", "mono"):
        raise ValueError("Unknown color look")
    if style["music"] not in ("none", "ambient", "pulse"):
        raise ValueError("Unknown soundtrack")
    if style.get("font", "sans") not in ("sans", "serif", "mono"):
        raise ValueError("Unknown typeface")
    if style.get("title_position", "top-left") not in ("top-left", "top-center", "bottom-left", "bottom-center"):
        raise ValueError("Unknown title position")
    if not isinstance(style.get("title_background", False), bool):
        raise ValueError("Title background must be a boolean")
    number(style["title_size"], 24, 120, "Title size")
    number(style["source_volume"], 0, 2, "Source volume")
    number(style["music_volume"], 0, 1, "Music volume")
    if len(style["title"]) > 120:
        raise ValueError("Title is limited to 120 characters")
    if len(project.get("brief", "")) > 4000:
        raise ValueError("Brief is limited to 4000 characters")


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def directory(self, pid):
        if not re.fullmatch(r"[a-f0-9]{16}", pid):
            raise ValueError("Invalid project identifier")
        return self.root / pid

    def load(self, pid):
        with self.lock:
            project = json.loads((self.directory(pid) / "project.json").read_text())
            project["style"] = {**DEFAULT_STYLE, **project["style"]}
            return project

    def save(self, project):
        directory = self.directory(project["id"])
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / "project.json"
        temp = directory / "project.tmp"
        temp.write_text(json.dumps(project, ensure_ascii=False, indent=2))
        temp.replace(target)

    def create(self, name="Untitled film"):
        with self.lock:
            project = {"id": ident(), "name": str(name)[:100], "version": 0, "assets": {},
                       "timeline": [], "style": copy.deepcopy(DEFAULT_STYLE), "brief": "",
                       "undo": [], "redo": [], "analysis": {}, "exports": []}
            self.save(project)
            return project

    def list(self):
        with self.lock:
            projects = []
            for path in sorted(self.root.glob("*/project.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                p = json.loads(path.read_text())
                projects.append({k: p[k] for k in ("id", "name", "version")})
            return projects

    @staticmethod
    def snapshot(project):
        return copy.deepcopy({k: project[k] for k in ("name", "timeline", "style", "brief")})

    def update(self, pid, version, operation):
        with self.lock:
            p = self.load(pid)
            if version != p["version"]:
                raise Conflict("Project changed. Reload before applying this edit.")
            before = self.snapshot(p)
            op = operation["op"]
            if op in ("undo", "redo"):
                source, dest = ("undo", "redo") if op == "undo" else ("redo", "undo")
                if not p[source]:
                    raise ValueError(f"Nothing to {op}")
                p[dest].append(before)
                p.update(p[source].pop())
            else:
                self.apply(p, operation)
                for index, shot in enumerate(before["timeline"]):
                    unlocking = (op == "shot" and operation.get("shot_id") == shot["id"] and operation.get("changes") == {"locked": False})
                    if shot.get("locked") and not unlocking and (index >= len(p["timeline"]) or p["timeline"][index] != shot):
                        raise ValueError("This edit would change a locked shot or its timeline position")
                p["undo"] = (p["undo"] + [before])[-100:]
                p["redo"] = []
            p["style"] = {**DEFAULT_STYLE, **p["style"]}
            validate(p)
            p["version"] += 1
            self.save(p)
            return p

    def apply(self, p, operation):
        op = operation["op"]
        if op == "add":
            asset = p["assets"].get(operation["asset_id"])
            if not asset:
                raise ValueError("Unknown asset")
            p["timeline"].append({"id": ident(), "asset_id": asset["id"], "start": operation.get("start", 0),
                                  "end": operation.get("end", asset["duration"]), "locked": False,
                                  "caption": "", "volume": 1.0})
        elif op in ("shot", "remove", "move", "split"):
            index = next((i for i, s in enumerate(p["timeline"]) if s["id"] == operation["shot_id"]), None)
            if index is None:
                raise ValueError("Unknown shot")
            shot = p["timeline"][index]
            if shot.get("locked") and not (op == "shot" and operation.get("changes") == {"locked": False}):
                raise ValueError("Unlock this shot before changing it")
            if op == "remove":
                p["timeline"].pop(index)
            elif op == "split":
                at = number(operation["at"], shot["start"] + .25, shot["end"] - .25, "Split time")
                right = copy.deepcopy(shot)
                right.update(id=ident(), start=at)
                shot["end"] = at
                p["timeline"].insert(index + 1, right)
            elif op == "move":
                to = operation["index"]
                if not isinstance(to, int) or not 0 <= to < len(p["timeline"]):
                    raise ValueError("Invalid destination")
                lo, hi = sorted((index, to))
                if any(s.get("locked") for s in p["timeline"][lo:hi + 1]):
                    raise ValueError("Moving across a locked shot would change its position")
                p["timeline"].insert(to, p["timeline"].pop(index))
            else:
                changes = operation["changes"]
                if not set(changes) <= {"start", "end", "locked", "caption", "volume"}:
                    raise ValueError("Unknown shot property")
                shot.update(changes)
        elif op == "settings":
            if "style" in operation:
                if not set(operation["style"]) <= set(DEFAULT_STYLE):
                    raise ValueError("Unknown style property")
                p["style"].update(operation["style"])
            for key in ("name", "brief"):
                if key in operation:
                    p[key] = str(operation[key])[:4000 if key == "brief" else 100]
        elif op == "proposal":
            proposed = copy.deepcopy(operation["timeline"])
            # Locks protect both shot contents and timeline position.
            for i, shot in enumerate(p["timeline"]):
                if shot.get("locked") and (i >= len(proposed) or proposed[i] != shot):
                    raise ValueError("Proposal changes a locked shot")
            p["timeline"] = proposed
        else:
            raise ValueError("Unknown operation")
