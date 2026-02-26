#!/usr/bin/env python3
"""CC Claude Codex Skill v2 — Cross-platform installer.

Usage: python setup.py
"""

import json
import platform
import shutil
import sys
from pathlib import Path


def get_skill_dir() -> Path:
    """Return ~/.claude/skills/cc-claude-codex/ for current platform."""
    return Path.home() / ".claude" / "skills" / "cc-claude-codex"


def get_python_cmd() -> str:
    """Return platform-appropriate python command."""
    return "python" if platform.system() == "Windows" else "python3"


def copy_skill(src: Path, dest: Path):
    """Copy skill files to destination."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # Copy SKILL.md
    shutil.copy2(src / "SKILL.md", dest / "SKILL.md")

    # Copy scripts/
    scripts_dest = dest / "scripts"
    scripts_dest.mkdir(exist_ok=True)
    for f in (src / "scripts").iterdir():
        if f.is_file() and f.suffix == ".py":
            shutil.copy2(f, scripts_dest / f.name)

    # Copy references/
    refs_dest = dest / "references"
    refs_dest.mkdir(exist_ok=True)
    for f in (src / "references").iterdir():
        if f.is_file():
            shutil.copy2(f, refs_dest / f.name)

    # Copy code-acceptance/ skill (standalone acceptance skill)
    acceptance_src = src / "code-acceptance"
    if acceptance_src.exists():
        acceptance_dest = dest.parent / "code-acceptance"
        if acceptance_dest.exists():
            shutil.rmtree(acceptance_dest)
        acceptance_dest.mkdir(parents=True, exist_ok=True)
        for f in acceptance_src.iterdir():
            if f.is_file():
                shutil.copy2(f, acceptance_dest / f.name)

    # Copy multi-agent-verify/ skill
    verify_src = src / "multi-agent-verify"
    if verify_src.exists():
        verify_dest = dest.parent / "multi-agent-verify"
        if verify_dest.exists():
            shutil.rmtree(verify_dest)
        verify_dest.mkdir(parents=True, exist_ok=True)
        for f in verify_src.iterdir():
            if f.is_file():
                shutil.copy2(f, verify_dest / f.name)


def generate_hooks_config(skill_dir: Path) -> dict:
    """Generate hooks JSON config with platform-correct paths."""
    py = get_python_cmd()
    scripts = skill_dir / "scripts"

    def cmd(script_name: str) -> str:
        return f'{py} "{(scripts / script_name).as_posix()}"'

    return {
        "hooks": {
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": cmd("stop_check.py"),
                            "timeout": 10000,
                        }
                    ],
                }
            ],
            "PreCompact": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": cmd("pre_compact.py"),
                            "timeout": 5000,
                        }
                    ],
                }
            ],
            "SessionStart": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": cmd("session_inject.py"),
                            "timeout": 5000,
                        }
                    ],
                }
            ],
        }
    }


def merge_hooks(settings: dict, new_hooks: dict) -> dict:
    """Merge skill hooks into existing settings, replacing old skill entries."""
    existing = settings.get("hooks", {})
    skill_scripts = ("stop_check.py", "pre_compact.py", "session_inject.py")

    def has_skill_hook(entry: dict) -> bool:
        """Return True if a hook entry contains any skill script command."""
        hooks = entry.get("hooks")
        if not isinstance(hooks, list):
            return False
        for hook in hooks:
            if not isinstance(hook, dict):
                continue
            command = hook.get("command", "")
            if isinstance(command, str) and any(s in command for s in skill_scripts):
                return True
        return False

    for event, entries in new_hooks["hooks"].items():
        if event not in existing:
            existing[event] = entries
            continue
        # Remove previous skill entries while tolerating malformed/empty hook arrays.
        filtered = []
        for e in existing[event]:
            if not isinstance(e, dict) or not has_skill_hook(e):
                filtered.append(e)
        existing[event] = filtered + entries
    settings["hooks"] = existing
    return settings


def main():
    src = Path(__file__).resolve().parent.parent
    if not (src / "SKILL.md").exists():
        print("Error: Run this script from the cc-claude-codex skill directory.", file=sys.stderr)
        sys.exit(1)

    skill_dir = get_skill_dir()
    print(f"Installing CC Claude Codex skill to: {skill_dir}")

    copy_skill(src, skill_dir)
    print("  Skill files copied.")

    for tool in ("codex", "opencode", "claude"):
        if shutil.which(tool):
            print(f"  {tool} found in PATH.")
        else:
            print(f"  Warning: '{tool}' not found in PATH.", file=sys.stderr)

    # Auto-merge hooks into settings.json
    settings_file = Path.home() / ".claude" / "settings.json"
    new_hooks = generate_hooks_config(skill_dir)

    if settings_file.exists():
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    else:
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings = {}

    old_settings = json.dumps(settings, indent=2, ensure_ascii=False)
    settings = merge_hooks(settings, new_hooks)
    new_settings = json.dumps(settings, indent=2, ensure_ascii=False)

    if old_settings == new_settings:
        print("  Hooks already configured, no changes needed.")
    else:
        settings_file.write_text(new_settings, encoding="utf-8")
        print("  Hooks merged into ~/.claude/settings.json.")

    print("\nInstallation complete.")


if __name__ == "__main__":
    main()

