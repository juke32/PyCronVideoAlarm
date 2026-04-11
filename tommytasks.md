# LINUX:
Change Brightness when user is added tothe video group more indebth research and testing on other systems
opening url broke in linux
The test individual actions doesn't behave the same as when played from cron, the url on linux trying to open chrome works only in the sequence editor

# Windows:
Audio shows VLC screen
one time alarm doesn't delete after run
videos show under application
next run text is hidden on short displays
Whole scaling is wack and not relative, but that can be fixed later



# General features/issues:


# App Feature Ideas:
Need to fix or removesome of the actions (who cares)
    audio recording doesn't work as of now
    photos dont work (maybe open camera app, idk why I would want a video recording in the morning)

record video in app
be able to add sequences without jumping to the top
Add less spacing between actions

Alarm templates:
    Morning motivation
    Funny Morning
    Freedom (funny, motivational, self talk) video maybe with random tasks like stretching, or journaling
    Meditation Mindfullness

Adjust alarm minutes up or down buttons?? for touchscreen setting time?


# Build instructions
- add "build" as the first word of a commit :p

# History:
2026-02-17_0324 - Still having issues with the VLC on linux, also there is that alarm deletion bug when they have the same days, so the date reading thing has to be made, also the black screen improvement works well so I would rather only go back one revision or stay and push throug these current issues but I don't know. I think the easiest is to fix the bug, and add the alternative player for linux, and then we can work on stability and features... not just getting it working.

2026-02-25 Switching over to MPV only due to issues on linux and it hopefully working well on windows too?
- Must have the word build in the message to trigger the build

2026-02-25_1911_PyCronVideoAlarm_Linux good but no settings file
2026-02-25_1927_PyCronVideoAlarm_Linux perfect!!! adds feature to edit sleep cycle offset
