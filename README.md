# Watched status toolbox

A few tools for managing watched status, play count, and resume points for videos in the
library. There are add-on options to disable each section of the add-on.

## Context menu items

Context menu items added to the "Manage..." menu of media items: "Mark watched again"
adds 1 to the play count and updates the last played time, as if
you had just watched it again. "Remove one watch count" removes one from the play count
and changes the last played time to a time between the current last played and date added.
"Clear resume status" removes the resume status of an item, leaving it simply watched or unwatched.

These context items require Kodi 16 Jarvis and above.

## Tweak last played time

This feature changes the last played time for movies and episodes in the library to
update only if at least a small portion has actually been played, preventing updates to
videos that were accidentally played, skipped over, started then quickly interrupted, and
so on, hopefully improving the usefulness of lists and add-ons using this timestamp.

It defaults to updating the last played time after the video has been played for at least
2 minutes, and there is an add-on setting to change that amount of time.

This part is goofy. Add-ons can't stop Kodi from updating the last played time, so this restores the previous
time after Kodi updates it, spitting out a second 'VideoLibrary.OnUpdate' notification to
other add-ons when it affects a video. It can miss rolling back the rare video due to
circumstance or whim. Something kinda like this built into Kodi would be less goofy, but
how exactly is it supposed to work so that it fits nicely with everyone's viewing/misclicking habits?
