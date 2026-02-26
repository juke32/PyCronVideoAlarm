import sys
import os
import logging
import getpass
import uuid
from typing import List, Dict, Any

# Try to import CronTab — same direct approach as reference/testcrontab.py
try:
    from crontab import CronTab
    HAS_CRONTAB = True
    logging.info("Successfully imported CronTab")
except ImportError as e:
    HAS_CRONTAB = False
    logging.warning(f"python-crontab not found: {e}")
    
    # Detect wrong package installed (common mistake)
    try:
        import crontab
        logging.warning(f"'crontab' module found at {crontab.__file__} but 'CronTab' class is missing. "
                       "Install the correct package: pip install python-crontab")
    except ImportError:
        logging.warning("Install with: pip install python-crontab")


class LinuxScheduler:
    """Linux-specific scheduler using crontab.
    
    Follows the same simple pattern as reference/testcrontab.py:
        cron = CronTab(user=True)
        job = cron.new(command='...')
        job.minute.on(30)
        cron.write()
    
    No subprocess pre-checks — just try it directly and handle errors.
    """
    MARKER = "#PyCronVideoAlarm"
    
    def __init__(self):
        self.cron = None
        
        # Log user info for debugging
        try:
            user = getpass.getuser()
            uid = os.getuid()
            home = os.environ.get('HOME', 'unknown')
            logging.info(f"LinuxScheduler init: user='{user}', uid={uid}, home='{home}'")
        except Exception:
            pass
        
        if not HAS_CRONTAB:
            logging.warning("CronTab not available — scheduling disabled")
            return
        
        # Just try it — exactly like testcrontab.py does
        try:
            self.cron = CronTab(user=True)
            
            # Quick sanity check: iterate to verify we can read
            count = sum(1 for _ in self.cron)
            logging.info(f"Crontab initialized successfully ({count} existing jobs)")
        except Exception as e:
            logging.error(f"Failed to access crontab: {e}")
            logging.error(f"  User: {getpass.getuser()}, UID: {os.getuid()}")
            logging.error(f"  Check: /etc/cron.allow and /etc/cron.deny")
            logging.error(f"  Fix: echo {getpass.getuser()} | sudo tee -a /etc/cron.allow")
            self.cron = None

    def add_alarm(self, alarm_time, sequence_name: str, days: List[str], one_time: bool = True) -> (bool, str):
        """Add a new alarm to crontab. Returns (success, message).
        
        Keeps it simple — just like reference/testcrontab.py:
            job = cron.new(command='python main.py --execute-sequence "Name"')
            job.minute.on(X)
            cron.write()
        
        Environment detection (DISPLAY, audio, etc.) is handled by main.py
        at runtime, NOT baked into the cron command.
        """
        # IMPORTANT: use `is None`, NOT `not self.cron`!
        # CronTab implements __len__, so an empty crontab (0 jobs) is falsy.
        # `not self.cron` would return True when crontab is valid but empty!
        if self.cron is None: 
            return False, "Crontab not available. Check logs for details."
        
        try:
            # Build command — inject environment variables to fix headless execution issues in Cron
            # Cron does not provide a DISPLAY or XDG_RUNTIME_DIR by default, which causes GUI apps (like VLC) to fail.
            # We hardcode safe defaults here to ensure the alarm can launch visible windows.
            # This is a "Defense in Depth" strategy: main.py also has runtime checks, but setting it here is cleaner.
            uid = os.getuid()
            # Injecting XDG_CURRENT_DESKTOP=KDE helps Qt apps (VLC) pick up the right theme/scaling immediately
            env_prefix = f"DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/{uid} XDG_CURRENT_DESKTOP=KDE "

            if getattr(sys, 'frozen', False):
                cmd = f'{env_prefix}"{sys.executable}" --execute-sequence "{sequence_name}"'
            else:
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../main.py"))
                cmd = f'{env_prefix}"{sys.executable}" "{script_path}" --execute-sequence "{sequence_name}"'
            
            job_id = str(uuid.uuid4())
            
            if one_time:
                time_str = alarm_time.strftime('%H:%M')
                cmd += f" --delete-after --job-id {job_id} --scheduled-time {time_str}"
                comment = f"{self.MARKER}:{job_id}"
            else:
                comment = self.MARKER
            
            # Create the job — same as testcrontab.py: cron.new(command=...)
            job = self.cron.new(command=cmd, comment=comment)
            job.minute.on(alarm_time.minute)
            job.hour.on(alarm_time.hour)
            
            # Set schedule
            if one_time:
                job.month.on(alarm_time.month)
                job.day.on(alarm_time.day)
            elif len(days) == 7 or not days:
                job.dow.every(1)
            else:
                day_map = {"MON":1, "TUE":2, "WED":3, "THU":4, "FRI":5, "SAT":6, "SUN":0}
                cron_days = [day_map.get(d, 1) for d in days]
                job.dow.on(*cron_days)
            
            # Write — same as testcrontab.py: cron.write()
            self.cron.write()
            
            msg = f"Alarm set for {alarm_time.strftime('%H:%M')} via Cron"
            logging.info(f"Crontab write successful. {msg}")
            logging.info(f"Cron command: {cmd}")
            return True, msg
            
        except Exception as e:
            logging.exception(f"Add alarm failed: {e}")
            return False, f"Crontab Error: {str(e)}"

    def list_alarms(self) -> List[Dict[str, Any]]:
        """List all PyCronVideoAlarm jobs from crontab."""
        if self.cron is None: 
            return []
        
        alarms = []
        for job in self.cron:
            # Handle standard marker and UUID-suffixed marker
            if job.comment and (job.comment == self.MARKER or job.comment.startswith(self.MARKER + ":")):
                try:
                    import shlex
                    args = shlex.split(job.command)
                    seq_idx = args.index('--execute-sequence')
                    sequence = args[seq_idx + 1]
                    
                    time_str = f"{job.hour}:{str(job.minute).zfill(2)}"
                    
                    # Parse days of week
                    day_rev_map = {"1":"MON", "2":"TUE", "3":"WED", "4":"THU", 
                                   "5":"FRI", "6":"SAT", "0":"SUN"}
                    dow_str = str(job.dow)
                    if " --delete-after" in job.command:
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
                    logging.debug(f"Skipping unparseable cron job: {e}")
                    continue
        
        return alarms

    def remove_alarm(self, sequence_name: str, time_str: str, days_str: str = "") -> (bool, str):
        """Remove an alarm from crontab. Returns (success, message).
        
        Matches on time, sequence name, AND days to find the exact job.
        """
        if self.cron is None: 
            return False, "Crontab not available"
        
        try:
            hour, minute = map(int, time_str.split(":"))
            removed = False
            
            # Build a comparable days string from the UI format
            # UI sends: "Daily", "SUN", "MON, WED", etc.
            day_rev_map = {"1":"MON", "2":"TUE", "3":"WED", "4":"THU", 
                           "5":"FRI", "6":"SAT", "0":"SUN"}
            
            for job in self.cron:
                # Check marker prefix (supports both legacy and UUID versions)
                is_our_job = job.comment and (job.comment == self.MARKER or job.comment.startswith(self.MARKER + ":"))
                
                if (is_our_job and 
                    job.hour == hour and job.minute == minute and
                    sequence_name in job.command):
                    
                    # If days_str provided, also match on days of week
                    if days_str:
                        dow_str = str(job.dow)
                        if " --delete-after" in job.command:
                            job_days = "Once"
                        elif dow_str == "*":
                            job_days = "Daily"
                        else:
                            job_days = ", ".join(
                                day_rev_map.get(d.strip(), d) for d in dow_str.split(",")
                            )
                        
                        if job_days != days_str:
                            continue  # Not a match — skip this job
                    
                    self.cron.remove(job)
                    removed = True
                    logging.info(f"Removed cron job: {job.command[:80]}...")
                    break  # Only remove ONE matching job
            
            if removed:
                self.cron.write()
                return True, f"Removed alarm: {sequence_name}"
            
            return False, f"Alarm '{sequence_name}' at {time_str} not found in crontab."
            
        except Exception as e:
            logging.exception(f"Remove alarm failed: {e}")
            return False, f"Remove Error: {str(e)}"

    def get_debug_info(self) -> str:
        """Return debug info about crontab state."""
        info = ["=== Linux Crontab Debug Info ==="]
        
        try:
            user = getpass.getuser()
            info.append(f"User: {user} (UID: {os.getuid()})")
            info.append(f"HOME: {os.environ.get('HOME', 'not set')}")
            info.append(f"DISPLAY: {os.environ.get('DISPLAY', 'not set')}")
            info.append(f"XDG_RUNTIME_DIR: {os.environ.get('XDG_RUNTIME_DIR', 'not set')}")
            info.append(f"CronTab available: {self.cron is not None}")
        except Exception as e:
            info.append(f"Error getting user info: {e}")
        
        if self.cron is not None:
            info.append(f"\nAll crontab entries:")
            for job in self.cron:
                marker = " [OURS]" if job.comment == self.MARKER else ""
                info.append(f"  {job}{marker}")
        else:
            info.append("\nCrontab not accessible")
        
        return "\n".join(info)
