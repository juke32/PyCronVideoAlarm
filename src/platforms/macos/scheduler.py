import sys
import os
import plistlib
import subprocess
import logging
import uuid
import glob
from typing import List, Dict, Any

PLIST_DIR = os.path.expanduser("~/Library/LaunchAgents")
LABEL_PREFIX = "com.juke32.pycronvideoalarm"


def _uid() -> str:
    return str(os.getuid())


def _plist_path(job_id: str) -> str:
    return os.path.join(PLIST_DIR, f"{LABEL_PREFIX}.{job_id}.plist")


def _launchctl_load(plist_file: str) -> bool:
    """Load a plist using the modern bootstrap API (macOS 10.15+).
    Falls back to legacy 'launchctl load' if bootstrap fails.
    Returns True if either method succeeds.
    IMPORTANT: Never deletes the plist file on failure — the plist
    stays on disk so list_alarms() can still see it and remove_alarm()
    can clean it up from the UI.
    """
    # Modern API: launchctl bootstrap gui/<uid> <plist>
    try:
        result = subprocess.run(
            ["launchctl", "bootstrap", f"gui/{_uid()}", plist_file],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logging.info(f"launchctl bootstrap succeeded for {os.path.basename(plist_file)}")
            return True
        logging.debug(f"launchctl bootstrap failed (rc={result.returncode}): {result.stderr.strip()}")
    except Exception as e:
        logging.debug(f"launchctl bootstrap error: {e}")

    # Legacy fallback: launchctl load <plist>
    try:
        result = subprocess.run(
            ["launchctl", "load", plist_file],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logging.info(f"launchctl load succeeded (legacy) for {os.path.basename(plist_file)}")
            return True
        logging.warning(f"launchctl load (legacy) failed (rc={result.returncode}): {result.stderr.strip()}")
    except Exception as e:
        logging.warning(f"launchctl load error: {e}")

    # Both failed — plist is still written, alarm appears in UI, but may not fire
    logging.error(
        f"Could not register {os.path.basename(plist_file)} with launchd. "
        "The alarm is saved but may not fire automatically. "
        "Try: launchctl bootstrap gui/$(id -u) " + plist_file
    )
    return False


def _launchctl_unload(plist_file: str) -> bool:
    """Unload a plist using bootout (modern) or unload (legacy)."""
    label = None
    try:
        with open(plist_file, "rb") as f:
            plist = plistlib.load(f)
        label = plist.get("Label", "")
    except Exception:
        pass

    # Modern: launchctl bootout gui/<uid> <label>  OR  bootout gui/<uid> <plist>
    if label:
        r = subprocess.run(
            ["launchctl", "bootout", f"gui/{_uid()}", plist_file],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            return True

    # Legacy: launchctl unload <plist>
    r = subprocess.run(
        ["launchctl", "unload", plist_file],
        capture_output=True, text=True
    )
    return r.returncode == 0


class MacOSScheduler:
    """macOS scheduler using launchd (~/Library/LaunchAgents).

    Each alarm is a .plist in ~/Library/LaunchAgents/.
    The plist is ALWAYS written to disk; launchctl loading is attempted
    separately and its failure does not delete the plist.

    NOTE: ~/Library/ is hidden in Finder by default.
    To open it: Finder → Go menu → hold Option → Library.
    Or: Finder → Go to Folder → ~/Library/LaunchAgents/
    """

    MARKER = LABEL_PREFIX

    def __init__(self):
        os.makedirs(PLIST_DIR, exist_ok=True)
        logging.info(f"MacOSScheduler ready. plist dir: {PLIST_DIR}")

    def _build_cmd(self, sequence_name: str, job_id: str,
                   one_time: bool, alarm_time) -> List[str]:
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--execute-sequence", sequence_name]
        else:
            script_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../main.py")
            )
            cmd = [sys.executable, script_path, "--execute-sequence", sequence_name]

        if one_time:
            time_str = alarm_time.strftime('%H:%M')
            cmd += ["--delete-after", "--job-id", job_id,
                    "--scheduled-time", time_str]
        return cmd

    def _build_calendar_interval(self, alarm_time, days: List[str],
                                 one_time: bool):
        day_map = {"MON": 1, "TUE": 2, "WED": 3, "THU": 4,
                   "FRI": 5, "SAT": 6, "SUN": 0}
        if one_time:
            return {"Month": alarm_time.month, "Day": alarm_time.day,
                    "Hour": alarm_time.hour, "Minute": alarm_time.minute}
        elif not days or len(days) == 7:
            return {"Hour": alarm_time.hour, "Minute": alarm_time.minute}
        else:
            return [
                {"Weekday": day_map.get(d, 1),
                 "Hour": alarm_time.hour, "Minute": alarm_time.minute}
                for d in days
            ]

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def add_alarm(self, alarm_time, sequence_name: str, days: List[str],
                  one_time: bool = True):
        try:
            job_id = str(uuid.uuid4())
            label = f"{LABEL_PREFIX}.{job_id}"
            plist_file = _plist_path(job_id)

            cmd = self._build_cmd(sequence_name, job_id, one_time, alarm_time)
            calendar = self._build_calendar_interval(alarm_time, days, one_time)

            plist = {
                "Label": label,
                "ProgramArguments": cmd,
                "StartCalendarInterval": calendar,
                "RunAtLoad": False,
                "StandardOutPath": os.path.expanduser(
                    f"~/Library/Logs/PyCronVideoAlarm.{job_id}.log"),
                "StandardErrorPath": os.path.expanduser(
                    f"~/Library/Logs/PyCronVideoAlarm.{job_id}.log"),
                "EnvironmentVariables": {
                    "PCVA_SEQUENCE": sequence_name,
                    "PCVA_ONE_TIME": "1" if one_time else "0",
                    "PCVA_DAYS": ",".join(days) if days else "daily",
                    "PCVA_JOB_ID": job_id,
                },
            }

            # Always write the plist first
            with open(plist_file, "wb") as f:
                plistlib.dump(plist, f)
            logging.info(f"Plist written: {plist_file}")

            # Load it (failure does NOT delete the plist)
            loaded = _launchctl_load(plist_file)
            time_str = alarm_time.strftime('%H:%M')
            if loaded:
                msg = f"Alarm set for {time_str} via launchd"
            else:
                msg = (f"Alarm saved for {time_str} but launchd registration "
                       "failed — it may not fire. See logs for details.")
            return loaded, msg

        except Exception as e:
            logging.exception(f"MacOSScheduler add_alarm failed: {e}")
            return False, f"launchd Error: {str(e)}"

    def list_alarms(self) -> List[Dict[str, Any]]:
        alarms = []
        pattern = os.path.join(PLIST_DIR, f"{LABEL_PREFIX}.*.plist")
        for plist_file in sorted(glob.glob(pattern)):
            try:
                with open(plist_file, "rb") as f:
                    plist = plistlib.load(f)
                env = plist.get("EnvironmentVariables", {})
                sequence = env.get("PCVA_SEQUENCE", "Unknown")
                one_time = env.get("PCVA_ONE_TIME", "0") == "1"
                days_raw = env.get("PCVA_DAYS", "daily")

                cal = plist.get("StartCalendarInterval", {})
                if isinstance(cal, list):
                    cal = cal[0]
                hour = cal.get("Hour", 0)
                minute = cal.get("Minute", 0)
                time_str = f"{hour}:{str(minute).zfill(2)}"

                if one_time:
                    days = ["Once"]
                elif days_raw == "daily":
                    days = ["Daily"]
                else:
                    days = [d.strip() for d in days_raw.split(",") if d.strip()]

                label = plist.get("Label", "")
                r = subprocess.run(["launchctl", "list", label],
                                   capture_output=True, text=True)
                enabled = r.returncode == 0

                alarms.append({
                    "time": time_str,
                    "sequence": sequence,
                    "days": days,
                    "enabled": enabled,
                })
            except Exception as e:
                logging.debug(f"Skipping {os.path.basename(plist_file)}: {e}")
        return alarms

    def remove_alarm(self, sequence_name: str, time_str: str,
                     days_str: str = ""):
        try:
            hour, minute = map(int, time_str.split(":"))
            pattern = os.path.join(PLIST_DIR, f"{LABEL_PREFIX}.*.plist")
            for plist_file in glob.glob(pattern):
                try:
                    with open(plist_file, "rb") as f:
                        plist = plistlib.load(f)
                    env = plist.get("EnvironmentVariables", {})
                    if env.get("PCVA_SEQUENCE") != sequence_name:
                        continue

                    cal = plist.get("StartCalendarInterval", {})
                    if isinstance(cal, list):
                        cal = cal[0]
                    if cal.get("Hour") != hour or cal.get("Minute") != minute:
                        continue

                    if days_str:
                        days_raw = env.get("PCVA_DAYS", "daily")
                        if days_raw == "daily":
                            job_days = "Daily"
                        elif env.get("PCVA_ONE_TIME") == "1":
                            job_days = "Once"
                        else:
                            job_days = ", ".join(
                                d.strip() for d in days_raw.split(","))
                        if job_days != days_str:
                            continue

                    _launchctl_unload(plist_file)
                    os.remove(plist_file)
                    logging.info(f"Removed alarm plist: {os.path.basename(plist_file)}")
                    return True, f"Removed alarm: {sequence_name}"
                except Exception:
                    continue
            return False, f"Alarm '{sequence_name}' at {time_str} not found."
        except Exception as e:
            logging.exception(f"MacOSScheduler remove_alarm failed: {e}")
            return False, f"Remove Error: {str(e)}"

    def get_debug_info(self) -> str:
        lines = [
            "=== macOS launchd Scheduler ===",
            f"Plist directory: {PLIST_DIR}",
            f"(Hidden in Finder — Go menu → hold Option → Library)",
        ]
        pattern = os.path.join(PLIST_DIR, f"{LABEL_PREFIX}.*.plist")
        plists = sorted(glob.glob(pattern))
        lines.append(f"Alarm plists found: {len(plists)}")
        for p in plists:
            try:
                with open(p, "rb") as f:
                    data = plistlib.load(f)
                env = data.get("EnvironmentVariables", {})
                seq = env.get("PCVA_SEQUENCE", "?")
                label = data.get("Label", "")
                r = subprocess.run(["launchctl", "list", label],
                                   capture_output=True, text=True)
                status = "loaded" if r.returncode == 0 else "NOT loaded"
                lines.append(f"  {os.path.basename(p)} | {seq} | {status}")
            except Exception as e:
                lines.append(f"  {os.path.basename(p)} [error: {e}]")
        return "\n".join(lines)
