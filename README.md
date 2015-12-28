## Tweak Last played time

Here's an esoteric little add-on for you. It changes the last played time for videos to update only if at least a small portion has actually been played, leaving out videos that were accidentally played, skipped over, started then quickly interrupted, or whatever, hopefully improving the usefulness of lists and add-ons using this timestamp.

It defaults to updating the last played time after the video has been played for at least 2 minutes, and there is an add-on setting to change that amount of time.

### It is goofy

Add-ons can't stop Kodi from updating the last played time, so this changes it back after Kodi updates it. It spits out a second 'VideoLibrary.OnUpdate' notification to other add-ons when it affects a video. It only works on movies and episodes in the library. It can miss rolling back the rare video due to circumstance or whim. Something kinda like this built into Kodi would be less goofy, but how exactly is it supposed to work so that it fits nicely with everyone's viewing/misclicking habits?

It's goofy as nuts, but it does successfully round off a rough edge that I dislike. Maybe there's even someone else out there that feels the same way.
