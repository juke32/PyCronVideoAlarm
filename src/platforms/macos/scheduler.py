import sys
import os
import logging
import getpass
import uuid
from typing import List, Dict, Any

try:
    from crontab import CronTab
    HAS_CRONTAB = True
    logging.info("MacOSScheduler: CronTab imported successfully")
except ImportError as e:
    HAS_CRONTAB = False
    logging.warning(f"MacOSScheduler: python-crontab not found: {e}. "
                    "Install with: pip install python-crontab")


class MacOSScheduler:
    """macOS scheduler using the user crontab.

    macOS ships with cron — no launchd/launchctl required.
    The API is identical to LinuxScheduler, minus the Linux-specific
    DISPLAY / XDG_RUNTIME_DIR environment injection that cron needs on Linux
    (macOS GUI sessions are always available to cron jobs via the Aqua session).
    """

    MARKER = "#PyCronVideoAlarm"

    def __init__(self):
        self.cron = None
        if not HAS_CRONTAB:
            logging.warning("MacOSScheduler: CronTab unavailable — scheduling disabled")
            return
        try:
            self.cron = CronTab(user=True)
            count = sum(1 for _ in self.cron)
            logging.info(f"MacOSScheduler: crontab opened ({count} existing jobs)")
        except Exception as e:
            logging.error(f"MacOSScheduler: failed to access crontab: {e}")
            self.cron = None

    def add_alarm(self, alarm_time, sequence_name: str, days: List[str],
                  one_time: bool = True) -> tuple:
        """Add an alarm to the crontab. Returns (success, message)."""
        if self.cron is None:
            return False, "Crontab not available. Check logs for details."

        try:
            # Build command — no DISPLAY prefix needed on macOS
            if getattr(sys, 'frozen', False):
                # frozen: executable is inside App.app/Contents/MacOS/
                # The sequences/ folder lives next to the .app bundle
                cmd = f'"{sys.executable}" --execute-sequence "{sequence_name}"'
            else:
                script_path = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "../../main.py")
                )
                cmd = f'"{sys.executable}" "{script_path}" --execute-sequence "{sequence_name}"'

            job_id = str(uuid.uuid4())

            if one_time:
                time_str = alarm_time.strftime('%H:%M')
                cmd += f" --delete-after --job-id {job_id} --scheduled-time {time_str}"
                comment = f"{self.MARKER}:{job_id}"
            else:
                comment = self.MARKER

            job = self.cron.new(command=cmd, comment=comment)
            job.minute.on(alarm_time.minute)
            job.hour.on(alarm_time.hour)

            if one_time:
                job.month.on(alarm_time.month)
                job.day.on(alarm_time.day)
            elif len(days) == 7 or not days:
                job.dow.every(1)
            else:
                day_map = {"MON": 1, "TUE": 2, "WED": 3, "THU": 4,
                           "FRI": 5, "SAT": 6, "SUN": 0}
                cron_days = [day_map.get(d, 1) for d in days]
                job.dow.on(*cron_days)

            self.cron.write()
            msg = f"Alarm set for {alarm_time.strftime('%H:%M')} via Cron"
            logging.info(f"MacOSScheduler: {msg} | cmd: {cmd}")
            return True, msg

        except Exception as e:
            logging.exception(f"MacOSScheduler add_alarm failed: {e}")
            return False, f"Crontab Error: {str(e)}"

    def list_alarms(self) -> List[Dict[str, Any]]:
        """List all PyCronVideoAlarm jobs from crontab."""
        if self.cron is None:
            return []

        alarms = []
        for job in self.cron:
            if not (job.comment and (
                job.comment == self.MARKER
                or job.comment.startswith(self.MARKER + ":")
            )):
                continue
            try:
                import shlex
                args = shlex.split(job.command)
                seq_idx = args.index('--execute-sequence')
                sequence = args[seq_idx + 1]
                time_str = f"{job.hour}:{str(job.minute).zfill(2)}"

                day_rev_map = {"1": "MON", "2": "TUE", "3": "WED", "4": "THU",
                               "5": "FRI", "6": "SAT", "0": "SUN"}
                dow_str = str(job.dow)
                if "--delete-after" in job.command:
                    days = ["Once"]
                elif dow_str == "*":
                    days = ["Daily"]
                else:
                    days = [day_rev_map.get(d.strip(), d) for d in dow_str.split(",")]

                alarms.append({
                    'time': time_str,
                    'sequence': sequence,
                    'days': days,
                    'enabled': job.is_enabled()
                })
            except Exception as e:
                logging.debug(f"MacOSScheduler: skipping unparseable job: {e}")
                continue
        return alarms

    def remove_alarm(self, sequence_name: str, time_str: str,
                     days_str: str = "") -> tuple:
        """Remove an alarm from crontab. Returns (success, message)."""
        if self.cron is None:
            return False, "Crontab not available"

        try:
            hour, minute = map(int, time_str.split(":"))
            removed = False
            day_rev_map = {"1": "MON", "2": "TUE", "3": "WED", "4": "THU",
                           "5": "FRI", "6": "SAT", "0": "SUN"}

            for job in self.cron:
                is_ours = job.comment and (
                    job.comment == self.MARKER
                    or job.comment.startswith(self.MARKER + ":")
                )
                if not (is_ours and job.hour == hour
                        and job.minute == minute
                        and sequence_name in job.command):
                    continue

                if days_str:
                    dow_str = str(job.dow)
                    if "--delete-after" in job.command:
                        job_days = "Once"
                    elif dow_str == "*":
                        job_days = "Daily"
                    else:
                        job_days = ", ".join(
                            day_rev_map.get(d.strip(), d)
                            for d in dow_str.split(",")
                        )
                    if job_days != days_str:
                        continue

                self.cron.remove(job)
                removed = True
                break

            if removed:
                self.cron.write()
                return True, f"Removed alarm: {sequence_name}"
            return False, f"Alarm '{sequence_name}' at {time_str} not found."

        except Exception as e:
            logging.exception(f"MacOSScheduler remove_alarm failed: {e}")
            return False, f"Remove Error: {str(e)}"

    def get_debug_info(self) -> str:
        info = ["=== macOS Crontab Debug Info ==="]
        try:
            info.append(f"User: {getpass.getuser()}")
            info.append(f"HOME: {os.environ.get('HOME', 'not set')}")
            info.append(f"CronTab available: {self.cron is not None}")
        except Exception as e:
            info.append(f"Error: {e}")
        if self.cron is not None:
            info.append("\nAll crontab entries:")
            for job in self.cron:
                marker = " [OURS]" if (job.comment and self.MARKER in job.comment) else ""
                info.append(f"  {job}{marker}")
        return "\n".join(info)
