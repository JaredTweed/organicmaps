package app.organicmaps.search;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.core.text.HtmlCompat;
import androidx.recyclerview.widget.RecyclerView;
import app.organicmaps.R;
import app.organicmaps.sdk.bookmarks.data.BookmarkInfo;
import app.organicmaps.sdk.bookmarks.data.BookmarkManager;
import java.util.ArrayList;
import java.util.List;
import java.util.function.LongConsumer;

/** Ordinary bookmark results, independent of the bookmark's import source. */
final class BookmarkResultsAdapter extends RecyclerView.Adapter<BookmarkResultsAdapter.Holder>
{
  private final List<BookmarkInfo> results = new ArrayList<>();
  private final LongConsumer select;

  BookmarkResultsAdapter(LongConsumer select)
  {
    this.select = select;
  }

  void update(long[] ids)
  {
    results.clear();
    if (ids != null)
      for (long id : ids)
      {
        BookmarkInfo info = BookmarkManager.INSTANCE.getBookmarkInfo(id);
        if (info != null)
          results.add(info);
      }
    notifyDataSetChanged();
  }

  @Override
  public int getItemCount()
  {
    return results.size();
  }
  @NonNull
  @Override
  public Holder onCreateViewHolder(@NonNull ViewGroup parent, int type)
  {
    return new Holder(LayoutInflater.from(parent.getContext()).inflate(R.layout.item_search_result, parent, false));
  }
  @Override
  public void onBindViewHolder(@NonNull Holder holder, int position)
  {
    BookmarkInfo info = results.get(position);
    ((TextView) holder.itemView.findViewById(R.id.title)).setText(info.getName());
    ((TextView) holder.itemView.findViewById(R.id.description)).setText(R.string.bookmarks);
    ((TextView) holder.itemView.findViewById(R.id.region))
        .setText(HtmlCompat.fromHtml(info.getDescription(), HtmlCompat.FROM_HTML_MODE_LEGACY));
    holder.itemView.findViewById(R.id.open).setVisibility(View.GONE);
    holder.itemView.findViewById(R.id.distance).setVisibility(View.GONE);
    holder.itemView.setOnClickListener(view -> select.accept(info.getBookmarkId()));
  }
  static final class Holder extends RecyclerView.ViewHolder
  {
    Holder(View view)
    {
      super(view);
    }
  }
}
