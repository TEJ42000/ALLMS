# Sound Effects for Gamification

This directory contains sound effects for gamification events.

## Required Sound Files

The following sound files should be added to this directory:

1. **level-up.mp3** - Played when user levels up
   - Suggested: Triumphant fanfare or achievement sound
   - Duration: 1-2 seconds
   - Format: MP3, 128kbps

2. **badge-earned.mp3** - Played when user earns a badge
   - Suggested: Coin collect or success chime
   - Duration: 0.5-1 second
   - Format: MP3, 128kbps

3. **xp-gain.mp3** - Played when user gains XP
   - Suggested: Subtle positive sound
   - Duration: 0.3-0.5 seconds
   - Format: MP3, 128kbps

4. **streak-milestone.mp3** - Played when user reaches streak milestone
   - Suggested: Celebration or applause sound
   - Duration: 1-2 seconds
   - Format: MP3, 128kbps

## Sound Sources

You can obtain royalty-free sound effects from:

- **Freesound.org** - https://freesound.org/
- **Zapsplat** - https://www.zapsplat.com/
- **Mixkit** - https://mixkit.co/free-sound-effects/
- **Pixabay** - https://pixabay.com/sound-effects/

## Implementation Notes

- All sounds are optional - the system works without them
- Sounds are muted by default on mobile devices
- Users can toggle sounds on/off via the sound control button
- Sounds respect the `prefers-reduced-motion` accessibility setting
- Volume is set to 30% by default to avoid being jarring

## Adding Custom Sounds

To add custom sounds:

1. Place MP3 files in this directory with the exact names listed above
2. Ensure files are optimized for web (128kbps or lower)
3. Test on multiple browsers and devices
4. Verify sounds are not too loud or jarring

## Accessibility

Sound effects are designed to enhance the experience but are not required for functionality. All gamification events also have visual feedback.

