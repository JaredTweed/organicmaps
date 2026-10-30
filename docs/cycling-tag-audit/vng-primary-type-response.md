Yes: one primary `highway=*` for an ordinary road, with attached infrastructure in additional types such as `cyclewaytag=*` / `footwaytag=*`. A shared footway/cycleway on one physical path is a legitimate exception, not a reason to manufacture a second highway category for a road with a cycle lane.

`extra_tag` here is only classifier membership (`=` / `!=`), including parent-path matching against the rule's own classifier. It neither reads arbitrary OSM tags nor chooses a primary road type. A secondary road can test `extra_tag=cyclewaytag=lane` without also becoming `highway=cycleway`.

A dedicated cycleway having a core line, with attached infrastructure potentially offset in the generic style, makes sense. The #12692 comparison preview will retain its existing centerline appearance; side-aware offsets remain a separate proposal/prototype, not something this selector implements. The current generator collapses left/right categories, so correct offsets first need side/direction data, reversal handling and avoidance of duplicating separately mapped paths.

One legacy detail to clarify: `replaced_tags.txt` already turns `ford=yes` into `highway=ford` (with a TODO to change that). The Vancouver audit has 137 footway/cycleway pairs and six footway/ford pairs, unchanged from #12692, and no other multi-highway combinations. Should ford remain an acknowledged legacy modifier for now, with migration handled separately rather than silently changing rendering/routing here?

I will keep the other changes as drafts and hold further code-head rewrites while we agree this boundary.
