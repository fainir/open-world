# City gameplay guidance

Verified on 2026-11-22. The existing city service completed the release from `35272d9dc65c`. The public game served the exact guide stylesheet and script, and the health check returned a healthy database and game files. [Play Open World](https://open-world.gg/)

- At 1440 × 812, the game opens directly with a persistent guide and visible hotkeys. Vehicles and Style show how to choose and resume. The Diving Contest guide changed after board selection and after the jump. Chrome flipped and returned to the city with the keyboard. [Diving guide on desktop](city-guide-desktop.jpg)
- At a 375 px phone viewport and in 812 × 375 landscape, the guide explained the visible touch actions. The tests opened and closed the vehicle and style menus, paused, resumed, and used the diving board buttons to choose, jump, flip and leave. [Landscape touch guide](city-guide-touch.jpg)
- On a 320 × 568 touch viewport, the Arcade directions and board stayed clear of each other. The Gallery reticle remained visible, a quick Shoot tap used one round, and Reload refilled the magazine. The independent review also steered the Breakout paddle. [Compact Arcade](city-guide-arcade.jpg) · [Browser regression](check-game-startup.mjs)
