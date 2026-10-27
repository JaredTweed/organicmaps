# Pixel 8 Pro research validation

This work stays on `research/cycling-tag-types`. No PR is created or modified.
The isolated application is `app.organicmaps.cyclingresearch.debug`, not the
normal `app.organicmaps` application.

## Executed On Pixel 8 Pro

Five Debug runs completed on the connected Pixel 8 Pro: baseline and clean,
each in light and dark with OpenGL ES 3, and clean/light with Vulkan. All nine
viewport readiness acknowledgements and nine screenshots were recorded in each
run. Logs identify the Mali-G715 renderer, the requested backend, the Outdoors
layer, and the requested rules override. In the inspected
zoom-18 light and dark screenshots, the clean variant removes many commercial
POI overlays while retaining street labels, crossings and bicycle-route context.
This is an observation of selected views, not a usability study or a conclusion
about the best facility encoding.

The synthetic `display-track.kml` was also imported into the isolated research
app. In one inspected clean/light Vulkan screenshot, its magenta stroke was
visually distinct from nearby blue bicycle-route context. The fixture is not a
navigable route; computed-route overlap, dark mode and daylight/night riding
remain untested. The screenshot remains local as
`build-cycling-research/phone-captures/track-vulkan-clean-light.png`.

The first attempts uncovered and fixed two fixture problems: an invalid region
filename caused map registration to abort, and an unset Outdoors-layer flag
caused Android to switch back to the default style. Those earlier captures are
not comparison evidence. The successful captures and the 302 MB prepared bundle
are retained locally under `build-cycling-research/`; a sanitized
[result summary](cycling-tag-audit/phone-results.json) is committed, while
screenshots and device logs remain local because they contain device UI information.
The map was locally available but its generation provenance is not fully verified.

## Scope

The prepared Debug build is for functional checks and screenshots. It enables
the existing `DRAPE_SCENARIO` and queue-trace instrumentation and the research
type selector. **Debug timings are not release performance evidence.**

There is no dedicated Cycling mode on this branch's pinned upstream base.
The experiment uses the existing Outdoors family as a clearly labeled surrogate:

- Baseline: the exact Outdoors rules bundled in this APK.
- Clean: the same rules with optional commercial/cultural POI overlays reduced
  and major motor-road widths multiplied by 0.8. Geometry, road labels, crossings,
  barriers and priority values remain. Bicycle services, water, shelter, lodging,
  ferry/bus stations and medical services are retained.
- Neither variant adds classifier types, changes routing, classifies safety or
  reconstructs facility distinctions absent from an old map.

The derivation is deterministic, uses the pinned Kothic binary reader/writer,
and round-trips the generated family. Its rule inventory is in
`style-report.json`. It is a hypothesis about clutter, not a usability result.
Do not move these changes into the default style without review.

## Rebuild and stage

From `android/`, with the installed Android SDK:

```sh
ANDROID_HOME="$HOME/Android/Sdk" ./gradlew :app:assembleGoogleDebug \
  -Parm64 -PresearchApplicationId=app.organicmaps.cyclingresearch \
  -PdrapeBenchmark=ON -Pnjobs=2 --max-workers=2
```

The application ID override is opt-in; ordinary builds retain their original ID.
Use the resulting Google Debug APK, not a previously built APK from another
checkout. From the research worktree:

```sh
python3 -B docs/cycling-tag-audit/phone_probe.py prepare \
  --apk /absolute/path/to/new-google-debug.apk \
  --map /absolute/path/to/Vancouver.mwm \
  --aapt "$HOME/Android/Sdk/build-tools/37.0.0/aapt" \
  --kothic tools/kothic --bundle build-cycling-research/phone-bundle
```

Use the installed build-tools version if its directory differs. The bundle also
contains `display-track.kml`, a synthetic display fixture, not a route to follow.
Preparation
refuses an existing output directory, another package, a non-debuggable APK or
an APK without ARM64. It reads map-directory version and baseline style from
the APK itself and hashes all inputs. Directory version alone does **not**
establish compatibility or provenance of the older Vancouver map: inspect the
device rendering before interpreting the trace.

## When the phone is connected

Unlock it, enable USB debugging and approve this computer's RSA prompt. These
are the only manual prerequisites for attempting the automated capture:

```sh
"$HOME/Android/Sdk/platform-tools/adb" devices -l
python3 -B docs/cycling-tag-audit/phone_probe.py capture \
  --bundle build-cycling-research/phone-bundle --output /tmp/cycling-phone-baseline-light \
  --adb "$HOME/Android/Sdk/platform-tools/adb" --serial PHONE_SERIAL \
  --style baseline --theme light --backend OpenGLES3
```

Repeat with a **new output directory** for clean/light, baseline/dark and
clean/dark. Repeat on Vulkan and reverse run order on a second pass. Keep
brightness, orientation, zoom, layers, route and device thermal conditions fixed.
The runner records battery/thermal state; it does not alter global phone settings,
clear logcat, uninstall apps, use root or clear app data.

The runner installs/updates only the research package, force-stops only that
package and uses its `run-as` access to stage a map, rules, preferences and trace.
It overwrites those fixture files inside the research app; do not put personal
bookmarks or settings in this disposable app. Existing normal-app data is not used.

It captures nine readiness-barrier viewports across three Vancouver locations at
zooms 14/16/18. Each has a three-second screenshot dwell. Results include per-view
PNGs, final screenshot, raw logcat, memory and readiness records. Missing/out-of-order
or failed readiness acknowledgements, missed screenshots and scenario failure
make the capture fail. A successful capture still requires **human pixel review**:
the engine can report readiness for an empty or wrong-style map. Backend selection
is a request; verify the actual initialized backend in logs.

If a startup permission/onboarding dialog blocks the trace, inspect the saved
screenshot and complete that dialog in the research app, then rerun with a fresh
output directory. A completed run still needs screenshot and log review.

## Manual checks not replaced by the trace

1. Compare the remaining matched screenshots in rows. Check orientation context, crossings,
   street labels, optional POIs and service discovery at each zoom.
2. Build a bicycle route and compare it with the imported synthetic track and
   position marker in both themes and across zooms.
   Confirm all three remain distinct from infrastructure in both themes.
3. Repeat with contours and cycling-relation overlays, planning and navigation.
4. Review daylight legibility and actual night brightness on the bicycle; a
   desktop dark screenshot is not a night usability test.
5. Test asymmetric facilities and rural/shared paths on **matching regenerated
   candidate maps**. The older Vancouver map cannot validate candidate retention.
6. For performance selection, build matched optimized candidates and collect
   repeated cold/warm tile/frame latency and memory. Do not rank encodings from
   this Debug baseline or compare with unrelated emulator reference numbers.

Product scope, acceptable loss/priority and release compatibility remain maintainer
decisions. A prepared phone bundle does not close those gates.
