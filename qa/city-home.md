# City home and controls

Verified on 2026-11-22. Production serves city revision `3d4644faa557` from the completed existing-service deployment. The live health check confirmed the database, game files and backup. [Play Open World](https://open-world.gg/)

## Homepage

- At 1440 × 812 and 375 × 812 Chrome reached the live city directly once the 3D engine loaded. Both showed Loading when the import was delayed and returned directly to play after Retry recovered from a failed import. The city filled the viewport and the desktop frame received keyboard focus.

## Controls

- Desktop Chrome opened the vehicle menu with V and returned to play with Escape. The independent check also verified B, G and the X and Click shooting labels. [Desktop direct play](city-home-desktop.jpg)
- The 375 × 812 touch view rendered an 812 × 375 game. After turning to 812 × 375, Chrome opened and closed Style, paused and resumed. The independent check also verified the rotated joystick, the vehicle and weapon menus, and the fullscreen button in both orientations. [Landscape touch controls](city-home-landscape.jpg)
- The independent check observed fullscreen and pointer-lock requests after deliberate input. The browser kept the game iframe opaque. All 101 local checks passed. [Startup regression](check-game-startup.mjs)
