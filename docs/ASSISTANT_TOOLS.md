# Connected tools and live radio

External information runs through the IAM-authenticated AgentCore Gateway in Tokyo; vehicle controls, timers, notes and calculations remain in the Node backend. No third-party API keys are needed. The self-hosted cascade dispatches recognized information intents with an application router; Sonic uses native `assistant_tool` calls. Each request handles one information intent. Use separate requests for compound information tasks on the cascade.

## Measured tool screen

3 consecutive serial calls per tool: first call plus two repeats. Provider caches included. p95 is nearest-rank (maximum with n=3). Includes MCP tool discovery on first call; excludes ASR, model inference, TTS and browser playback. Synthetic requests only. A smoke screen, not a load test.

Tools require **3/3 successful samples and tool round-trip p95 ≤3,000 ms** to appear enabled. This small smoke screen is not a sustained-load benchmark or an assurance that later calls will be equally fast. Cached repeats explain the difference between median and p95. Requests have a 6.5-second backend budget. Nearby-place lookup returned provider HTTP 502 on all three samples and is excluded.

| Tool | English example | Status | Tool median / p95 | Speech first audio |
| --- | --- | --- | --- | --- |
| weather | `Weather in Seoul` | Enabled | 189 / 1553 ms | 878 ms |
| places | `Find nearby cafes` | Excluded: provider failures | 414 / 1105 ms | — |
| radio | `Play jazz radio` | Enabled | 177 / 177 ms | 617 ms |
| wiki | `Tell me about Gyeongbokgung` | Enabled | 165 / 2972 ms | 740 ms |
| holidays | `When is the next Korean public holiday?` | Enabled | 182 / 277 ms | 498 ms |
| exchange | `Convert 100 US dollars to Korean won` | Enabled | 111 / 153 ms | 695 ms |
| sun | `Sunset in Gangneung` | Enabled | 186 / 445 ms | 705 ms |
| route | `Distance from Seoul City Hall to Seoul Station` | Enabled | 174 / 845 ms | 706 ms |
| web | `Search the web for recent electric vehicle news` | Enabled | 453 / 453 ms | 2902 ms |
| timer | `Set a timer for ten minutes` | Enabled | 0 / 1 ms | 309 ms |
| notes | `Note: parking spot B12 on basement level 2` | Enabled | 0 / 0 ms | 338 ms |
| calculate | `Calculate 20 * 350` | Enabled | 0 / 70 ms | 423 ms |

The speech column is **one synthetic Korean input per tool**, through deployed CloudFront → Whisper → tool → Polly. It measures the first received audio event, excluding synthetic input generation, microphone endpointing and browser playback. All 11 enabled scenarios returned the expected operation, successful tool result and reply audio; this is an integration check, not a language-quality score. See [tool samples](../research/assistant-tool-latency.json) and [speech cases](../research/assistant-demo-smoke.json).

## Cabin UI and recent conversation

The existing vehicle MEDIA card contains the real radio player, station selector, Play and Stop controls. Its title and playback indicator follow the actual radio state. Information shortcuts and the bounded results area live inside the vehicle cabin panel. Voice/model options are in a scrollable disclosure. The conversation panel has a fixed height and keeps only the latest six messages in the browser; the backend conversation and downloaded session keep the full history.

## Radio playback

The player uses a small curated station list, selected after researching Radio Browser and checking the upstream streams. There is no Spotify/Apple Music login. The four streams returned audio/mpeg with at least 8 KiB of real audio on the Seoul host:

| Station | First audio byte |
| --- | --- |
| groovesalad | 648 ms |
| secretagent | 535 ms |
| dronezone | 269 ms |
| kpop | 1018 ms |

Browser playback was separately checked with the HTML audio element: Secret Agent reached readyState 4, paused=false and advancing currentTime. Server byte arrival is not the same metric as browser playback. The player reports its own connection/playback errors and actual playback start time. Browser autoplay may require pressing Play. Radio can pause or change volume through existing media commands. Streams are delivered directly from the broadcaster; audio is not archived.

## Provider sources and limits

- [MET Norway](https://api.met.no/doc/TermsOfService): coordinate-based forecasts, backend identification, caching and CC BY attribution. Default coordinate is explicitly a Seoul City Hall demo location. Browser location is opt-in.
- [AgentCore Web Search](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html): managed AWS search, with visible source citations. The current cascade reads concise excerpts, rather than claiming a fully verified synthesis.
- [Radio Browser](https://docs.radio-browser.info/) and [SomaFM](https://somafm.com/): discovery and curated broadcaster streams. Listing access does not grant redistribution rights; playback availability can change.
- [Wikipedia](https://www.mediawiki.org/wiki/API:REST_API): encyclopedia excerpts with linked attribution; not current opening hours or admission prices.
- [Nager.Date](https://github.com/nager/Nager.Date): Korean holiday list; temporary holidays and future provider/API revisions require rechecking.
- [Frankfurter](https://frankfurter.dev/): daily reference currency conversion, not a bank quote or live trading price.
- [Sunrise-Sunset](https://sunrise-sunset.org/api): astronomical events with visible attribution.
- [OSRM](https://project-osrm.org/) / OpenStreetMap: route distance and estimated time, without live traffic. Two known Seoul endpoints were tested; arbitrary destinations may add geocoding latency. Public demo servers have no availability guarantee.
- [Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API): nearby OSM features, currently excluded after repeated failures; never represents live charger occupancy.

Timers show a countdown, then a persistent dismissible banner and a three-tone chime. Browser audio is unlocked by interaction; **Test chime** can enable/check sound. Deadline-based expiry prevents repeated alerts even if a background-tab tick is delayed. Keep the demo tab open: these are not OS push notifications or durable reminders, and reload/reset clears the timer. Notes are per-session and disappear on reset, expiration or server restart. Calculation uses a bounded numeric parser, never JavaScript evaluation; charging/fuel unit prices must be provided by the user. Selecting precise location sends coordinates through the backend to the selected information provider. Export/feedback can contain request text and tool results; treat those records accordingly.

## Reproduce

See [deployment](DEPLOYMENT.md#6-agentcore-information-tools). Vehicle planner results in the main README predate these information tools; the original prompts and command executor are preserved. Do not merge this tool latency screen into the historical vehicle model benchmark.

## Native Sonic integration

Three English text scenarios (100 USD conversion, jazz radio, a ten-minute timer) passed native tool invocation and native audio output through the deployed WebSocket connection. First received audio was 3,667 / 1,243 / 1,078 ms respectively; an initial spoken acknowledgement can precede tool completion, so these values are not tool-completion latency. See [the native tool records](../research/sonic-assistant-smoke.json).
