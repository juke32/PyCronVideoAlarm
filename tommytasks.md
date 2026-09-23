# LINUX

[ ] Change Brightness when user is added tothe video group more indebth research and testing on other systems
[x] opening url broke in linux  (FIXED: open_url_reliably() in actions.py — webbrowser + xdg-open fallback; used everywhere incl. Kofi)
[x] The test individual actions doesn't behave the same as when played from cron, the url on linux trying to open chrome works only in the sequence editor  (FIXED: play/test actions now spawn the same headless main.py --execute-sequence subprocess as scheduled runs)
[x] clicking the play on individual actions doesn't work, make it play them like they are actually being scheduled like the main test  (FIXED: play_action_by_index / play_sequence_from_index use _spawn_sequence_run)
[x] Kofi button doesn't work  (FIXED: uses open_url_reliably instead of raw webbrowser)

# Windows

[x] Audio shows VLC screen  (FIXED in code: audio files → --intf dummy --no-video, fullscreen forced off; uses is_audio_file) — untested on Windows
[x] one time alarm doesn't delete after run  (FIXED in code: add_alarm embeds --job-id + --scheduled-time; remove_alarm matches by job-id; main.py passes args.scheduled_time + job_id) — untested on Windows
[x] videos show under application  (FIXED in code: --video-on-top added for VLC on Windows) — untested on Windows
[x] next run text is hidden on short displays  (FIXED in code: Next Alarm label moved above the alarm list) — untested on Windows
[ ] Whole scaling is wack and not relative, but that can be fixed later

# General features/issues

# App Feature Ideas

[ ] Need to fix or removesome of the actions (who cares)
[x]     audio recording doesn't work as of now  (IMPROVED: no hard scipy dep (stdlib wave fallback), Linux arecord fallback, better logs)
[x]     photos dont work (maybe open camera app, idk why I would want a video recording in the morning)  (IMPROVED: OpenCV frame warm-up + Linux fswebcam fallback)

[ ] record video in app
[x] be able to add sequences without jumping to the top  (FIXED: scroll position preserved on re-render; snaps to bottom so the new card stays in view)
[x] Add less spacing between actions  (FIXED: card pady 2 → 1)

[ ] Alarm templates:
    [ ] Morning motivation
    [ ] Funny Morning
    [ ] Freedom (funny, motivational, self talk) video maybe with random tasks like stretching, or journaling
    [ ] Meditation Mindfullness

[ ] Adjust alarm minutes up or down buttons?? for touchscreen setting time?

# Build instructions

- add "build" as the first word of a commit :p

# History

2026-02-17_0324 - Still having issues with the VLC on linux, also there is that alarm deletion bug when they have the same days, so the date reading thing has to be made, also the black screen improvement works well so I would rather only go back one revision or stay and push throug these current issues but I don't know. I think the easiest is to fix the bug, and add the alternative player for linux, and then we can work on stability and features... not just getting it working.

2026-02-25 Switching over to MPV only due to issues on linux and it hopefully working well on windows too?

- Must have the word build in the message to trigger the build

2026-02-25_1911_PyCronVideoAlarm_Linux good but no settings file
2026-02-25_1927_PyCronVideoAlarm_Linux perfect!!! adds feature to edit sleep cycle offset
