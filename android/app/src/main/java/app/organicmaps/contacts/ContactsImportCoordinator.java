package app.organicmaps.contacts;

import android.Manifest;
import android.app.Application;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.Looper;
import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;
import app.organicmaps.R;
import app.organicmaps.sdk.bookmarks.data.BookmarkManager;
import app.organicmaps.sdk.downloader.MapManager;
import app.organicmaps.sdk.search.SearchEngine;
import app.organicmaps.sdk.util.Language;
import app.organicmaps.sdk.util.concurrency.ThreadPool;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

public final class ContactsImportCoordinator
{
  private final Application application;
  private Application getApplication()
  {
    return application;
  }
  private static ContactsImportCoordinator instance;

  // Process-owned: the bookmarks activity is finished when returning to the map.
  // Only the application context and temporary import state are retained.
  @androidx.annotation.MainThread
  public static ContactsImportCoordinator getInstance(Application app)
  {
    if (instance == null)
      instance = new ContactsImportCoordinator(app);
    return instance;
  }
  private final Handler main = new Handler(Looper.getMainLooper());
  private final MutableLiveData<ContactsImporter.State> state = new MutableLiveData<>(
      new ContactsImporter.State(ContactsImporter.Phase.IDLE, 0, 0, 0, ContactsImporter.Error.NONE, null));
  private final NativeResolver resolver = new NativeResolver();
  private final ContactsImporter importer;
  private CancellationSignal reading;
  private long readGeneration;

  public ContactsImportCoordinator(@NonNull Application app)
  {
    application = app;
    importer = new ContactsImporter(resolver, this::save, main::post, this::hasPermission, this::publish);
  }

  private void publish(ContactsImporter.State value)
  {
    var preferences = application.getSharedPreferences("contact_import", 0);
    if (preferences.getBoolean("interrupted", false) != value.isRunning())
      preferences.edit().putBoolean("interrupted", value.isRunning()).apply();
    state.setValue(value);
  }

  public boolean wasInterrupted()
  {
    return !state.getValue().isRunning()
 && application.getSharedPreferences("contact_import", 0).getBoolean("interrupted", false);
  }

  public LiveData<ContactsImporter.State> getState()
  {
    return state;
  }

  private boolean hasPermission()
  {
    return Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
 && ContextCompat.checkSelfPermission(getApplication(), Manifest.permission.READ_CONTACTS)
        == PackageManager.PERMISSION_GRANTED;
  }

  public void start()
  {
    try
    {
      ContextCompat.startForegroundService(application,
                                           new android.content.Intent(application, ContactsImportService.class));
    }
    catch (RuntimeException e)
    {
      fail(ContactsImporter.Error.SAVE);
    }
  }

  void begin()
  {
    if (state.getValue().isRunning())
      return;
    if (!hasPermission())
    {
      fail(ContactsImporter.Error.PERMISSION);
      return;
    }
    if (MapManager.nativeGetDownloadedCount() == 0)
    {
      fail(ContactsImporter.Error.MAPS);
      return;
    }
    long generation = ++readGeneration;
    CancellationSignal signal = new CancellationSignal();
    reading = signal;
    publish(new ContactsImporter.State(ContactsImporter.Phase.READING, 0, 0, 0, ContactsImporter.Error.NONE, null));
    ThreadPool.getStorage().execute(() -> {
      try
      {
        List<ContactsImporter.Contact> contacts = ContactsReader.read(getApplication().getContentResolver(), signal);
        main.post(() -> {
          if (generation != readGeneration)
            return;
          reading = null;
          try
          {
            String[] tuples = BookmarkManager.INSTANCE.getImportedContactLocations();
            java.util.List<ContactsImporter.Entry> previous = new java.util.ArrayList<>();
            for (int i = 0; i + 4 < tuples.length; i += 5)
            {
              final long categoryId = Long.parseLong(tuples[i + 4]);
              previous.add(new ContactsImporter.Entry(
                  tuples[i], "", tuples[i + 1],
                  new ContactsImporter.Location(Double.parseDouble(tuples[i + 2]),
                                                Double.parseDouble(tuples[i + 3])),
                  "", java.util.List.of(), BookmarkManager.INSTANCE.isContactCategory(categoryId)));
            }
            importer.start(contacts, previous);
          }
          catch (RuntimeException e)
          {
            fail(ContactsImporter.Error.READ);
          }
        });
      }
      catch (RuntimeException e)
      {
        main.post(() -> {
          if (generation == readGeneration)
          {
            reading = null;
            fail(hasPermission() ? ContactsImporter.Error.READ : ContactsImporter.Error.PERMISSION);
          }
        });
      }
    });
  }

  public void cancel()
  {
    if (!state.getValue().isRunning())
      return;
    ++readGeneration;
    if (reading != null)
    {
      reading.cancel();
      reading = null;
    }
    importer.cancel();
  }

  public void dismissResult()
  {
    if (!state.getValue().isRunning())
      state.setValue(
          new ContactsImporter.State(ContactsImporter.Phase.IDLE, 0, 0, 0, ContactsImporter.Error.NONE, null));
  }

  private void fail(ContactsImporter.Error error)
  {
    publish(new ContactsImporter.State(ContactsImporter.Phase.ERROR, 0, 0, 0, error, null));
  }

  private ContactsImporter.Summary save(List<ContactsImporter.Entry> entries)
  {
    final List<String> obsoleteKeys = new ArrayList<>();
    for (ContactsImporter.Entry entry : entries)
      obsoleteKeys.addAll(entry.obsoleteKeys());

    final long[] values = BookmarkManager.INSTANCE.importContactBookmarks(
        getApplication().getString(R.string.bookmarks_contacts_list_name),
        entries.stream().map(ContactsImporter.Entry::key).toArray(String[] ::new),
        entries.stream().map(ContactsImporter.Entry::name).toArray(String[] ::new),
        entries.stream().map(ContactsImporter.Entry::address).toArray(String[] ::new),
        entries.stream().mapToDouble(entry -> entry.location().latitude()).toArray(),
        entries.stream().mapToDouble(entry -> entry.location().longitude()).toArray());

    if (!obsoleteKeys.isEmpty())
      BookmarkManager.INSTANCE.deleteImportedContactBookmarks(obsoleteKeys.toArray(String[] ::new));

    return new ContactsImporter.Summary(values);
  }

  private final class NativeResolver implements ContactsImporter.Resolver
  {
    private Runnable timeout;
    private long activeId;

    @Override
    public long resolve(ContactAddress address, Consumer<ContactsImporter.Location> callback)
    {
      List<ContactAddress.SearchQuery> queries = address.getSearchQueries();
      long id = SearchEngine.INSTANCE.resolveAddress(
          queries.stream().map(query -> query.query).toArray(String[] ::new),
          queries.stream().map(query -> query.expectedStreet).toArray(String[] ::new),
          Language.getKeyboardLocale(getApplication()), false, (requestId, found, lat, lon) -> {
            if (requestId != activeId)
              return;
            activeId = 0;
            if (timeout != null)
              main.removeCallbacks(timeout);
            timeout = null;
            callback.accept(found ? new ContactsImporter.Location(lat, lon) : null);
          });
      activeId = id;
      timeout = () ->
      {
        if (activeId != id)
          return;
        activeId = 0;
        SearchEngine.INSTANCE.cancelAddressResolution(id);
        timeout = null;
        callback.accept(null);
      };
      main.postDelayed(timeout, 30_000);
      return id;
    }

    @Override
    public void cancel(long id)
    {
      SearchEngine.INSTANCE.cancelAddressResolution(id);
      activeId = 0;
      if (timeout != null)
        main.removeCallbacks(timeout);
      timeout = null;
    }
  }
}
