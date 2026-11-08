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
import androidx.lifecycle.AndroidViewModel;
import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;
import app.organicmaps.R;
import app.organicmaps.sdk.bookmarks.data.BookmarkManager;
import app.organicmaps.sdk.downloader.MapManager;
import app.organicmaps.sdk.search.SearchEngine;
import app.organicmaps.sdk.util.Language;
import app.organicmaps.sdk.util.concurrency.ThreadPool;
import java.util.List;
import java.util.function.Consumer;

public final class ContactsImportViewModel extends AndroidViewModel
{
  private final Handler main = new Handler(Looper.getMainLooper());
  private final MutableLiveData<ContactsImporter.State> state = new MutableLiveData<>(
      new ContactsImporter.State(ContactsImporter.Phase.IDLE, 0, 0, 0, ContactsImporter.Error.NONE, null));
  private final NativeResolver resolver = new NativeResolver();
  private final ContactsImporter importer;
  private CancellationSignal reading;
  private long readGeneration;

  public ContactsImportViewModel(@NonNull Application app)
  {
    super(app);
    importer = new ContactsImporter(resolver, this::save, main::post, this::hasPermission, state::setValue);
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
    state.setValue(
        new ContactsImporter.State(ContactsImporter.Phase.READING, 0, 0, 0, ContactsImporter.Error.NONE, null));
    ThreadPool.getStorage().execute(() -> {
      try
      {
        List<ContactsImporter.Contact> contacts = ContactsReader.read(getApplication().getContentResolver(), signal);
        main.post(() -> {
          if (generation != readGeneration)
            return;
          reading = null;
          importer.start(contacts);
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
    state.setValue(new ContactsImporter.State(ContactsImporter.Phase.ERROR, 0, 0, 0, error, null));
  }

  private ContactsImporter.Summary save(List<ContactsImporter.Entry> entries)
  {
    return new ContactsImporter.Summary(BookmarkManager.INSTANCE.importContactBookmarks(
        getApplication().getString(R.string.bookmarks_contacts_list_name),
        entries.stream().map(ContactsImporter.Entry::key).toArray(String[] ::new),
        entries.stream().map(ContactsImporter.Entry::name).toArray(String[] ::new),
        entries.stream().map(ContactsImporter.Entry::address).toArray(String[] ::new),
        entries.stream().mapToDouble(entry -> entry.location().latitude()).toArray(),
        entries.stream().mapToDouble(entry -> entry.location().longitude()).toArray()));
  }

  @Override
  protected void onCleared()
  {
    cancel();
    super.onCleared();
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
