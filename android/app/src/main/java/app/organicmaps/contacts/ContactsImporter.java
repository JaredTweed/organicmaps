package app.organicmaps.contacts;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Executor;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;

// Main-thread state machine. No observers, durable contact cache, or search-UI integration.
public final class ContactsImporter
{
  public enum Phase
  {
    IDLE,
    READING,
    RESOLVING,
    SAVING,
    DONE,
    CANCELLED,
    ERROR
  }
  public enum Error
  {
    NONE,
    PERMISSION,
    READ,
    SAVE,
    MAPS
  }

  static final class Contact
  {
    final String key;
    final String name;
    final List<ContactAddress> addresses = new ArrayList<>();

    Contact(String key, String name)
    {
      this.key = key;
      this.name = name;
    }

    void addAddress(ContactAddress address)
    {
      if (addresses.stream().noneMatch(item -> item.getAddressKey().equals(address.getAddressKey())))
        addresses.add(address);
    }
  }

  record Location(double latitude, double longitude)
  {
  }
  record Entry(String key, String name, String address, Location location, String streetKey,
               List<String> obsoleteKeys, boolean inContacts)
  {
    Entry(String key, String name, String address, Location location)
    {
      this(key, name, address, location, "", List.of(), true);
    }
    Entry(String key, String name, String address, Location location, String streetKey,
          List<String> obsoleteKeys)
    {
      this(key, name, address, location, streetKey, obsoleteKeys, true);
    }
  }

  public static final class Summary
  {
    public final long categoryId;
    public final long added;
    public final long updated;
    public final long unchanged;
    public final long edited;
    public final long skipped;

    Summary(long[] values)
    {
      if (values == null || values.length != 6)
        throw new IllegalArgumentException("Invalid bookmark import summary");
      categoryId = values[0];
      added = values[1];
      updated = values[2];
      unchanged = values[3];
      edited = values[4];
      skipped = values[5];
    }
  }

  public static final class State
  {
    public final Phase phase;
    public final int processed;
    public final int total;
    public final int unresolved;
    public final Error error;
    public final Summary result;

    State(Phase phase, int processed, int total, int unresolved, Error error, Summary result)
    {
      this.phase = phase;
      this.processed = processed;
      this.total = total;
      this.unresolved = unresolved;
      this.error = error;
      this.result = result;
    }

    public boolean isRunning()
    {
      return phase == Phase.READING || phase == Phase.RESOLVING || phase == Phase.SAVING;
    }
  }

  interface Resolver
  {
    long resolve(ContactAddress address, Consumer<Location> callback);
    void cancel(long id);
  }

  interface Store
  {
    Summary save(List<Entry> entries);
  }

  private final Resolver resolver;
  private final Store store;
  private final Executor main;
  private final BooleanSupplier permitted;
  private final Consumer<State> observer;
  private final Map<String, Location> locations = new HashMap<>();
  private final List<Entry> entries = new ArrayList<>();
  private final Map<String, Location> previousLocations = new HashMap<>();
  private final List<Entry> previousEntries = new ArrayList<>();
  private List<Contact> contacts = List.of();
  private int index;
  private int addressIndex;
  private int unresolved;
  private long generation;
  private long pending;
  private boolean running;

  ContactsImporter(Resolver resolver, Store store, Executor main, BooleanSupplier permitted, Consumer<State> observer)
  {
    this.resolver = resolver;
    this.store = store;
    this.main = main;
    this.permitted = permitted;
    this.observer = observer;
  }

  void start(List<Contact> contacts)
  {
    start(contacts, List.of());
  }

  void start(List<Contact> contacts, List<Entry> previous)
  {
    clear();
    java.util.Set<String> duplicates = new java.util.HashSet<>();
    for (Entry entry : previous)
    {
      String key = entry.key + "\0" + entry.address;
      if (previousLocations.putIfAbsent(key, entry.location) != null)
        duplicates.add(key);
    }
    duplicates.forEach(previousLocations::remove);
    previousEntries.clear();
    for (Entry entry : previous)
    {
      String streetKey = ContactAddressNormalizer.normalizeStreet(entry.address);
      previousEntries.add(new Entry(entry.key, entry.name, entry.address, entry.location, streetKey,
                                    List.of(), entry.inContacts()));
    }
    this.contacts = List.copyOf(contacts);
    index = addressIndex = unresolved = 0;
    running = true;
    next();
  }

  void cancel()
  {
    int total = contacts.size();
    clear();
    observer.accept(new State(Phase.CANCELLED, index, total, unresolved, Error.NONE, null));
  }

  private void clear()
  {
    ++generation;
    running = false;
    if (pending != 0)
      resolver.cancel(pending);
    pending = 0;
    contacts = List.of();
    entries.clear();
    locations.clear();
    previousLocations.clear();
    previousEntries.clear();
  }

  private static String locationKey(Location location)
  {
    return String.format(Locale.ROOT, "%.7f,%.7f", location.latitude(), location.longitude());
  }

  private static final double RESIDENCE_RADIUS_METERS = 300.0;

  private static final class ResidenceGroup
  {
    final String streetKey;
    final List<Entry> entries = new ArrayList<>();
    final Set<String> names = new LinkedHashSet<>();

    ResidenceGroup(String streetKey)
    {
      this.streetKey = streetKey;
    }

    boolean canAccept(Entry entry)
    {
      if (streetKey.isEmpty() || entry.streetKey().isEmpty())
        return locationKey(entries.get(0).location()).equals(locationKey(entry.location()));
      if (!streetKey.equals(entry.streetKey()))
        return false;
      return entries.stream().anyMatch(
          existing -> distanceMeters(existing.location(), entry.location()) <= RESIDENCE_RADIUS_METERS);
    }

    void add(Entry entry)
    {
      entries.add(entry);
      names.add(entry.name());
    }

    Entry first()
    {
      return entries.get(0);
    }
  }

  // People who share a residence often have different unit prefixes or address formatting and
  // resolve to slightly different points. Group by the normalized street and a small radius, not
  // by exact coordinates.
  private List<Entry> groupByResidence(List<Entry> source)
  {
    List<ResidenceGroup> groups = new ArrayList<>();
    for (Entry entry : source)
    {
      ResidenceGroup target = null;
      for (ResidenceGroup group : groups)
      {
        if (group.canAccept(entry))
        {
          target = group;
          break;
        }
      }
      if (target == null)
      {
        target = new ResidenceGroup(entry.streetKey());
        groups.add(target);
      }
      target.add(entry);
    }

    List<Entry> result = new ArrayList<>(groups.size());
    for (ResidenceGroup group : groups)
    {
      final List<String> previousKeys = new ArrayList<>();
      final Set<String> movedOutKeys = new LinkedHashSet<>();
      for (Entry previous : previousEntries)
      {
        final boolean near;
        if (group.streetKey.isEmpty() || previous.streetKey().isEmpty())
          near = locationKey(group.first().location()).equals(locationKey(previous.location()));
        else
          near = group.streetKey.equals(previous.streetKey()) &&
                 group.entries.stream().anyMatch(
                     entry -> distanceMeters(entry.location(), previous.location()) <= RESIDENCE_RADIUS_METERS);
        if (!near)
          continue;
        if (previous.inContacts())
          previousKeys.add(previous.key());
        else
          movedOutKeys.add(previous.key());
      }

      final String primaryKey;
      if (!previousKeys.isEmpty())
        primaryKey = previousKeys.get(0);
      else
        primaryKey = group.entries.stream()
                         .map(Entry::key)
                         .filter(key -> !movedOutKeys.contains(key))
                         .findFirst()
                         .orElse("residence:" + group.streetKey + "@" + locationKey(group.first().location()));
      final List<String> obsoleteKeys =
          previousKeys.stream().filter(key -> !key.equals(primaryKey)).distinct().toList();
      result.add(new Entry(primaryKey, String.join(", ", group.names), group.first().address(),
                           group.first().location(), group.streetKey, obsoleteKeys));
    }
    return result;
  }

  private static double distanceMeters(Location first, Location second)
  {
    final double lat1 = Math.toRadians(first.latitude());
    final double lat2 = Math.toRadians(second.latitude());
    final double dLat = lat2 - lat1;
    final double dLon = Math.toRadians(second.longitude() - first.longitude());
    final double sinLat = Math.sin(dLat / 2);
    final double sinLon = Math.sin(dLon / 2);
    final double h = sinLat * sinLat + Math.cos(lat1) * Math.cos(lat2) * sinLon * sinLon;
    return 2 * 6371000 * Math.asin(Math.sqrt(h));
  }

  private void next()
  {
    if (!running)
      return;
    if (!permitted.getAsBoolean())
    {
      finish(Phase.ERROR, Error.PERMISSION, null);
      return;
    }
    while (index < contacts.size())
    {
      observer.accept(new State(Phase.RESOLVING, index, contacts.size(), unresolved, Error.NONE, null));
      Contact contact = contacts.get(index);
      while (addressIndex < contact.addresses.size())
      {
        ContactAddress address = contact.addresses.get(addressIndex++);
        if (address.getSearchQueries().isEmpty())
          continue;
        String key = address.getAddressKey();
        String streetKey = ContactAddressNormalizer.normalizeStreet(address.address);
        Location previous = previousLocations.get(contact.key + "\0" + address.address);
        if (previous != null)
        {
          entries.add(new Entry(contact.key, contact.name, address.address, previous, streetKey, List.of()));
          break;
        }
        if (locations.containsKey(key))
        {
          Location cached = locations.get(key);
          if (cached == null)
            continue;
          entries.add(new Entry(contact.key, contact.name, address.address, cached, streetKey, List.of()));
          break;
        }
        long attempt = ++generation;
        try
        {
          pending = resolver.resolve(address, location -> main.execute(() -> {
            if (!running || attempt != generation)
              return;
            pending = 0;
            Location valid = location;
            if (valid != null
                && (!Double.isFinite(valid.latitude) || !Double.isFinite(valid.longitude)
                    || Math.abs(valid.latitude) > 90 || Math.abs(valid.longitude) > 180))
              valid = null;
            locations.put(key, valid);
            if (valid != null)
            {
              entries.add(new Entry(contact.key, contact.name, address.address, valid, streetKey, List.of()));
              ++index;
              addressIndex = 0;
            }
            next();
          }));
        }
        catch (RuntimeException e)
        {
          finish(Phase.ERROR, Error.SAVE, null);
        }
        return;
      }
      if (entries.isEmpty() || !entries.get(entries.size() - 1).key.equals(contact.key))
        ++unresolved;
      ++index;
      addressIndex = 0;
    }
    if (!permitted.getAsBoolean())
    {
      finish(Phase.ERROR, Error.PERMISSION, null);
      return;
    }
    observer.accept(new State(Phase.SAVING, index, contacts.size(), unresolved, Error.NONE, null));
    try
    {
      Summary result = entries.isEmpty() ? new Summary(new long[] {-1, 0, 0, 0, 0, 0})
                                         : store.save(groupByResidence(entries));
      finish(Phase.DONE, Error.NONE, result);
    }
    catch (RuntimeException e)
    {
      finish(Phase.ERROR, Error.SAVE, null);
    }
  }

  private void finish(Phase phase, Error error, Summary result)
  {
    int total = contacts.size();
    clear();
    observer.accept(new State(phase, index, total, unresolved, error, result));
  }
}
