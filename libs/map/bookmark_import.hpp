#pragma once

#include "kml/types.hpp"

#include <string>
#include <vector>

class BookmarkManager;

// Stable source keys let an explicit re-import update ordinary bookmarks without duplicating them.
struct BookmarkImportEntry
{
  std::string m_key;
  std::string m_name;
  std::string m_address;
  double m_lat = 0;
  double m_lon = 0;
};

struct BookmarkImportResult
{
  kml::MarkGroupId m_categoryId = kml::kInvalidMarkGroupId;
  size_t m_added = 0;
  size_t m_updated = 0;
  size_t m_unchanged = 0;
  size_t m_edited = 0;
  size_t m_skipped = 0;
};

// Main-thread operation. Preserves local changes, unrelated bookmarks, and category names/visibility.
BookmarkImportResult ImportBookmarks(BookmarkManager & manager, std::string const & source,
                                     std::string const & categoryName,
                                     std::vector<BookmarkImportEntry> const & entries);
