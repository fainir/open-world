# Open World Island entry and place previews

Public production checks on November 21, 2026 used the original service release `4b6c49a` and Chrome on macOS. The phone viewport used desktop Chrome's touch and viewport emulation.

| Check | Observed result |
| --- | --- |
| Original game at 375 × 812 | The home page served `/game/base`. Tap to play opened the HUD, then the vehicle selector opened. |
| Original game at 1200 × 780 | The same base game started with the keyboard and displayed its HUD and bottom bar. |
| Island entry at both widths | [Open World Island](https://open-world.gg/island) opened the live 3D atlas. Both pages reported “Tidefall Island \| Open World” and zero uncaught page exceptions. |
| Redirect and health | GET and HEAD returned 302 to the fixed island origin with `Cache-Control: no-store`. A query with an alternate destination still reached the island. The original health endpoint reported an available database and game files. |
| Public API guard | An empty JSON POST to `/api/island/place-design` returned 422 and identified the three required fields. The input failed validation before any model call. |
| Model contract and limits | All 100 [source checks](../tests/test_island_design.py) passed on the release commit. The 11 place tests used a simulated provider, exercised the existing signed text transport, and verified geometry limits, concurrent retries, quota sharing and original-game preservation. |
