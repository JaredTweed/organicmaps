package app.organicmaps.contacts;

import static org.junit.Assert.*;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;
import org.junit.Test;

public class ContactsImporterTest
{
  private final ArrayDeque<Runnable> tasks = new ArrayDeque<>();
  private final List<Consumer<ContactsImporter.Location>> callbacks = new ArrayList<>();
  private final List<Long> cancelled = new ArrayList<>();
  private final List<List<ContactsImporter.Entry>> saved = new ArrayList<>();
  private final List<ContactsImporter.State> states = new ArrayList<>();
  private final AtomicBoolean allowed = new AtomicBoolean(true);
  private final ContactsImporter importer = new ContactsImporter(
      new ContactsImporter.Resolver() {
        public long resolve(ContactAddress address, Consumer<ContactsImporter.Location> callback)
        {
          callbacks.add(callback);
          return callbacks.size();
        }
        public void cancel(long id)
        {
          cancelled.add(id);
        }
      },
      entries
      -> {
        saved.add(entries);
        return new ContactsImporter.Summary(new long[] {42, entries.size(), 0, 0, 0, 0});
      },
      tasks::add, allowed::get, states::add);

  private static ContactsImporter.Contact contact(String key, String... addresses)
  {
    var contact = new ContactsImporter.Contact(key, "Name " + key);
    for (String address : addresses)
      contact.addAddress(new ContactAddress(address, "", ""));
    return contact;
  }

  private void complete(int request, ContactsImporter.Location location)
  {
    callbacks.get(request).accept(location);
    while (!tasks.isEmpty())
      tasks.remove().run();
  }

  private ContactsImporter.State last()
  {
    return states.get(states.size() - 1);
  }

  @Test
  public void resolvesOnceForPeopleSharingAnAddress()
  {
    importer.start(List.of(contact("one", "123 Main Street, Canada"), contact("two", "123 Main Street, Canada")));
    assertTrue(saved.isEmpty());
    complete(0, new ContactsImporter.Location(49, -123));
    assertEquals(1, callbacks.size());
    assertEquals(2, saved.get(0).size());
    assertEquals(ContactsImporter.Phase.DONE, last().phase);
    assertEquals(0, last().unresolved);
  }

  @Test
  public void triesOtherAddressesAfterAnUnresolvedPrimary()
  {
    importer.start(List.of(contact("one", "123 Main Street, Canada", "456 Other Road, Canada")));
    complete(0, null);
    assertTrue(saved.isEmpty());
    complete(1, new ContactsImporter.Location(49, -123));
    assertEquals("456 Other Road, Canada", saved.get(0).get(0).address());
    assertEquals(1, saved.get(0).size());
  }

  @Test
  public void cancelDoesNotSavePartialResults()
  {
    importer.start(List.of(contact("one", "123 Main Street, Canada"), contact("two", "456 Other Road, Canada")));
    complete(0, new ContactsImporter.Location(49, -123));
    importer.cancel();
    complete(1, new ContactsImporter.Location(50, -124));
    assertTrue(saved.isEmpty());
    assertEquals(List.of(2L), cancelled);
    assertEquals(ContactsImporter.Phase.CANCELLED, last().phase);
    assertEquals(2, last().total);
  }

  @Test
  public void restartIgnoresAnOlderImportsCallback()
  {
    importer.start(List.of(contact("old", "123 Main Street, Canada")));
    importer.cancel();
    importer.start(List.of(contact("new", "456 Other Road, Canada")));
    complete(0, new ContactsImporter.Location(49, -123));
    assertTrue(saved.isEmpty());
    complete(1, new ContactsImporter.Location(50, -124));
    assertEquals("new", saved.get(0).get(0).key());
  }

  @Test
  public void permissionRevocationDoesNotSaveOrContinue()
  {
    importer.start(List.of(contact("one", "123 Main Street, Canada")));
    allowed.set(false);
    complete(0, new ContactsImporter.Location(49, -123));
    assertTrue(saved.isEmpty());
    assertEquals(ContactsImporter.Error.PERMISSION, last().error);
  }

  @Test
  public void allMissingAddressesDoNotCreateAList()
  {
    importer.start(List.of(contact("one", "123 Main Street, Canada"), contact("two", "123 Main Street, Canada")));
    complete(0, null);
    assertEquals(1, callbacks.size());
    assertTrue(saved.isEmpty());
    assertEquals(2, last().unresolved);
    assertEquals(-1, last().result.categoryId);
  }

  @Test
  public void skipsNonAddressesWithoutCallingTheResolver()
  {
    importer.start(List.of(contact("one", "same as my parents")));
    assertTrue(callbacks.isEmpty());
    assertEquals(1, last().unresolved);
  }

  @Test
  public void rejectsNonFiniteCoordinates()
  {
    importer.start(List.of(contact("one", "123 Main Street, Canada")));
    complete(0, new ContactsImporter.Location(Double.NaN, -123));
    assertTrue(saved.isEmpty());
    assertEquals(1, last().unresolved);
  }

  @Test
  public void missingAddressCacheDoesNotSurviveTheImport()
  {
    var contacts = List.of(contact("one", "123 Main Street, Canada"));
    importer.start(contacts);
    complete(0, null);
    importer.start(contacts);
    assertEquals(2, callbacks.size());
    complete(1, new ContactsImporter.Location(49, -123));
    assertEquals(1, saved.size());
  }

  @Test
  public void providerKeysAreHashedAndDeterministic()
  {
    String key = ContactsReader.hashKey("lookup:personal-provider-key");
    assertEquals(64, key.length());
    assertTrue(key.matches("[0-9a-f]{64}"));
    assertEquals(key, ContactsReader.hashKey("lookup:personal-provider-key"));
    assertNotEquals(key, ContactsReader.hashKey("lookup:different"));
  }

  @Test
  public void contactDropsDuplicateAddressRows()
  {
    assertEquals(1, contact("one", "123 Main Street, Canada", "123 Main Street, Canada").addresses.size());
  }
}
