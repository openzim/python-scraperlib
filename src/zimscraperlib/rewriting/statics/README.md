This folder must contain two files which are not under Git version control:

- wombat.js, a webrecorder software
- wombatSetup.js, a custom configuration script for wombat.js, which is built in this
  project from files in the javascript folder

If you install zimscraperlib from sdist or wheel, we've pre-packaged these files for
convenience and also so that your version of wombatSetup.js is "aligned" (i.e. if you
install zimscraperlib x.y.z, we are sure which version wombatSetup.js you have).
