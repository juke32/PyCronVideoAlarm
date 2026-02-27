import sys
import os
import plistlib
import subprocess
import logging
import uuid
import glob
from typing import List, Dict, Any
from datetime import datetime

PLIST_DIR = os.path.expanduser("~/Library/LaunchAgents")
LABEL_PREFIX = "com.juke32.pycronvideoalarm"


def _plist_path(job_id: str) -> str:
    return os.path.join(PLIST_DIR, f"{LABEL_PREFIX}.{job_id}.plist")


def _launchctl(args: list) -> bool:
    """Run launchctl command. Returns True on success."""
    try:
        result = subprocess.run(
            ["launchctl"] + args,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logging.warning(f"launchctl {args}: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        logging.error(f"launchctl failed: {e}")
        return False


class MacOSScheduler:
    """macOS scheduler using launchd (~/Library/LaunchAgents).

    Each alarm is stored as a .plist in ~/Library/LaunchAgents/ and
    loaded with 'launchctl load'. This is the recommended macOS approach:
    - No PATH or GUI session issues (unlike cron)
    - Handles missed jobs when Mac was asleep
    - Native OS integration

    Plist label format:  com.juke32.pycronvideoalarm.{uuid}
    Plist file location: ~/Library/LaunchAgents/com.juke32.pycronvideoalarm.{uuid}.plist
    """

    MARKER = LABEL_PREFIX

    def __init__(self):
        os.makedirs(PLIST_DIR, exist_ok=True)
        logging.info(f"MacOSScheduler: using launchd (plist dir: {PLIST_DIR})")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_cmd(self, sequence_name: str, job_id: str, one_time: bool,
                   alarm_time) -> List[str]:
        if getattr(sys, 'frozen', False):
            executable = sys.executable
        else:
            executable = sys.executable
            script_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../main.py")
            )
            # For dev: run as 'python script.py'
            return self._build_cmd_dev(sequence_name, job_id, one_time, alarm_time, script_path, executable)

        cmd = [executable, "--execute-sequence", sequence_name]
        if one_time:
            time_str = alarm_time.strftime('%H:%M')
            cmd += ["--delete-after", "--job-id", job_id, "--scheduled-time", time_str]
        return cmd

    def _build_cmd_dev(self, sequence_name, job_id, one_time, alarm_time, script_path, python):
        cmd = [python, script_path, "--execute-sequence", sequence_name]
        if one_time:
            time_str = alarm_time.strftime('%H:%M')
            cmd += ["--delete-after", "--job-id", job_id, "--scheduled-time", time_str]
        return cmd

    def _build_calendar_interval(self, alarm_time, days: List[str], one_time: bool):
        """Build the StartCalendarInterval plist structure."""
        day_map = {"MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6, "SUN": 0}

        if one_time:
            return {
                "Month":  alarm_time.month,
                "Day":    alarm_time.day,
                "Hour":   alarm_time.hour,
                "Minute": alarm_time.minute,
            }
        elif not days or len(days) == 7:
            # Daily — no Weekday key = runs every day at this time
            return {"Hour": alarm_time.hour, "Minute": alarm_time.minute}
        else:
            # Specific weekdays → array of dicts
            return [
                {"Weekday": day_map.get(d, 1), "Hour": alarm_time.hour, "Minute": alarm_time.minute}
                for d in days
            ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_alarm(self, alarm_time, sequence_name: str, days: List[str],
                  one_time: bool = True):
        """Create a launchd plist for the alarm and load it. Returns (success, msg)."""
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
                # Store metadata so we can reconstruct alarm info later
                "EnvironmentVariables": {
                    "PCVA_SEQUENCE": sequence_name,
                    "PCVA_ONE_TIME": "1" if one_time else "0",
                    "PCVA_DAYS": ",".join(days) if days else "daily",
                    "PCVA_JOB_ID": job_id,
                }
            }

            with open(plist_file, "wb") as f:
                plistlib.dump(plist, f)

            if _launchctl(["load", plist_file]):
                msg = f"Alarm set for {alarm_time.strftime('%H:%M')} via launchd"
                logging.info(f"MacOSScheduler: {msg} | plist: {plist_file}")
                return True, msg
            else:
                os.remove(plist_file)
                return False, "launchctl load failed — check logs"

        except Exception as e:
            logging.exception(f"MacOSScheduler add_alarm failed: {e}")
            return False, f"launchd Error: {str(e)}"

    def list_alarms(self) -> List[Dict[str, Any]]:
        """List all PyCronVideoAlarm launchd jobs."""
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
                    cal = cal[0]  # First entry for display
                hour = cal.get("Hour", 0)
                minute = cal.get("Minute", 0)
                time_str = f"{hour}:{str(minute).zfill(2)}"

                if one_time:
                    days = ["Once"]
                elif days_raw == "daily":
                    days = ["Daily"]
                else:
                    days = [d.strip() for d in days_raw.split(",") if d.strip()]

                # Check if actually loaded via launchctl
                label = plist.get("Label", "")
                result = subprocess.run(
                    ["launchctl", "list", label],
                    capture_output=True, text=True
                )
                enabled = result.returncode == 0

                alarms.append({
                    'time': time_str,
                    'sequence': sequence,
                    'days': days,
                    'enabled': enabled
                })
            except Exception as e:
                logging.debug(f"MacOSScheduler: skipping {plist_file}: {e}")
                continue
        return alarms

    def remove_alarm(self, sequence_name: str, time_str: str,
                     days_str: str = ""):
        """Unload and delete the matching launchd plist. Returns (success, msg)."""
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

                    # days check if provided
                    if days_str:
                        days_raw = env.get("PCVA_DAYS", "daily")
                        if days_raw == "daily":
                            job_days = "Daily"
                        elif env.get("PCVA_ONE_TIME") == "1":
                            job_days = "Once"
                        else:
                            job_days = ", ".join(d.strip() for d in days_raw.split(","))
                        if job_days != days_str:
                            continue

                    _launchctl(["unload", plist_file])
                    os.remove(plist_file)
                    logging.info(f"MacOSScheduler: removed {plist_file}")
                    return True, f"Removed alarm: {sequence_name}"
                except Exception:
                    continue

            return False, f"Alarm '{sequence_name}' at {time_str} not found."
        except Exception as e:
            logging.exception(f"MacOSScheduler remove_alarm failed: {e}")
            return False, f"Remove Error: {str(e)}"

    def get_debug_info(self) -> str:
        lines = ["=== macOS launchd Scheduler Debug Info ==="]
        pattern = os.path.join(PLIST_DIR, f"{LABEL_PREFIX}.*.plist")
        plists = sorted(glob.glob(pattern))
        lines.append(f"Plist directory: {PLIST_DIR}")
        lines.append(f"Alarm plists found: {len(plists)}")
        for p in plists:
            lines.append(f"  {os.path.basename(p)}")
        return "\n".join(lines)
